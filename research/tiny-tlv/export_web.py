"""Export a built Tiny Tel Aviv scene (.blend from build_scene.py) as a tiled, versioned model set for the
streaming three.js viewer in public/tiny-tlv/index.html.

    blender -b --factory-startup --disable-autoexec SCENE.blend -P research/tiny-tlv/export_web.py [-- OUT_DIR]

Output (default public/tiny-tlv/model/<version>/, version = short hash of every file written):

    manifest.json      grid, counts and the file list with byte sizes and SHA-256 hashes
    base.glb           paints first: ground, every building and landmark, the tower, facade detail, and a coarse
                       (decimated) copy of every tree grouped per tile under an empty named coarse_trees_<i>_<j>
    tiles/<i>_<j>.glb  one file per grid cell, streamed by camera priority: the full-detail trees of that cell,
                       street furniture, roof items, kerb paint, balconies, signs, bollards, people and vehicles.
                       Meshes that span several cells (kerb paint, bollards, roof items...) are cut per cell by
                       face centroid. When a tile arrives the viewer hides the base's coarse trees for that cell.

This is the 3-D counterpart of the Deep Zoom pyramid that tiny.london and isometric.nyc stream through
OpenSeadragon: a coarse level everywhere, sharp tiles where the camera looks, immutable versioned folders.

glTF carries only Principled base colours and image textures, so procedural shaders (facade window grids, paving,
asphalt noise) are flattened to the material's base colour (diffuse_color, set by build_scene.principled). The
orthophoto roof material is replaced by a plain roof tone: the Mappa ortho is internal and must not be published.
UV-mapped photo textures (Commons CC, CC0/CC-BY vehicle kits, sign faces) are kept, downsized; the box-projected
CC0 material sets have no UVs and are flattened to their palette colour. Meshes are
Draco-compressed; linked duplicates (trees, vehicles) are written with EXT_mesh_gpu_instancing.
"""
import hashlib
import json
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

repo = Path(__file__).resolve().parents[2]
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out_root = Path(args[0]) if args else repo / 'public/tiny-tlv/model'
GRID = 4                       # 4 x 4 tiles over the diorama square (~117 m each)
COARSE_TREE_RATIO = 0.18       # decimate ratio for the base layer's stand-in trees
MAX_TEX = 1024                 # longest texture side (photo textures)
MAX_ATLAS = 2048
ROOF = (0.80, 0.77, 0.72, 1.0)
BASE_COLLECTIONS = {'ground', 'buildings', 'shalom_meir_tower', 'landmarks', 'facade_detail'}
TILE_COLLECTIONS = {'trees', 'actors', 'procedural_details', 'record_furniture', 'roof_items', 'street_clutter',
                    'props'}
t0 = time.time()
log = lambda *a: print('[ttlv]', *a, flush=True)

# ---------------------------------------------------------------- 1. clean up: cameras, lights, masks, materials
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT') or 'towermask' in o.name.lower():
        bpy.data.objects.remove(o, do_unlink=True)

resized = set()
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    imgs = [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image]
    ortho = m.name.startswith('roof_ortho') or any('ortho' in n.image.name.lower() for n in imgs)
    # The CC0 material sets (blender/pbr.py) are mean-normalised ratio textures box-projected on world position:
    # the meshes have no UVs, so glTF cannot carry them. Flatten those to the palette colour (diffuse_color), which
    # is exactly what the texture's mip chain converges to at distance.
    box = any(n.projection == 'BOX' or 'colour_norm' in n.image.name for n in imgs)
    if bsdf and imgs and not ortho and not box and bsdf.inputs['Base Color'].is_linked:
        # Keep the base-colour texture only: height / roughness / normal maps triple the download for a miniature
        # seen from the air, and the viewer's lighting does not need them.
        for sock in ('Normal', 'Roughness', 'Metallic', 'Coat Normal', 'Specular IOR Level'):
            if sock in bsdf.inputs:
                for l in list(bsdf.inputs[sock].links):
                    nt.links.remove(l)
        bsdf.inputs['Roughness'].default_value = 0.85
        for n in imgs:                                            # keep photo / PBR textures, but small
            im = n.image
            if im.name in resized:
                continue
            resized.add(im.name)
            w, h = im.size
            cap = MAX_ATLAS if 'atlas' in im.name.lower() else MAX_TEX
            if max(w, h) > cap:
                im.scale(int(w * cap / max(w, h)), int(h * cap / max(w, h)))
        continue
    col = ROOF if ortho else tuple(m.diffuse_color)
    alpha = bsdf.inputs['Alpha'].default_value if bsdf else 1.0
    rough = bsdf.inputs['Roughness'].default_value if bsdf else 0.8
    metal = bsdf.inputs['Metallic'].default_value if bsdf else 0.0
    nt.nodes.clear()
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); o_ = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(b.outputs[0], o_.inputs[0])
    b.inputs['Base Color'].default_value = col
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
for im in bpy.data.images:                                        # never ship the internal orthophoto
    if 'ortho' in im.name.lower():
        bpy.data.images.remove(im)

# ---------------------------------------------------------------- 2. grid over the exported geometry
scene = bpy.context.scene
def collection_of(o):
    for c in o.users_collection:
        if c.name in BASE_COLLECTIONS or c.name in TILE_COLLECTIONS:
            return c.name
    return None

meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.data.polygons and not o.hide_render
          and collection_of(o)]
def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (min(p.x for p in pts), min(p.y for p in pts), max(p.x for p in pts), max(p.y for p in pts))
boxes = {o.name: world_bbox(o) for o in meshes}
x0 = min(b[0] for b in boxes.values()); y0 = min(b[1] for b in boxes.values())
x1 = max(b[2] for b in boxes.values()); y1 = max(b[3] for b in boxes.values())
TILE = max(x1 - x0, y1 - y0) / GRID + 1e-6
def cell(x, y):
    return min(GRID - 1, max(0, int((x - x0) / TILE))), min(GRID - 1, max(0, int((y - y0) / TILE)))
log(f'{len(meshes)} meshes, extent x {x0:.1f}..{x1:.1f} y {y0:.1f}..{y1:.1f}, {GRID}x{GRID} tiles of {TILE:.1f} m')

# ---------------------------------------------------------------- 3. assign objects to base / tiles
export_cols = {}
def export_collection(name):
    if name not in export_cols:
        c = bpy.data.collections.new(name); scene.collection.children.link(c); export_cols[name] = c
    return export_cols[name]

def move(o, cname):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    export_collection(cname).objects.link(o)

def split_by_cell(o):
    """Cut a merged mesh (kerb paint, bollards, roof items...) into one object per grid cell by face centroid."""
    me = o.data; mw = o.matrix_world
    centroids = [mw @ p.center for p in me.polygons]
    cells = [cell(c.x, c.y) for c in centroids]
    by_cell = defaultdict(list)
    for i, c in enumerate(cells):
        by_cell[c].append(i)
    parts = []
    for c, faces in by_cell.items():
        keep = set(faces)
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context='FACES')
        me_c = bpy.data.meshes.new(f'{me.name}_{c[0]}_{c[1]}')
        bm.to_mesh(me_c); bm.free()
        for mat in me.materials:
            me_c.materials.append(mat)
        ob = bpy.data.objects.new(f'{o.name}_{c[0]}_{c[1]}', me_c)
        ob.matrix_world = mw.copy()
        parts.append((c, ob))
    bpy.data.objects.remove(o, do_unlink=True)
    return parts

tile_objects = defaultdict(list)
base_objects = []
tree_objects = []
counts = Counter()
for o in meshes:
    cname = collection_of(o)
    if cname in BASE_COLLECTIONS:
        base_objects.append(o)
        if cname == 'buildings' or cname == 'landmarks':
            counts['buildings'] += 1
        continue
    if cname == 'trees':
        tree_objects.append(o); counts['trees'] += 1
        tile_objects[cell(*o.matrix_world.translation.xy)].append(o)
        continue
    head = o.name.split('.')[0].rstrip('0123456789_')
    if head == 'person':
        counts['people'] += 1
    elif head in ('car', 'bus', 'bicycle', 'escooter', 'motor_scooter'):
        counts['vehicles'] += 1
    bx0, by0, bx1, by1 = boxes[o.name]
    if o.data.users > 1 or (bx1 - bx0 < TILE * 0.5 and by1 - by0 < TILE * 0.5):
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2          # small or instanced: whole object, by bbox centre
        tile_objects[cell(cx, cy)].append(o)
    else:
        for c, part in split_by_cell(o):
            tile_objects[c].append(part)
log(f'base {len(base_objects)} objects; tiles ' + ' '.join(f'{k}:{len(v)}' for k, v in sorted(tile_objects.items())))

# ---------------------------------------------------------------- 4. coarse stand-in trees for the base layer
depsgraph = bpy.context.evaluated_depsgraph_get()
coarse_mesh = {}
def coarse_of(me):
    if me.name not in coarse_mesh:
        tmp = bpy.data.objects.new('tmp_decimate', me)
        scene.collection.objects.link(tmp)
        mod = tmp.modifiers.new('dec', 'DECIMATE'); mod.ratio = COARSE_TREE_RATIO; mod.use_collapse_triangulate = True
        depsgraph.update()
        ev = tmp.evaluated_get(depsgraph)
        cm = bpy.data.meshes.new_from_object(ev); cm.name = me.name + '_coarse'
        bpy.data.objects.remove(tmp, do_unlink=True)
        coarse_mesh[me.name] = cm
    return coarse_mesh[me.name]
coarse_parents = {}
for o in tree_objects:
    c = cell(*o.matrix_world.translation.xy)
    if c not in coarse_parents:
        e = bpy.data.objects.new(f'coarse_trees_{c[0]}_{c[1]}', None)
        export_collection('export_base').objects.link(e)
        coarse_parents[c] = e
    ob = bpy.data.objects.new(o.name + '_coarse', coarse_of(o.data))
    ob.matrix_world = o.matrix_world.copy(); ob.parent = coarse_parents[c]
    ob.matrix_parent_inverse = coarse_parents[c].matrix_world.inverted()
    base_objects.append(ob)
log(f'{len(coarse_mesh)} coarse tree prototypes, '
    f'{sum(len(m.polygons) for m in coarse_mesh.values())} faces (vs {sum(len(o.data.polygons) for o in tree_objects)} instanced fine)')

for o in base_objects:
    move(o, 'export_base')
for c, objs in tile_objects.items():
    # The glTF exporter only merges linked duplicates into EXT_mesh_gpu_instancing among siblings under one parent,
    # so each tile's trees and vehicles hang under an empty.
    parent = bpy.data.objects.new(f'trees_{c[0]}_{c[1]}', None)
    export_collection(f'export_tile_{c[0]}_{c[1]}').objects.link(parent)
    for o in objs:
        move(o, f'export_tile_{c[0]}_{c[1]}')
        if o.data.users > 1 and o.parent is None:
            o.parent = parent; o.matrix_parent_inverse = parent.matrix_world.inverted()

# ---------------------------------------------------------------- 5. export
work = out_root / '_export_tmp'
if work.exists():
    shutil.rmtree(work)
(work / 'tiles').mkdir(parents=True)
view_layer = bpy.context.view_layer

def export_selection(objs, path):
    for o in bpy.data.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False); o.hide_viewport = False; o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', export_yup=True, export_apply=True,
                              use_selection=True, export_cameras=False, export_lights=False,
                              export_image_format='JPEG', export_jpeg_quality=80,
                              export_gpu_instances=True,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                              export_draco_position_quantization=14, export_draco_normal_quantization=8,
                              export_draco_color_quantization=8, export_draco_texcoord_quantization=12)
    return path.stat().st_size

def tris(objs):
    n = 0
    for o in objs:
        if o.type == 'MESH':
            n += sum(len(p.vertices) - 2 for p in o.data.polygons)
    return n

base_objs = list(export_cols['export_base'].objects)
base_bytes = export_selection(base_objs, work / 'base.glb')
log(f'base.glb {base_bytes / 1e6:.2f} MB, {tris(base_objs):,} triangles')
tiles = []
for (i, j), objs in sorted(tile_objects.items()):
    objs = list(export_cols[f'export_tile_{i}_{j}'].objects)
    f = work / 'tiles' / f'{i}_{j}.glb'
    nbytes = export_selection(objs, f)
    cx, cy = x0 + (i + 0.5) * TILE, y0 + (j + 0.5) * TILE
    tiles.append({'i': i, 'j': j, 'file': f'tiles/{i}_{j}.glb', 'bytes': nbytes, 'triangles': tris(objs),
                  'objects': len(objs), 'trees': sum(1 for o in objs if o.name.startswith('tree_')),
                  'center': [round(cx, 2), round(cy, 2)]})     # Blender x, y (metres); viewer maps y -> -z
    log(f'tile {i},{j}: {nbytes / 1e6:.2f} MB, {tiles[-1]["triangles"]:,} triangles, {len(objs)} objects')

# ---------------------------------------------------------------- 6. manifest + content-hash version folder
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
files = {'base.glb': {'bytes': base_bytes, 'sha256': sha(work / 'base.glb')}}
for t in tiles:
    t['sha256'] = sha(work / t['file']); files[t['file']] = {'bytes': t['bytes'], 'sha256': t['sha256']}
version = hashlib.sha256(json.dumps(sorted((k, v['sha256']) for k, v in files.items())).encode()).hexdigest()[:10]
manifest = {
    'version': version,
    'units': 'metres', 'up': 'glTF +Y (Blender +Z); tile centres are Blender x,y -> viewer x,-z',
    'grid': {'n': GRID, 'tile_m': round(TILE, 3), 'origin': [round(x0, 3), round(y0, 3)],
             'extent': [round(x1 - x0, 3), round(y1 - y0, 3)]},
    'base': {'file': 'base.glb', 'bytes': base_bytes, 'sha256': files['base.glb']['sha256'],
             'triangles': tris(base_objs), 'coarse_tree_ratio': COARSE_TREE_RATIO},
    'tiles': tiles,
    'counts': dict(counts),
    'total_bytes': sum(v['bytes'] for v in files.values()),
    'total_triangles': tris(base_objs) - tris([o for o in base_objs if o.name.endswith('_coarse')])
                       + sum(t['triangles'] for t in tiles),
    'source_blend_sha256': hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
}
(work / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
final = out_root / version
if final.exists():
    shutil.rmtree(final)
work.rename(final)
log(f'wrote {final} ({manifest["total_bytes"] / 1e6:.1f} MB, {manifest["total_triangles"]:,} triangles, '
    f'{len(tiles)} tiles) in {time.time() - t0:.0f}s')
print('TTLV_VERSION', version, flush=True)
