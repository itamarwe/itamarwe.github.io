"""Validate the shipped tiled model against the viewer, the manifest and model-source.json.

Checks: the viewer's MODEL_VERSION folder exists and is the only version shipped; every file in the manifest is
present with the recorded size and SHA-256; each GLB is self-contained (no external URIs), carries no orthophoto
texture and only JPEG or PNG images; triangle counts in the manifest match the GLBs; and model-source.json records the
same version, byte total and counts.
"""
import hashlib
import json
import re
import struct
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
pub = repo / 'public/tiny-tlv'
html = (pub / 'index.html').read_text()
version = re.search(r"const MODEL_VERSION = '([0-9a-f]{10})'", html).group(1)
model = pub / 'model' / version
assert model.is_dir(), f'viewer points at missing model version {version}'
assert [p.name for p in (pub / 'model').iterdir() if p.is_dir()] == [version], 'ship exactly one model version'
assert not (pub / 'tiny_tel_aviv.glb').exists(), 'the monolithic GLB was replaced by the tiled model'
manifest = json.loads((model / 'manifest.json').read_text())
assert manifest['version'] == version
source = json.loads((Path(__file__).parent / 'model-source.json').read_text())
assert source['model_version'] == version, 'model-source.json is out of date'

def read_glb(path):
    data = path.read_bytes()
    magic, ver, size = struct.unpack_from('<4sII', data)
    assert (magic, ver, size) == (b'glTF', 2, len(data)), path
    json_size, chunk_type = struct.unpack_from('<I4s', data, 12)
    assert chunk_type == b'JSON'
    return data, json.loads(data[20:20 + json_size])

def check(entry, path):
    data, gltf = read_glb(path)
    assert len(data) == entry['bytes'], f'{path.name}: size changed'
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], f'{path.name}: hash changed'
    for e in gltf.get('images', []) + gltf.get('buffers', []):
        assert 'uri' not in e, f'{path.name} must be self-contained'
    for im in gltf.get('images', []):
        assert 'ortho' not in im.get('name', '').lower(), f'{path.name}: internal orthophoto leaked'
        assert im.get('mimeType') in ('image/jpeg', 'image/png'), f'{path.name}: {im.get("name")} has an unexpected format'
    for m in gltf.get('materials', []):
        if 'ortho' in m.get('name', '').lower():
            assert 'baseColorTexture' not in m.get('pbrMetallicRoughness', {})
    tris = 0
    nodes = gltf['nodes']
    for node in nodes:
        if 'mesh' not in node:
            continue
        inst = node.get('extensions', {}).get('EXT_mesh_gpu_instancing')
        count = gltf['accessors'][inst['attributes']['TRANSLATION']]['count'] if inst else 1
        for prim in gltf['meshes'][node['mesh']]['primitives']:
            assert prim.get('mode', 4) == 4
            tris += count * gltf['accessors'][prim['indices']]['count'] // 3
    return tris, gltf

base_tris, base = check(manifest['base'], model / manifest['base']['file'])
assert base_tris == manifest['base']['triangles'], f'base triangles {base_tris} != {manifest["base"]["triangles"]}'
grid = manifest['grid']['n']
coarse = {n['name'] for n in base['nodes'] if n.get('name', '').startswith('coarse_trees_')}
total = sum(v['bytes'] for v in [manifest['base']] + manifest['tiles'])
for t in manifest['tiles']:
    tris, _ = check(t, model / t['file'])
    assert tris == t['triangles'], f'{t["file"]}: triangles {tris} != {t["triangles"]}'
    assert 0 <= t['i'] < grid and 0 <= t['j'] < grid
    if t['trees']:
        assert f'coarse_trees_{t["i"]}_{t["j"]}' in coarse, f'{t["file"]}: base has no coarse trees to hide'
assert total == manifest['total_bytes'] == source['model_bytes']
assert manifest['counts'] == source['counts']
assert source['source_blend_sha256'] == manifest['source_blend_sha256']
print(f'Model {version} verified: base {manifest["base"]["bytes"]:,} B + {len(manifest["tiles"])} tiles = '
      f'{total / 1e6:.1f} MB, {manifest["total_triangles"]:,} triangles, JPEG/PNG textures only, no orthophoto.')
