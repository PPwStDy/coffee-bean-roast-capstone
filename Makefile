.PHONY: help data dvc-pull train export serve test loadtest cost portability-audit verify container-build container-run monitor-up monitor-down trigger-alert clean

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
EPOCHS ?= 20
BATCH_SIZE ?= 8
URL ?= http://127.0.0.1:8080
PORT ?= 8080

help:
	@echo "Automated Coffee Bean Roast Classification API — Make Targets"
	@echo "  make data               Validate prepared roast dataset splits"
	@echo "  make dvc-pull           Restore DVC-managed dataset files"
	@echo "  make train              Train model and log lineage to MLflow"
	@echo "  make export             Export trained model to TorchScript & ONNX"
	@echo "  make serve              Run FastAPI inference microservice locally"
	@echo "  make test               Execute full pytest test suite (contracts + faults)"
	@echo "  make loadtest           Execute latency SLO load test benchmark"
	@echo "  make cost               Generate documented cost analysis report"
	@echo "  make portability-audit  Verify Three-Layer Portability compliance"
	@echo "  make verify             Run end-to-end CI validation suite"
	@echo "  make container-build    Build lean production Docker image"
	@echo "  make container-run      Run serving container locally on port $(PORT)"
	@echo "  make monitor-up         Start API, Prometheus, Grafana, and alert webhook"
	@echo "  make monitor-down       Stop local monitoring stack"
	@echo "  make trigger-alert      Send a synthetic occlusion frame to the API"

data:
	$(PYTHON) -c "from src.data import setup_data_directory; setup_data_directory()"

dvc-pull:
	$(PYTHON) -m dvc pull data/coffee_bean_roast.dvc models/iteration4_swin.pth.dvc

train:
	$(PYTHON) -m src.train --epochs $(EPOCHS) --batch-size $(BATCH_SIZE) --seed 42
	$(PYTHON) -m src.export_onnx --evaluate-test

export:
	$(PYTHON) -m src.export_onnx

serve:
	$(PYTHON) -m uvicorn service.app:app --host 0.0.0.0 --port $(PORT)

test:
	PYTHONPATH=. $(PYTHON) -m pytest -v tests/

loadtest:
	PYTHONPATH=. $(PYTHON) -m loadtest.bench --url $(URL) --enforce

cost:
	$(PYTHON) reports/cost_report.py

portability-audit:
	$(PYTHON) scripts/portability_audit.py

verify: portability-audit test loadtest cost
	@echo "\n=============================================="
	@echo "ALL CAPSTONE OPERATIONAL VERIFICATIONS PASSED"
	@echo "=============================================="

container-build:
	docker build -t itcs355-coffee-roast:latest .

container-run: container-build
	docker run -d --rm -p $(PORT):8080 --name coffee-roast-service itcs355-coffee-roast:latest

monitor-up:
	docker compose up --build -d

monitor-down:
	docker compose down

trigger-alert:
	$(PYTHON) scripts/trigger_occlusion.py --url http://localhost:$(PORT)/predict

clean:
	rm -rf .pytest_cache __pycache__ src/__pycache__ service/__pycache__ tests/__pycache__

cloud-check:
	$(PYTHON) -m cloudlayer.config

budget-check:
	$(PYTHON) -m cloudlayer.budget

lint:
	.venv/bin/ruff check src service cloudlayer tests scripts loadtest

dvc-remote:
	$(PYTHON) -m scripts.dvc_remote

release-check:
	$(PYTHON) -m scripts.release_integrity

failure-drill:
	$(PYTHON) -m scripts.failure_drill

cloud-deploy: cloud-check budget-check release-check
	$(PYTHON) -m cloudlayer.deploy

cloud-teardown:
	$(PYTHON) -m cloudlayer.teardown

cold-starts:
	$(PYTHON) -m cloudlayer.cold_starts --url $(URL)

freeze-slo:
	$(PYTHON) -m scripts.freeze_slo
