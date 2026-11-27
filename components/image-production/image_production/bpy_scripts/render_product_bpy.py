"""Runs INSIDE Blender (never imported by the library). One product render from
its kit's 3D model, background transparent, physically posed.

    blender -b --python render_product_bpy.py -- <spec.json>

The spec is written by `image_production/product3d.py`; every number in it comes
from the kit's `model/render3d.json` or from the caller. Nothing here names a
brand or a product. Units: 1 Blender unit = 1 cm (the kit declares it).

Writes: spec["out"] (the product, with its contact shadow in the alpha),
spec["mask_out"] (the product alone, no shadow) and spec["meta_out"] (where the
product sits in the picture, its contact point, and px per cm at that point).
"""
import json
import math
import sys

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

spec = json.loads(open(sys.argv[sys.argv.index("--") + 1]).read())
model = spec["model"]
pose = spec.get("pose") or {}
camspec = spec.get("camera") or {}
light = spec.get("light") or {}


def keep_only(root_name):
    """Keep the product hierarchy of the kit's blend, drop its studio."""
    root = bpy.data.objects[root_name]
    keep = {root}
    changed = True
    while changed:
        changed = False
        for o in bpy.data.objects:
            if o.parent in keep and o not in keep:
                keep.add(o)
                changed = True
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    return root, keep


def world_verts(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in objs:
        if o.type not in ("MESH", "CURVE") or o.hide_render or not getattr(o, "visible_camera", True):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world.copy()
        out.extend(mw @ v.co for v in me.vertices)
        ev.to_mesh_clear()
    return out


def material(name, rgb, metallic=0.0, rough=0.4):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m


def lin(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]


bpy.ops.wm.open_mainfile(filepath=model["blend"])
sc = bpy.context.scene
root, parts = keep_only(model.get("root", "product"))
for name in model.get("hide", []):
    if name in bpy.data.objects:
        bpy.data.objects[name].hide_render = True

# ── the holder, when the pose rests the product in one ───────────────────────
holder = spec.get("holder") or None
assembly = list(parts)
if holder and holder.get("kind") == "cup-from-product":
    # A cradle shaped from the product's own back half, scaled out so the
    # product sits in it with a gap: the holder it leans back in.
    body = bpy.data.objects[holder["body"]]
    vs = world_verts([body])
    lo = Vector([min(v[i] for v in vs) for i in range(3)])
    hi = Vector([max(v[i] for v in vs) for i in range(3)])
    centre = (lo + hi) / 2
    s = holder.get("scale", [1.1, 1.1, 1.1])
    me = body.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.transform(bm, matrix=body.matrix_world, verts=bm.verts)
    for v in bm.verts:
        d = v.co - centre
        v.co = centre + Vector((d.x * s[0], d.y * s[1], d.z * s[2])) + Vector(holder.get("shift_cm", [0, 0, 0]))
    cut_y = lo.y + (hi.y - lo.y) * holder.get("cut_frac", 0.5)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                           plane_co=(0, cut_y, 0), plane_no=(0, -1, 0), clear_outer=True)
    rim_pts = [e for e in bm.edges if e.is_boundary]
    rbm = bmesh.new()
    vmap = {}
    for e in rim_pts:
        for v in e.verts:
            if v not in vmap:
                vmap[v] = rbm.verts.new(v.co)
        rbm.edges.new((vmap[e.verts[0]], vmap[e.verts[1]]))
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(material("holder-shell", lin(holder.get("shell", "#16161A")),
                                 metallic=holder.get("shell_metallic", 0.6),
                                 rough=holder.get("shell_rough", 0.32)))
    for p in me.polygons:
        p.use_smooth = True
        p.material_index = 0
    cup = bpy.data.objects.new("holder-cup", me)
    sc.collection.objects.link(cup)
    sol = cup.modifiers.new("wall", "SOLIDIFY")
    sol.thickness = holder.get("wall_cm", 0.25)
    sol.offset = 1.0
    for _ in range(int(holder.get("rim_smooth", 8))):       # the cut edge is faceted; a rim is not
        bmesh.ops.smooth_vert(rbm, verts=rbm.verts[:], factor=0.5,
                              use_axis_x=True, use_axis_y=False, use_axis_z=True)
    rim_me = bpy.data.meshes.new("rim")
    rbm.to_mesh(rim_me)
    rbm.free()
    rim = bpy.data.objects.new("holder-rim", rim_me)
    sc.collection.objects.link(rim)
    bpy.context.view_layer.objects.active = rim
    for o in sc.objects:
        o.select_set(o is rim)
    bpy.ops.object.convert(target="CURVE")
    rim = bpy.context.view_layer.objects.active
    rim.data.bevel_depth = holder.get("rim_cm", 0.14)
    rim.data.bevel_resolution = 4
    rim.data.materials.append(material("holder-rim", lin(holder.get("rim", "#D9D9DE")),
                                       metallic=1.0, rough=0.1))
    off = holder.get("product_offset_cm", [0, 0, 0])
    root.location = root.location + Vector(off)
    root.rotation_euler.z += math.radians(holder.get("product_yaw_deg", 0.0))
    assembly += [cup, rim]

rig = bpy.data.objects.new("rig", None)
sc.collection.objects.link(rig)
bpy.context.view_layer.update()
for o in assembly:
    if o.parent is None:
        mw = o.matrix_world.copy()
        o.parent = rig
        o.matrix_world = mw

# ── the pose: lean back (top away from the face side), turn, settle down ─────
tilt = math.radians(pose.get("tilt_back_deg", 0.0))
yaw = math.radians(pose.get("yaw_deg", 0.0))
rig.rotation_euler = (-tilt, 0.0, yaw)
bpy.context.view_layer.update()
vs = world_verts(assembly)
minz = min(v.z for v in vs)
cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2
cy = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
rig.location = (-cx, -cy, -minz)
bpy.context.view_layer.update()
vs = world_verts(assembly)
lo = Vector([min(v[i] for v in vs) for i in range(3)])
hi = Vector([max(v[i] for v in vs) for i in range(3)])
contact = [v for v in vs if v.z < lo.z + 0.08]
cpt = Vector((sum(v.x for v in contact) / len(contact), sum(v.y for v in contact) / len(contact), 0.0))

# ── the camera ───────────────────────────────────────────────────────────────
az = math.radians(camspec.get("azimuth", 0.0))
el = math.radians(camspec.get("elevation", 0.0))
target = (lo + hi) / 2
radius = max((v - target).length for v in vs)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
direction = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
if camspec.get("ortho"):
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = radius * 2.1
    dist = radius * 6
else:
    cam.data.lens = camspec.get("focal_mm", 50.0)
    cam.data.sensor_width = 36.0
    fov = 2 * math.atan(18.0 / cam.data.lens)
    dist = radius * 1.08 / math.sin(fov / 2)
cam.data.clip_end = dist * 10
cam.location = target + direction * dist
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

# ── the light: key / fill / rim / top, biased by direction and warmth ───────
for o in list(sc.objects):
    if o.type == "LIGHT":
        bpy.data.objects.remove(o, do_unlink=True)
warm = max(-1.0, min(1.0, float(light.get("warmth", 0.0))))
if warm >= 0:
    tint = (1.0, 1.0 - 0.16 * warm, 1.0 - 0.38 * warm)
else:
    tint = (1.0 + 0.2 * warm, 1.0 + 0.08 * warm, 1.0)
strength = float(light.get("strength", 1.0))


def area(name, az_deg, el_deg, power, size, colour, shadow=True):
    a = math.radians(az_deg) + az
    e = math.radians(el_deg)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = power * (radius / 6.0) ** 2
    ld.size = size * radius
    ld.color = colour
    ld.use_shadow = shadow
    ob = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(ob)
    ob.location = target + d * radius * 4
    ob.rotation_euler = (target - ob.location).to_track_quat("-Z", "Y").to_euler()


key_az = float(light.get("azimuth", -40.0))     # relative to the camera; negative = from screen-left
key_el = float(light.get("elevation", 40.0))
area("key", key_az, key_el, 9000 * strength, 1.2, tint)
area("fill", -key_az * 0.9, 12, 2400 * strength * light.get("fill", 1.0), 2.0, tint, shadow=False)
area("rim", 180 - key_az * 0.6, 45, 7000 * strength * light.get("rim", 1.0), 0.8, (1, 1, 1), shadow=False)
area("top", 0, 85, 1600 * strength, 2.5, tint, shadow=False)

world = bpy.data.worlds.new("w3d")
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
amb = float(light.get("ambient", 0.16))
bg.inputs["Color"].default_value = (amb * tint[0], amb * tint[1], amb * tint[2], 1)

bpy.ops.mesh.primitive_plane_add(size=radius * 30, location=(0, 0, 0))
ground = bpy.context.active_object
ground.is_shadow_catcher = True

# ── render ───────────────────────────────────────────────────────────────────
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = int(spec.get("samples", 64))
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = spec.get("view_transform", "Standard")
size = int(spec.get("size_px", 1024))
sc.render.resolution_x = size
sc.render.resolution_y = size
sc.render.resolution_percentage = 100

if spec.get("shadow", True):
    sc.render.filepath = spec["out"]
    bpy.ops.render.render(write_still=True)
ground.hide_render = True
sc.render.filepath = spec["mask_out"]
bpy.ops.render.render(write_still=True)


def px(p):
    c = world_to_camera_view(sc, cam, p)
    return [c.x * sc.render.resolution_x, (1 - c.y) * sc.render.resolution_y]


right = (cam.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
a, b = px(cpt), px(cpt + right * 1.0)
meta = {
    "size": [sc.render.resolution_x, sc.render.resolution_y],
    "contact_px": a,
    "px_per_cm_at_contact": math.hypot(b[0] - a[0], b[1] - a[1]),
    "assembly_cm": [round(hi[i] - lo[i], 3) for i in range(3)],
    "camera": {"azimuth": camspec.get("azimuth", 0.0), "elevation": camspec.get("elevation", 0.0),
               "focal_mm": None if camspec.get("ortho") else cam.data.lens,
               "ortho": bool(camspec.get("ortho")), "distance_cm": round(dist, 2)},
    "pose": pose, "holder": (holder or {}).get("kind"),
    "light": {"azimuth": key_az, "elevation": key_el, "warmth": warm, "strength": strength},
}
open(spec["meta_out"], "w").write(json.dumps(meta, indent=1))
print("RENDER3D-OK")
