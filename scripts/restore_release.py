"""Materialize the selected immutable release into the serving build context."""
import json
import shutil
from pathlib import Path

selection=json.loads(Path('releases/selected.json').read_text())
release=Path('releases')/selection['model_version']
for source,destination in [('model.onnx','model.onnx'),('model.pt','model.pt'),('metadata.json','model_metadata.json')]:
    shutil.copy2(release/source,Path('reports')/destination)
