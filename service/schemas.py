"""Pydantic schemas for the Coffee Bean Roast Classification inference API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictBase64Request(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image string (JPEG/PNG).")


class PredictResponse(BaseModel):
    predicted_class: str = Field(..., json_schema_extra={"example": "Dark"})
    predicted_class_id: int = Field(..., json_schema_extra={"example": 0})
    confidence: float = Field(..., json_schema_extra={"example": 0.9652})
    probabilities: dict[str, float] = Field(
        ...,
        json_schema_extra={
            "example": {
                "Dark": 0.965,
                "Green": 0.005,
                "Light": 0.010,
                "Medium": 0.020,
            }
        },
    )
    pixel_std: float = Field(..., json_schema_extra={"example": 0.234})
    shannon_entropy: float = Field(..., json_schema_extra={"example": 7.21})
    latency_ms: float = Field(..., json_schema_extra={"example": 12.4})
    model_version: str = Field(..., json_schema_extra={"example": "v1.0.0"})


class HealthResponse(BaseModel):
    status: str = Field("alive", json_schema_extra={"example": "alive"})
    service: str = Field(
        "coffee-bean-roast-classification", json_schema_extra={"example": "coffee-bean-roast-classification"}
    )


class ReadyResponse(BaseModel):
    status: str = Field("ready", json_schema_extra={"example": "ready"})
    model_loaded: bool = Field(True, json_schema_extra={"example": True})
    model_version: str = Field(..., json_schema_extra={"example": "v1.0.0"})
    engine: str = Field(..., json_schema_extra={"example": "ONNXRuntime/TorchScript"})


class OcclusionRejectionResponse(BaseModel):
    error: str = Field(..., json_schema_extra={"example": "Optical Occlusion / Specular Glare Detected"})
    pixel_std: float = Field(..., json_schema_extra={"example": 0.012})
    threshold: float = Field(..., json_schema_extra={"example": 0.05})
    shannon_entropy: float = Field(..., json_schema_extra={"example": 0.45})
    message: str = Field(
        ...,
        json_schema_extra={
            "example": "Frame dynamic range collapsed below minimum threshold. Please inspect camera lens for dust, chaff, or specular glare."
        },
    )
