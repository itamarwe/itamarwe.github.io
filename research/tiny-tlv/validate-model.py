"""Validate the shipped GLB's geometry counts and public texture inventory."""
import hashlib
import json
import struct
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
model = (repo / 'public/tiny-tlv/tiny_tel_aviv.glb').read_bytes()
source = json.loads((Path(__file__).parent / 'model-source.json').read_text())
magic, version, size = struct.unpack_from('<4sII', model)
assert (magic, version, size) == (b'glTF', 2, len(model))
json_size, chunk_type = struct.unpack_from('<I4s', model, 12)
assert chunk_type == b'JSON'
gltf = json.loads(model[20:20 + json_size])
assert hashlib.sha256(model).hexdigest() == source['model_sha256']
assert len(model) == source['model_bytes']
allowed = {'endwall', 'crown_plain', 'fascia', 'glazed', 'south_office', 'podium_south', 'crown_south'}
assert {im['name'] for im in gltf.get('images', [])} == allowed
for entry in gltf.get('images', []) + gltf.get('buffers', []):
    assert 'uri' not in entry, 'The model must be self-contained'
for material in gltf.get('materials', []):
    if 'ortho' in material.get('name', '').lower():
        assert 'baseColorTexture' not in material.get('pbrMetallicRoughness', {})
triangles = 0
for node in gltf['nodes']:
    if 'mesh' not in node:
        continue
    for primitive in gltf['meshes'][node['mesh']]['primitives']:
        assert primitive.get('mode', 4) == 4
        triangles += gltf['accessors'][primitive['indices']]['count'] // 3
assert triangles == source['triangles']
print(f'GLB verified: {len(model):,} bytes, {triangles:,} triangles, seven embedded facade images, no orthophoto texture.')
