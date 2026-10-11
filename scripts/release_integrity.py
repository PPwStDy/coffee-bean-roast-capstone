"""Fail release validation if content, class order, clean lineage or export gates differ."""
import hashlib
import json
from pathlib import Path
from src.config import ARCHITECTURE, CLASSES

selection=json.loads(Path('releases/selected.json').read_text())
release=Path('releases')/selection['model_version']
manifest=json.loads((release/'sha256.json').read_text())
for filename,expected in manifest.items():
    assert hashlib.sha256((release/filename).read_bytes()).hexdigest()==expected, filename
metadata=json.loads((release/'metadata.json').read_text())
assert metadata['classes']==CLASSES and metadata['architecture']==ARCHITECTURE
assert metadata['evaluation_status']=='retrained_on_deduplicated_splits'
assert metadata['test_evaluation']['count']==181
assert len(metadata['code_revision'])==40
candidates=metadata['validation_candidates']
float_f1=next(c['macro_f1'] for c in candidates if c['quantization']=='float32')
selected=next(c for c in candidates if c['quantization']==metadata['quantization'])
assert selected['macro_f1']>=float_f1-.01-1e-12
assert selected['max_probability_error']<=.05
assert hashlib.sha256(Path('reports/model.onnx').read_bytes()).hexdigest()==metadata['onnx_sha256']
print('Release content, clean lineage, validation selection and parity gates passed')
