"""A round-section product — bottle, pump bottle, jar, tub — turned on a lathe
from its measured front outline, with its real front (and back, when there is a
back photo) wrapped on. Run by Blender:
  blender -b -P bottle.py -- <kit.json> <out.png> [yaw] [tilt] [w] [h] [transparent] [save.blend]
Everything comes from the product's kit.json (product_kit.py); nothing here names a product."""
import bpy, bmesh, math, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[sys.argv.index("-P") + 1]).resolve().parent))
import stage
A = stage.args(); kit = json.loads(Path(A["kit"]).read_text()); d = Path(A["kit"]).parent
o = kit["outline"]; prof = o["profile"]; hw = o["height_over_width"]
H = kit["size_cm"].get("height") or 10.0                       # no hand photo → nominal 10 units (kit.json says so)
W = kit["size_cm"].get("width") or H / hw
depth_ratio = (kit.get("section") or {}).get("depth_ratio", 1.0)   # round unless the photos show an oval
bpy.ops.wm.read_factory_settings(use_empty=True)


def interp(t):
    for i in range(len(prof) - 1):
        p0, p1 = prof[i], prof[i + 1]
        if p0[0] <= t <= p1[0]:
            return p0[1] + (p1[1] - p0[1]) * (t - p0[0]) / max(1e-9, p1[0] - p0[0])
    return prof[-1][1] if t > prof[-1][0] else prof[0][1]


mesh = bpy.data.meshes.new("product"); obj = bpy.data.objects.new("product", mesh); bpy.context.scene.collection.objects.link(obj)
bm = bmesh.new(); N = 96; steps = 160; rings = []
for i in range(steps + 1):
    t = i / steps; r = max(0.01, W * interp(t) / 2); z = H * (1 - t)
    rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / N), depth_ratio * r * math.sin(2 * math.pi * j / N), z)) for j in range(N)])
for i in range(steps):
    for j in range(N):
        bm.faces.new((rings[i][j], rings[i][(j + 1) % N], rings[i + 1][(j + 1) % N], rings[i + 1][j]))
bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
uv = bm.loops.layers.uv.new()
for f in bm.faces:
    back = f.calc_center_median().y > 0
    f.material_index = 1 if back else 0
    for lp in f.loops:
        x, y, z = lp.vert.co
        u = x / W + 0.5
        if back:
            u = 1 - u
        lp[uv].uv = (u, z / H)
bm.to_mesh(mesh); bm.free()
for p in mesh.polygons:
    p.use_smooth = True
fin = kit.get("finish") or {}
obj.data.materials.append(stage.mat("front", d, img=kit["labels"]["front"], rough=fin.get("roughness", 0.35), clear=0.3))
obj.data.materials.append(stage.mat("back", d, img=kit["labels"]["back"], rough=fin.get("roughness", 0.35), clear=0.3))
stage.shoot([obj], H, W, A["out"], A["RW"], A["RH"], A["transparent"], A["yaw"], A["tilt"], A["save"])
