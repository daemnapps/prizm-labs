"""A squeeze tube, built to its measured outline with its real labels — run by
Blender: blender -b -P tube.py -- <kit.json> <out.png> [yaw_deg] [tilt_deg] [width_px] [height_px] [transparent]
The outline profile, real size, cap colour and label images all come from the
product's kit.json (product_kit.py); nothing here names a product."""
import bpy, bmesh, math, sys, json
from pathlib import Path
a = sys.argv[sys.argv.index("--") + 1:]
kit = json.loads(Path(a[0]).read_text()); out = a[1]
yaw = float(a[2]) if len(a) > 2 else 0.0
tilt = float(a[3]) if len(a) > 3 else 0.0
RW = int(a[4]) if len(a) > 4 else 800
RH = int(a[5]) if len(a) > 5 else 1000
transparent = (a[6] == "1") if len(a) > 6 else False
d = Path(a[0]).parent
H = kit["size_cm"].get("height") or 10.0                      # no hand photo → built to a nominal 10 units, marked so in kit.json
W = kit["size_cm"].get("width") or H / kit["outline"]["height_over_width"]
prof = kit["outline"]["profile"]; SH = kit["outline"]["cap_from"]; capw = kit["outline"]["cap_width"]
def lin(c): return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
cap_rgb = [lin(c) for c in kit["cap_rgb"]] + [1]

bpy.ops.wm.read_factory_settings(use_empty=True)
def interp(t):
    for i in range(len(prof) - 1):
        p0, p1 = prof[i], prof[i + 1]
        if p0[0] <= t <= p1[0]:
            return p0[1] + (p1[1] - p0[1]) * (t - p0[0]) / (p1[0] - p0[0])
    return prof[-1][1]
mesh = bpy.data.meshes.new("tube"); body = bpy.data.objects.new("tube", mesh); bpy.context.scene.collection.objects.link(body)
bm = bmesh.new(); N = 64; steps = 48; rings = []
cap_kit = kit.get("cap") or {}
capH = H * (1 - SH); capR = W * capw / 2
capRy = capR * cap_kit.get("depth_ratio", 1.0)                   # a flip cap is oval; no reading = round
# THE BODY MEETS THE CAP (2 Oct, the owner saw the tube's bottom stick out past the
# cap like a shelf): the measured front outline is kept down to a short band
# above the cap, where the body narrows onto it — bottom width = cap width x
# meet_width, bottom depth = cap depth x meet_depth — and the depth grows from
# the flat crimp to that, never past it.
bk = kit.get("body") or {}
end_half = capR * bk.get("meet_width", 1.02); end_depth = capRy * bk.get("meet_depth", 1.05)
band = bk.get("meet_band", 0.06); curve = bk.get("depth_curve", 0.6)
def smooth(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
for i in range(steps + 1):
    t = SH * i / steps; half = W * interp(t) / 2
    if t > SH - band:
        k = smooth((t - (SH - band)) / band); half = half + (end_half - half) * k
    depth = max(0.05, end_depth * (t / SH) ** curve)    # flat at the crimp, meets the cap's depth at the shoulder
    z = H * (1 - t)
    rings.append([bm.verts.new((half * math.cos(2 * math.pi * j / N), depth * math.sin(2 * math.pi * j / N), z)) for j in range(N)])
faces = []
for i in range(steps):
    for j in range(N):
        faces.append(bm.faces.new((rings[i][j], rings[i][(j + 1) % N], rings[i + 1][(j + 1) % N], rings[i + 1][j])))
bm.faces.new(list(reversed(rings[0])))
uv = bm.loops.layers.uv.new()
for f in bm.faces:
    back = f.calc_center_median().y > 0
    f.material_index = 1 if back else 0
    for lp in f.loops:
        x, y, z = lp.vert.co
        u = (x / W) + 0.5
        if back: u = 1 - u
        lp[uv].uv = (u, (z - H * (1 - SH)) / H + (1 - SH))
bm.to_mesh(mesh); bm.free()
for p in mesh.polygons: p.use_smooth = True
bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=capR, depth=capH, location=(0, 0, capH / 2)); cap = bpy.context.active_object
cap.scale = (1, capRy / capR, 1); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
cb = bmesh.new(); cb.from_mesh(cap.data)
ring = lambda zz: [e for e in cb.edges if all(abs(v.co.z - zz) < 1e-4 for v in e.verts) and len(e.link_faces) == 2]
bmesh.ops.bevel(cb, geom=ring(-capH / 2), offset=capH * cap_kit.get("bottom_round", 0.11), segments=10, profile=0.5, affect="EDGES")
bmesh.ops.bevel(cb, geom=ring(capH / 2), offset=capH * 0.025, segments=3, profile=0.5, affect="EDGES")
cb.to_mesh(cap.data); cb.free()
# the thumb notch: a shallow rounded recess on the front, measured off the packshot
n = cap_kit.get("notch")                                         # only a notch the photos show
if n:
    nh = capH * (n["bottom"] - n["top"]); nw = 2 * capR * n["width"]; nz = capH * (1 - (n["top"] + n["bottom"]) / 2)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -capRy - 0.4 + n["depth_cm"], nz)); cut = bpy.context.active_object
    cut.scale = (nw, 0.8, nh); bpy.ops.object.transform_apply(scale=True)
    xb = bmesh.new(); xb.from_mesh(cut.data)                        # round the notch's corners, keep its rim crisp
    ys = [e for e in xb.edges if abs(e.verts[0].co.x - e.verts[1].co.x) < 1e-6 and abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6]
    bmesh.ops.bevel(xb, geom=ys, offset=min(nw, nh) * 0.42, segments=12, profile=0.5, affect="EDGES")
    xb.to_mesh(cut.data); xb.free()
    bv = cut.modifiers.new("b", "BEVEL"); bv.width = n["depth_cm"] * 0.5; bv.segments = 4; bv.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = cut; bpy.ops.object.modifier_apply(modifier="b")
    bo = cap.modifiers.new("notch", "BOOLEAN"); bo.operation = "DIFFERENCE"; bo.object = cut; bo.solver = "EXACT"
    bpy.context.view_layer.objects.active = cap; bpy.ops.object.modifier_apply(modifier="notch")
    bpy.data.objects.remove(cut, do_unlink=True)
cap.select_set(True); bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
line_z = capH * (1 - n["line"]) - capH / 2 if n and n.get("line") else 1e6                  # lid parting line, in the cap's own height
def mat(name, img=None, rgb=None, rough=0.42, clear=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = clear
    if img:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(d / img)); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = rgb
    return m
body.data.materials.append(mat("front", img=kit["labels"]["front"], rough=0.38, clear=0.25))
body.data.materials.append(mat("back", img=kit["labels"]["back"], rough=0.38, clear=0.25))
cm = mat("cap", rgb=cap_rgb, rough=0.48, clear=0.12); nt = cm.node_tree; b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sx.inputs[0])
d1 = nt.nodes.new("ShaderNodeMath"); d1.operation = "SUBTRACT"; d1.inputs[1].default_value = line_z; nt.links.new(sx.outputs["Z"], d1.inputs[0])
ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; nt.links.new(d1.outputs[0], ab.inputs[0])
lt = nt.nodes.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.02; nt.links.new(ab.outputs[0], lt.inputs[0])
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; nt.links.new(lt.outputs[0], mx.inputs["Factor"])
ci = {i.identifier: i for i in mx.inputs}; co = {o.identifier: o for o in mx.outputs}
ci["A_Color"].default_value = cap_rgb; ci["B_Color"].default_value = [c * 0.86 for c in cap_rgb[:3]] + [1]
nt.links.new(co["Result_Color"], b.inputs["Base Color"])
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; bp.invert = True
nt.links.new(lt.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
cap.data.materials.clear(); cap.data.materials.append(cm)
for p_ in cap.data.polygons: p_.material_index = 0
for o in (body, cap):
    o.rotation_euler = (math.radians(tilt), 0, math.radians(yaw))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.location = (0, -max(60, max(H, W * 1.25) * 5.7), H / 2); cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.type = "ORTHO"; cam.data.ortho_scale = max(H, W * RH / RW) * 1.6        # no perspective: the outline reads true
bpy.context.scene.camera = cam
for loc, e in (((-18, -30, 22), 3500), ((20, -20, 8), 1200)):
    l = bpy.data.objects.new("l", bpy.data.lights.new("l", "AREA")); l.data.energy = e; l.data.size = 25; l.location = loc
    l.rotation_euler = (math.radians(60), 0, math.radians(-30 if loc[0] < 0 else 30)); bpy.context.scene.collection.objects.link(l)
w = bpy.data.worlds.new("w"); w.use_nodes = True; bg = w.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (1, 1, 1, 1); bg.inputs["Strength"].default_value = 0.8; bpy.context.scene.world = w
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 96
sc.render.resolution_x = RW; sc.render.resolution_y = RH; sc.render.film_transparent = transparent
sc.view_settings.view_transform = "Standard"; sc.render.filepath = out
bpy.ops.render.render(write_still=True)
if len(a) > 7:
    bpy.ops.file.pack_all()                                      # labels travel inside the .blend (Drive copy for the team)
    bpy.ops.wm.save_as_mainfile(filepath=a[7])
