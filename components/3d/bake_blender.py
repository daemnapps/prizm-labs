"""
Blender side of make3d: take the raw TRELLIS.2 mesh + its voxel colour field
(npz), voxel-remesh it clean, decimate, colour it, UV-unwrap, bake the colour
into a base-color texture, and export a textured GLB.

blender -b -P bake_blender.py -- <in.npz> <out.glb> [texture_size] [roughness]
"""
import sys
import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = argv[0], argv[1]
tex = int(argv[2]) if len(argv) > 2 else 2048
rough = float(argv[3]) if len(argv) > 3 else 0.8

d = np.load(src)
V, F = d["verts"].astype(np.float32), d["faces"].astype(np.int32)
P, S = d["points"].astype(np.float32), d["point_colors"].astype(np.float32)  # voxel centres, sRGB
target = int(d["target_faces"])
voxel = float(d["remesh_voxel"])

bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("object")
me.vertices.add(len(V))
me.vertices.foreach_set("co", V.ravel())
me.loops.add(F.size)
me.loops.foreach_set("vertex_index", F.ravel())
me.polygons.add(len(F))
me.polygons.foreach_set("loop_start", np.arange(0, F.size, 3, dtype=np.int32))
me.polygons.foreach_set("loop_total", np.full(len(F), 3, dtype=np.int32))
me.update()
me.validate()

ob = bpy.data.objects.new("object", me)
bpy.context.scene.collection.objects.link(ob)
bpy.context.view_layer.objects.active = ob
ob.select_set(True)

# Optional voxel remesh (off by default: TRELLIS meshes are open, and the
# remesh shreds them). Face orientation is fixed on the Python side.
if voxel > 0:
    rm = ob.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    bpy.ops.object.modifier_apply(modifier="remesh")
nf = len(ob.data.polygons) * 2  # remesh gives quads -> tris
if voxel > 0 and nf > target:
    dm = ob.modifiers.new("decimate", "DECIMATE")
    dm.ratio = target / nf
    bpy.ops.object.modifier_apply(modifier="decimate")
if voxel > 0:
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
me = ob.data
# Flat shading, and no NORMAL attribute in the GLB (glTF viewers then use
# flat face normals). At ~300K faces this looks smooth, and it stays clean
# where the decoder's triangle winding is inconsistent: smooth vertex
# normals turn those spots into dark cracks, flat + double-sided does not.
for p_ in me.polygons:
    p_.use_smooth = False

# Colour each vertex from the TRELLIS.2 voxel colour field (k-NN, IDW)
from mathutils import kdtree
kd = kdtree.KDTree(len(P))
for i, pt in enumerate(P):
    kd.insert(pt, i)
kd.balance()
n = len(me.vertices)
co = np.empty(n * 3, np.float32)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)
C = np.empty((n, 3), np.float32)
eps = 1e-4
for i in range(n):
    hits = kd.find_n(co[i], 4)
    w = np.array([1.0 / (h[2] + eps) for h in hits])
    C[i] = (S[[h[1] for h in hits]] * w[:, None]).sum(0) / w.sum()
C = np.clip(C, 0, 1) ** 2.2  # sRGB -> linear for Blender
ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
rgba = np.concatenate([C, np.ones((n, 1), np.float32)], 1)
ca.data.foreach_set("color", rgba.ravel())
print("FACES", len(me.polygons))

# UV unwrap
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004)
bpy.ops.object.mode_set(mode="OBJECT")

# Bake target image
img = bpy.data.images.new("basecolor", tex, tex, alpha=False)
# Pre-fill with the model's average colour so any texel the bake misses
# (tiny/degenerate faces) reads as the surrounding colour, not black.
mean = C.mean(0) ** (1 / 2.2)
img.pixels.foreach_set(np.tile(np.r_[mean, 1.0].astype(np.float32), tex * tex))
mat = bpy.data.materials.new("material")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
col = nt.nodes.new("ShaderNodeVertexColor")
col.layer_name = "Col"
emit = nt.nodes.new("ShaderNodeEmission")
nt.links.new(col.outputs["Color"], emit.inputs["Color"])
outn = nt.nodes["Material Output"]
nt.links.new(emit.outputs["Emission"], outn.inputs["Surface"])
imgnode = nt.nodes.new("ShaderNodeTexImage")
imgnode.image = img
nt.nodes.active = imgnode
ob.data.materials.append(mat)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 1
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = True
    sc.cycles.device = "GPU"
except Exception:
    pass
sc.render.bake.margin = 16
sc.render.bake.margin_type = "EXTEND"
bpy.ops.object.bake(type="EMIT")

# Final material: image -> Principled base color
nt.links.new(imgnode.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(bsdf.outputs["BSDF"], outn.inputs["Surface"])
bsdf.inputs["Roughness"].default_value = rough
bsdf.inputs["Metallic"].default_value = 0.0
nt.nodes.remove(emit)
nt.nodes.remove(col)
img.pack()
me.color_attributes.remove(me.color_attributes["Col"])

bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True,
                          export_image_format="JPEG", export_jpeg_quality=92,
                          export_normals=False)
print("BAKED", out)
