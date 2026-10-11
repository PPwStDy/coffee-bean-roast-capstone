"""FastAPI inference microservice for Coffee Bean Roast Classification.

Adheres strictly to the ITCS355 three-layer portability contract.
Includes real-time Prometheus telemetry and an optical occlusion/glare guard
implementing our deliberate failure mode defense.

Run locally:
    uvicorn service.app:app --port 8080 --host 0.0.0.0
"""
from __future__ import annotations

import base64
import asyncio
import binascii
import hashlib
import io
import json
import logging
import os
import time
import uuid
import warnings
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from service.schemas import (
    HealthResponse,
    PredictBase64Request,
    PredictResponse,
    ReadyResponse,
)
from src.config import (
    ARCHITECTURE,
    CLASSES,
    IMAGE_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    MIN_PIXEL_STD_THRESHOLD,
    MIN_SHANNON_ENTROPY_THRESHOLD,
    MODEL_PATH,
    MODEL_METADATA_PATH,
    MODEL_VERSION,
    TORCHSCRIPT_MODEL_PATH,
)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        try:
            fields = json.loads(record.getMessage())
            if not isinstance(fields, dict):
                fields = {"message": fields}
        except (ValueError, TypeError):
            fields = {"message": record.getMessage()}
        return json.dumps({"ts": self.formatTime(record), "level": record.levelname, **fields})


log = logging.getLogger("coffee_service")
log.setLevel(logging.INFO)
log.propagate = False
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
log.addHandler(handler)

MAX_PAYLOAD = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_CONCURRENCY = int(os.environ.get("MAX_INFERENCE_CONCURRENCY", "2"))
if not 1 <= MAX_CONCURRENCY <= 8:
    raise ValueError("MAX_INFERENCE_CONCURRENCY must be between 1 and 8")
HTTP_REQUESTS = Counter("coffee_http_requests_total", "HTTP responses", ["route", "status"])
HTTP_ERRORS = Counter("coffee_http_errors_total", "HTTP errors", ["route", "status"])
HTTP_LATENCY = Histogram("coffee_http_latency_seconds", "End-to-end request duration", ["route"],
                         buckets=[.01, .05, .1, .2, .5, 1, 2, 5, 10])

# Prometheus Metrics
INFERENCE_LATENCY = Histogram(
    "coffee_inference_latency_seconds",
    "Inference latency in seconds for coffee roast classification",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.12, 0.2, 0.5],
)
PREDICTIONS_TOTAL = Counter(
    "coffee_predictions_total",
    "Total predictions classified by roast class",
    ["predicted_class"],
)
ANOMALY_FRAMES_TOTAL = Counter(
    "coffee_anomaly_frames_total",
    "Total frames rejected by optical occlusion/glare guard",
    ["rejection_reason"],
)

STATE: dict[str, Any] = {
    "model": None,
    "engine": "unknown",
    "version": os.environ.get("MODEL_VERSION", MODEL_VERSION),
}


def _load_inference_engine():
    """Loads inference model once at startup into memory.

    Prefers ONNX Runtime if available; falls back to native TorchScript CPU.
    """
    model_path = os.environ.get("MODEL_PATH", str(MODEL_PATH))
    ts_path = os.environ.get("TORCHSCRIPT_MODEL_PATH", str(TORCHSCRIPT_MODEL_PATH))
    metadata = json.loads(MODEL_METADATA_PATH.read_text())
    if metadata.get("classes") != CLASSES or metadata.get("architecture") != ARCHITECTURE:
        raise ValueError("Serving artifact metadata does not match the roast model contract")
    if metadata.get("input_size") != IMAGE_SIZE or metadata.get("normalization") != "ImageNet":
        raise ValueError("Serving artifact preprocessing contract is incompatible")
    expected_preprocessing = {"resize": "bilinear", "mean": IMAGENET_MEAN, "std": IMAGENET_STD}
    if metadata.get("preprocessing") != expected_preprocessing:
        raise ValueError("Serving artifact preprocessing details are missing or incompatible")
    if not isinstance(metadata.get("model_version"), str) or not metadata["model_version"].strip():
        raise ValueError("Serving artifact has no model version")
    if os.environ.get("MODEL_VERSION") and os.environ["MODEL_VERSION"] != metadata["model_version"]:
        raise ValueError("MODEL_VERSION differs from the exported model version")
    STATE["version"] = metadata["model_version"]

    def check_artifact(path, key):
        with open(path, "rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != metadata.get(key):
            raise ValueError(f"Serving artifact hash mismatch: {path}")

    # Check for ONNX Runtime
    if os.environ.get("INFERENCE_ENGINE", "onnx") == "onnx" and not os.path.exists(model_path):
        raise FileNotFoundError("Selected ONNX artifact is missing")
    try:
        import onnxruntime as ort

        if os.path.exists(model_path) and os.environ.get("INFERENCE_ENGINE", "onnx") == "onnx":
            check_artifact(model_path, "onnx_sha256")
            options = ort.SessionOptions()
            options.intra_op_num_threads = int(os.environ.get("INFERENCE_THREADS", "1"))
            options.inter_op_num_threads = 1
            session = ort.InferenceSession(model_path, sess_options=options, providers=["CPUExecutionProvider"])
            if session.get_outputs()[0].shape[-1] != len(CLASSES):
                raise ValueError("ONNX output count does not match the four roast classes")
            inputs = session.get_inputs()
            if len(inputs) != 1 or inputs[0].type != "tensor(float)" or inputs[0].shape[1:] != [3, IMAGE_SIZE, IMAGE_SIZE]:
                raise ValueError("ONNX input shape or dtype is incompatible")
            check = session.run(None, {inputs[0].name: np.zeros((1, 3, IMAGE_SIZE, IMAGE_SIZE), dtype=np.float32)})[0]
            if check.shape != (1, 4) or not np.isfinite(check).all():
                raise ValueError("ONNX startup inference produced invalid outputs")
            log.info('"Loaded ONNX model: %s"', model_path)
            return session, "ONNXRuntime"
    except ImportError:
        if os.environ.get("INFERENCE_ENGINE", "onnx") == "onnx":
            raise RuntimeError("Selected ONNX runtime is unavailable") from None

    # TorchScript fallback
    if os.path.exists(ts_path):
        check_artifact(ts_path, "torchscript_sha256")
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("TorchScript artifact exists but PyTorch is not installed") from exc
        model = torch.jit.load(ts_path, map_location="cpu")
        torch.set_num_threads(int(os.environ.get("INFERENCE_THREADS", "1")))
        model.eval()
        log.info('"Loaded TorchScript model: %s"', ts_path)
        return model, "TorchScript"

    raise FileNotFoundError(
        f"No ONNX or TorchScript model artifact found at {model_path!r} or {ts_path!r}"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.inference_slots = asyncio.Semaphore(MAX_CONCURRENCY)
    try:
        model, engine = _load_inference_engine()
        STATE["model"] = model
        STATE["engine"] = engine
        log.info('"Model ready, engine=%s, version=%s"', engine, STATE["version"])
    except Exception as exc:
        STATE["model"] = None
        STATE["engine"] = "failed"
        log.error('"Model loading failed: %s"', exc)
    yield
    STATE["model"] = None


app = FastAPI(
    title="Automated Coffee Bean Roast Classification API",
    version=MODEL_VERSION,
    description="Low-latency microservice for coffee bean roast classification with deliberate failure defense.",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_telemetry_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    if len(request_id) > 128 or any(ord(c) < 32 or ord(c) > 126 for c in request_id):
        request_id = str(uuid.uuid4())
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception(json.dumps({"event": "request_error", "request_id": request_id}))
        response = JSONResponse(status_code=500, content={"detail": "Internal service error"})
    latency_ms = (time.perf_counter() - started) * 1000

    response.headers["x-request-id"] = request_id
    response.headers["x-model-version"] = str(STATE["version"])

    route = request.url.path if request.url.path in {"/predict", "/predict/base64", "/ready", "/health", "/metrics"} else "other"
    HTTP_REQUESTS.labels(route, str(response.status_code)).inc()
    HTTP_LATENCY.labels(route).observe(latency_ms / 1000)
    if response.status_code >= 400:
        HTTP_ERRORS.labels(route, str(response.status_code)).inc()
    log.info(json.dumps({"event": "http_request", "request_id": request_id, "path": route,
                         "status": response.status_code, "latency_ms": round(latency_ms, 2),
                         "model_version": STATE["version"]}))
    return response


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe. Asserts the process is alive."""
    return HealthResponse(status="alive", service="coffee-bean-roast-classification")


@app.get("/ready", response_model=ReadyResponse)
def ready():
    """Readiness probe. Asserts the model is loaded and prepared to serve traffic."""
    if STATE["model"] is None or STATE["engine"] == "failed":
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "Model inference engine not loaded"},
        )
    return ReadyResponse(
        status="ready",
        model_loaded=True,
        model_version=str(STATE["version"]),
        engine=str(STATE["engine"]),
    )


@app.get("/metrics")
def metrics():
    """Prometheus telemetry scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def compute_shannon_entropy(image_np: np.ndarray) -> float:
    """Computes Shannon entropy of pixel intensity distribution."""
    gray = np.mean(image_np, axis=2).astype(np.uint8)
    hist, _ = np.histogram(gray, bins=256, range=(0, 256), density=True)
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log2(hist))) if len(hist) > 0 else 0.0


def validate_frame_quality(image: Image.Image) -> tuple[float, float]:
    """Optical Glare & Occlusion Guard (Deliberate Failure Mode Defense).

    Asserts input image maintains sufficient dynamic range.
    Rejects degenerate solid-color frames (e.g. overexposed white glare or
    black/gray camera occlusion) before uncalibrated softmax hallucination occurs.
    """
    img_array = np.array(image.convert("RGB").resize((IMAGE_SIZE, IMAGE_SIZE)), dtype=np.float32) / 255.0
    pixel_std = float(np.std(img_array))
    entropy = compute_shannon_entropy((img_array * 255).astype(np.uint8))

    if pixel_std < MIN_PIXEL_STD_THRESHOLD or entropy < MIN_SHANNON_ENTROPY_THRESHOLD:
        ANOMALY_FRAMES_TOTAL.labels(rejection_reason="low_variance_occlusion").inc()
        log.warning(
            '{"event":"occlusion_guard_rejection","pixel_std":%.4f,"entropy":%.4f,"threshold":%.4f}',
            pixel_std,
            entropy,
            MIN_PIXEL_STD_THRESHOLD,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Optical Occlusion / Specular Glare Detected",
                "pixel_std": round(pixel_std, 4),
                "threshold": MIN_PIXEL_STD_THRESHOLD,
                "shannon_entropy": round(entropy, 4),
                "message": (
                    "Frame dynamic range collapsed below minimum threshold. "
                    "Please inspect camera lens for dust, chaff, or specular glare."
                ),
            },
        )
    return pixel_std, entropy


def preprocess_image(image: Image.Image) -> np.ndarray:
    """Standardizes input crop into normalized 224x224 tensor."""
    resized = image.convert("RGB").resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
    arr = np.array(resized, dtype=np.float32) / 255.0
    # Normalize with ImageNet mean and std
    norm = (arr - np.array(IMAGENET_MEAN)) / np.array(IMAGENET_STD)
    tensor_chw = np.transpose(norm, (2, 0, 1)).astype(np.float32)
    batch_tensor = np.expand_dims(tensor_chw, axis=0)
    return batch_tensor


def run_inference(batch_np: np.ndarray) -> np.ndarray:
    """Dispatches inference to the active engine."""
    engine = STATE["engine"]
    model = STATE["model"]

    if engine == "ONNXRuntime":
        input_name = model.get_inputs()[0].name
        outputs = model.run(None, {input_name: batch_np})
        logits = outputs[0][0]
    elif engine == "TorchScript" or hasattr(model, "forward"):
        import torch

        with torch.no_grad():
            outputs = model(torch.from_numpy(batch_np))
            logits = outputs[0].numpy()
    else:
        raise HTTPException(status_code=503, detail="Model inference engine unavailable")

    # Softmax conversion
    if logits.shape != (len(CLASSES),) or not np.isfinite(logits).all():
        raise HTTPException(status_code=503, detail="Invalid model output")
    exp_logits = np.exp(logits - np.max(logits))
    probs = exp_logits / np.sum(exp_logits)
    return probs


def execute_scoring(image: Image.Image) -> PredictResponse:
    t_start = time.perf_counter()

    # 1. Deliberate failure quality guard
    pixel_std, entropy = validate_frame_quality(image)

    # 2. Preprocessing
    batch_np = preprocess_image(image)

    # 3. Model Scoring with telemetry
    with INFERENCE_LATENCY.time():
        probs = run_inference(batch_np)

    latency_ms = (time.perf_counter() - t_start) * 1000

    pred_idx = int(np.argmax(probs))
    pred_class = CLASSES[pred_idx]
    confidence = float(probs[pred_idx])

    # Record Prometheus metrics
    PREDICTIONS_TOTAL.labels(predicted_class=pred_class).inc()

    prob_dict = {cls_name: round(float(probs[i]), 4) for i, cls_name in enumerate(CLASSES)}

    return PredictResponse(
        predicted_class=pred_class,
        predicted_class_id=pred_idx,
        confidence=round(confidence, 4),
        probabilities=prob_dict,
        pixel_std=round(pixel_std, 4),
        shannon_entropy=round(entropy, 4),
        latency_ms=round(latency_ms, 2),
        model_version=str(STATE["version"]),
    )


def decode_image(contents: bytes) -> Image.Image:
    if not contents:
        raise HTTPException(400, "Empty image payload")
    if len(contents) > MAX_PAYLOAD:
        raise HTTPException(413, "Decoded image exceeds 5 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as source:
                if source.format not in {"JPEG", "PNG"}:
                    raise HTTPException(415, "Only JPEG and PNG images are supported")
                if source.width * source.height > MAX_PIXELS:
                    raise HTTPException(413, "Image exceeds 20 megapixels")
                source.load()
                return source.convert("RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(413, "Image exceeds safe pixel limits") from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "Unreadable or malformed image payload") from None


async def bounded_body(request: Request, limit: int) -> bytes:
    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > limit:
                raise HTTPException(413, "Request payload exceeds the supported size")
        except ValueError:
            raise HTTPException(400, "Malformed Content-Length") from None
    parts, total = [], 0
    async for part in request.stream():
        total += len(part)
        if total > limit:
            raise HTTPException(413, "Request payload exceeds the supported size")
        parts.append(part)
    return b"".join(parts)


async def score_bytes(request: Request, contents: bytes) -> PredictResponse:
    slots = request.app.state.inference_slots
    try:
        await asyncio.wait_for(slots.acquire(), timeout=1.0)
    except TimeoutError:
        raise HTTPException(503, "Inference capacity is busy; retry shortly") from None
    try:
        return await run_in_threadpool(lambda: execute_scoring(decode_image(contents)))
    finally:
        slots.release()


ERRORS = {400: {"description": "Malformed or unreadable image"}, 413: {"description": "5 MiB or 20 megapixel limit exceeded"},
          415: {"description": "Unsupported image type"}, 422: {"description": "Optical rejection or invalid request fields"},
          503: {"description": "Model unavailable or inference capacity busy"}}


@app.post("/predict", response_model=PredictResponse, responses=ERRORS, openapi_extra={
    "requestBody": {"required": True, "content": {
        "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
        "image/png": {"schema": {"type": "string", "format": "binary"}},
        "multipart/form-data": {"schema": {"type": "object", "required": ["file"], "properties": {
            "file": {"type": "string", "format": "binary"}}}}}}})
async def predict(request: Request) -> PredictResponse:
    """JPEG/PNG bytes or multipart `file`; maximum 5 MiB and 20 megapixels."""
    content_type = request.headers.get("content-type", "").split(";")[0].lower()
    contents = await bounded_body(request, MAX_PAYLOAD + 65536 if content_type == "multipart/form-data" else MAX_PAYLOAD)
    if content_type == "multipart/form-data":
        request._body = contents
        try:
            async with request.form(max_files=1, max_fields=0, max_part_size=MAX_PAYLOAD) as form:
                file_item = form.get("file")
                if file_item is None or not hasattr(file_item, "read"):
                    raise HTTPException(400, "Multipart form requires one file field")
                contents = await file_item.read(MAX_PAYLOAD + 1)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(400, "Malformed multipart upload") from None
    elif content_type not in {"image/jpeg", "image/png", "application/octet-stream", ""}:
        raise HTTPException(415, "Send JPEG/PNG bytes or a multipart file")
    return await score_bytes(request, contents)


@app.post("/predict/base64", response_model=PredictResponse, responses=ERRORS, openapi_extra={
    "requestBody": {"required": True, "content": {"application/json": {
        "schema": PredictBase64Request.model_json_schema()}}}})
async def predict_base64(request: Request) -> PredictResponse:
    """Strict base64 JPEG/PNG in JSON; maximum decoded image size 5 MiB."""
    from pydantic import ValidationError
    body = await bounded_body(request, 4 * ((MAX_PAYLOAD + 2) // 3) + 1024)
    try:
        payload = PredictBase64Request.model_validate_json(body)
    except ValidationError:
        raise HTTPException(422, "JSON requires an image_base64 string") from None
    try:
        raw_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "Malformed base64 image data") from None
    return await score_bytes(request, raw_bytes)
