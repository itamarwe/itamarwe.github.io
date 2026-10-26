"""Export a built scene (.blend from build_scene.py) to a compact GLB for the three.js viewer.

    blender -b --factory-startup --disable-autoexec SCENE.blend -P research/tiny-tlv/export_web.py

Defaults to public/tiny-tlv/tiny_tel_aviv.glb relative to this script.
An optional output path may be passed after --. Adapted from the Tiny Tel Aviv source project.

glTF carries only Principled base colours and image textures, so procedural shaders (facade window grids, paving,
asphalt noise) are flattened to the material's base colour (diffuse_color, set by build_scene.principled). The
orthophoto roof material is replaced by a plain roof tone: the Mappa ortho is internal and must not be published.
Photo textures (Commons, CC) are kept, downsized. Meshes are Draco-compressed.
"""
import sys
from pathlib import Path

import bpy

repo = Path(__file__).resolve().parents[2]
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = Path(args[0]) if args else repo / 'public/tiny-tlv/tiny_tel_aviv.glb'
out.parent.mkdir(parents=True, exist_ok=True)
ROOF = (0.80, 0.77, 0.72, 1.0)

for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT') or 'towermask' in o.name.lower():
        bpy.data.objects.remove(o, do_unlink=True)

for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    imgs = [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image]
    ortho = m.name.startswith('roof_ortho') or any('ortho' in n.image.name.lower() for n in imgs)
    if bsdf and imgs and not ortho and bsdf.inputs['Base Color'].is_linked:
        for n in imgs:                                            # keep photo textures, but small
            w, h = n.image.size
            if max(w, h) > 1024:
                n.image.scale(int(w * 1024 / max(w, h)), int(h * 1024 / max(w, h)))
        continue
    col = ROOF if ortho else tuple(m.diffuse_color)
    alpha = bsdf.inputs['Alpha'].default_value if bsdf else 1.0
    rough = bsdf.inputs['Roughness'].default_value if bsdf else 0.8
    metal = bsdf.inputs['Metallic'].default_value if bsdf else 0.0
    emit = bsdf.inputs['Emission Strength'].default_value if bsdf else 0.0
    nt.nodes.clear()
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); o_ = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(b.outputs[0], o_.inputs[0])
    b.inputs['Base Color'].default_value = col
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    if emit > 0 and 'night' not in m.name:
        pass                                                      # day viewer: no emission

bpy.ops.export_scene.gltf(filepath=str(out), export_format='GLB', export_yup=True, export_apply=True,
                          export_cameras=False, export_lights=False, export_image_format='JPEG',
                          export_jpeg_quality=78, export_draco_mesh_compression_enable=True,
                          export_draco_mesh_compression_level=6, export_draco_position_quantization=14,
                          export_draco_normal_quantization=8, export_draco_color_quantization=8)
print('[ttlv] exported', out, round(out.stat().st_size / 1e6, 2), 'MB', flush=True)
