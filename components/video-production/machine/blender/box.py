"""A box or carton, built to its measured front (width × height) with its real
front and back faces; sides and top in the box's own colour. Depth comes from
kit.json "box.depth_ratio" (depth / width), read off a side photo — without one
it is marked unmeasured. Run by Blender:
  blender -b -P box.py -- <kit.json> <out.png> [yaw] [tilt] [w] [h] [transparent] [save.blend]"""
import bpy, bmesh, math, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[sys.argv.index("-P") + 1]).resolve().parent))
import stage
A = stage.args(); kit = json.loads(Path(A["kit"]).read_text()); d = Path(A["kit"]).parent
hw = kit["outline"]["height_over_width"]
H = kit["size_cm"].get("height") or 10.0
W = kit["size_cm"].get("width") or H / hw
D = W * (kit.get("box") or {}).get("depth_ratio", 0.35)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, H / 2)); obj = bpy.context.active_object
obj.scale = (W, D, H); bpy.ops.object.transform_apply(scale=True)
bm = bmesh.new(); bm.from_mesh(obj.data); uv = bm.loops.layers.uv.active or bm.loops.layers.uv.new()   # the cube's own UV layer is the one rendered
for f in bm.faces:
    n = f.normal
    f.material_index = 0 if n.y < -0.5 else (1 if n.y > 0.5 else 2)
    for lp in f.loops:
        x, y, z = lp.vert.co
        u = x / W + 0.5
        if n.y > 0.5:
            u = 1 - u
        lp[uv].uv = (u, z / H)
bm.to_mesh(obj.data); bm.free()
bv = obj.modifiers.new("b", "BEVEL"); bv.width = min(W, D, H) * 0.01; bv.segments = 2
rgb = [stage.lin(c) for c in (kit.get("body_rgb") or [0.5, 0.5, 0.5])]
obj.data.materials.append(stage.mat("front", d, img=kit["labels"]["front"], rough=0.5, clear=0.1))
obj.data.materials.append(stage.mat("back", d, img=kit["labels"]["back"], rough=0.5, clear=0.1))
obj.data.materials.append(stage.mat("side", d, rgb=rgb, rough=0.5, clear=0.1))
stage.shoot([obj], H, W, A["out"], A["RW"], A["RH"], A["transparent"], A["yaw"], A["tilt"], A["save"])
