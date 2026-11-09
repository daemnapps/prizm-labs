"""Runs inside Blender (motion.py `blocking` starts it): a blocking spec in, frames of the blocking out.

    blender -b -P blocking_blender.py -- <spec.json> <frames dir>

Stand-in people (a jointed figure per person: head with a nose and eyes so the face direction reads, torso, arms, legs),
a floor, an optional 3D set (a .glb, e.g. a world exported from a 3D set builder), a camera that can move, and beats:
  {"from": 1.0, "to": 2.0, "who": "A", "hands": "both|left|right", "reach": "B.cheeks|B.face|B.shoulder|null"}
      the hands travel to the target between `from` and `to`; "reach": null brings them back down
  {"from": 0, "to": 3, "who": "A", "walk": [x, y]}      the person walks to that spot on the floor
  {"from": 2, "to": 2.5, "who": "B", "turn": "A"|degrees}  the person turns to face someone or an angle
Sizes in metres; a person is 1.7 m tall. Nothing here names a brand, product or person.
"""
import json
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SPEC = json.load(open(argv[0]))
OUT = argv[1]
FPS = int(SPEC.get("fps") or 16)
SECS = float(SPEC.get("seconds") or 5)
W, H = SPEC.get("size") or [480, 854]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, int(round(SECS * FPS))
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = next((e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in engines), "BLENDER_WORKBENCH")
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"      # true colours: the tracker reads skin against clothes against the set
sc.render.filepath = OUT.rstrip("/") + "/f-"


def frame(t):
    return 1 + int(round(t * FPS))


def mat(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


# ---------------------------------------------------------------- the world
world = bpy.data.worlds.new("w")
sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (*(SPEC.get("sky") or [0.55, 0.7, 0.9]), 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
bpy.ops.object.light_add(type="SUN", location=(2, -3, 6))
sun = bpy.context.object
sun.data.energy = 4.5
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
bpy.context.object.data.materials.append(mat("floor", SPEC.get("floor") or [0.76, 0.68, 0.52], 0.9))
for prop in SPEC.get("props") or []:          # simple boxes for set pieces: {"at": [x, y, z], "size": [w, d, h], "color": [...]}
    bpy.ops.mesh.primitive_cube_add(size=1, location=prop["at"])
    o = bpy.context.object
    o.scale = prop["size"]
    o.data.materials.append(mat("prop", prop.get("color") or [0.95, 0.95, 0.95]))
if SPEC.get("set"):
    bpy.ops.import_scene.gltf(filepath=SPEC["set"])
    for o in bpy.context.selected_objects:
        if o.parent is None:
            o.location = Vector(SPEC.get("set_at") or [0, 0, 0])
            o.scale *= float(SPEC.get("set_scale") or 1)

# ---------------------------------------------------------------- the people
# bone: (head, tail) in the figure's own space; the figure faces -Y before it is turned
BONES = {
    "hips": ((0, 0, 0.92), (0, 0, 1.05), None), "spine": ((0, 0, 1.05), (0, 0, 1.40), "hips"),
    "neck": ((0, 0, 1.40), (0, 0, 1.52), "spine"), "head": ((0, 0, 1.52), (0, 0, 1.74), "neck"),
    "upper_arm.L": ((0.20, 0, 1.40), (0.23, 0.04, 1.12), "spine"), "forearm.L": ((0.23, 0.04, 1.12), (0.24, -0.01, 0.87), "upper_arm.L"),
    "hand.L": ((0.24, -0.01, 0.87), (0.24, -0.02, 0.79), "forearm.L"),
    "upper_arm.R": ((-0.20, 0, 1.40), (-0.23, 0.04, 1.12), "spine"), "forearm.R": ((-0.23, 0.04, 1.12), (-0.24, -0.01, 0.87), "upper_arm.R"),
    "hand.R": ((-0.24, -0.01, 0.87), (-0.24, -0.02, 0.79), "forearm.R"),
    "thigh.L": ((0.10, 0, 0.92), (0.11, -0.02, 0.48), "hips"), "shin.L": ((0.11, -0.02, 0.48), (0.11, 0, 0.06), "thigh.L"),
    "thigh.R": ((-0.10, 0, 0.92), (-0.11, -0.02, 0.48), "hips"), "shin.R": ((-0.11, -0.02, 0.48), (-0.11, 0, 0.06), "thigh.R"),
}
RADIUS = {"spine": 0.16, "hips": 0.15, "neck": 0.05, "upper_arm": 0.05, "forearm": 0.043, "hand": 0.035, "thigh": 0.075, "shin": 0.055}


def facing_angle(at, target_at):
    d = Vector((target_at[0] - at[0], target_at[1] - at[1]))
    return math.atan2(d.x, -d.y)          # a turn about Z that points the figure's front (-Y) along d


def limb(name, a, b, r, m, arm, bone):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=16, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    _bind(o, arm, bone)
    return o


def ball(loc, r, m, arm, bone, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
    o = bpy.context.object
    o.scale = scale
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    _bind(o, arm, bone)
    return o


def _bind(o, arm, bone):
    mw = o.matrix_world.copy()
    o.parent, o.parent_type, o.parent_bone = arm, "BONE", bone
    o.matrix_world = mw


people = {}
for p in SPEC["people"]:
    bpy.ops.object.armature_add(location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = p["name"]
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    eb.remove(eb[0])
    for n, (h, t, par) in BONES.items():
        e = eb.new(n)
        e.head, e.tail = h, t
        if par:
            e.parent = eb[par]
            e.use_connect = Vector(BONES[par][1]) == Vector(h)
    bpy.ops.object.mode_set(mode="OBJECT")
    skin = mat("skin-" + p["name"], p.get("skin") or [0.78, 0.57, 0.45], 0.5)
    top = mat("top-" + p["name"], p.get("color") or [0.3, 0.4, 0.8])
    legs = mat("legs-" + p["name"], p.get("legs") or [0.2, 0.2, 0.25])
    dark = mat("eye", [0.03, 0.03, 0.03], 0.3)
    for n, (h, t, _) in BONES.items():
        kind = n.split(".")[0]
        if kind == "head":
            ball((0, 0, 1.63), 0.105, skin, arm, n, (0.9, 1.0, 1.15))
            ball((0, -0.1, 1.62), 0.022, skin, arm, n)                       # nose: the way the face points
            for s in (-1, 1):
                ball((0.038 * s, -0.088, 1.66), 0.013, dark, arm, n)          # eyes
                ball((0.098 * s, -0.005, 1.63), 0.022, skin, arm, n)          # ears
        elif kind == "hand":
            ball(Vector(t), 0.04, skin, arm, n, (0.8, 0.5, 1.3))
        elif kind == "spine":
            limb(n, h, t, RADIUS["spine"], top, arm, n).scale = (1.15, 0.7, 1)
        elif kind == "hips":
            limb(n, h, t, RADIUS["hips"], legs, arm, n).scale = (1.05, 0.7, 1)
        else:
            m = top if kind in ("upper_arm",) else legs if kind in ("thigh", "shin") else skin
            limb(n, h, t, RADIUS[kind], m, arm, n)
            ball(Vector(t), RADIUS[kind] * 1.05, m, arm, n)                   # the joint
    arm.location = (p["at"][0], p["at"][1], 0)
    people[p["name"]] = {"arm": arm, "spec": p}
    arm.show_in_front = False
    arm.hide_render = True

# who faces whom at the start
for name, P in people.items():
    f = P["spec"].get("face")
    a = P["arm"]
    if isinstance(f, str) and f in people:
        a.rotation_euler = (0, 0, facing_angle(P["spec"]["at"], people[f]["spec"]["at"]))
    elif f is not None:
        a.rotation_euler = (0, 0, math.radians(float(f)))
    a.keyframe_insert("rotation_euler", frame=1)
    a.keyframe_insert("location", frame=1)

# targets: points on a person, in that person's own space (they move with the person)
TARGETS = {"cheeks": {"L": (0.085, -0.04, 1.6), "R": (-0.085, -0.04, 1.6)}, "face": {"L": (0.03, -0.12, 1.62), "R": (-0.03, -0.12, 1.62)},
           "shoulder": {"L": (0.2, -0.08, 1.38), "R": (-0.2, -0.08, 1.38)}}
iks = {}


def ik(who, side):
    key = (who, side)
    if key not in iks:
        arm = people[who]["arm"]
        e = bpy.data.objects.new(f"reach-{who}-{side}", None)
        sc.collection.objects.link(e)
        c = arm.pose.bones["forearm." + side].constraints.new("IK")
        c.target, c.chain_count, c.influence = e, 2, 0.0
        c.keyframe_insert("influence", frame=1)
        iks[key] = (e, c)
    return iks[key]


for b in SPEC.get("beats") or []:
    who, f0, f1 = b["who"], frame(b["from"]), frame(b["to"])
    arm = people[who]["arm"]
    if "reach" in b:
        sides = {"both": ["L", "R"], "left": ["L"], "right": ["R"]}[b.get("hands") or "both"]
        for side in sides:
            e, c = ik(who, side)
            c.influence = c.influence
            c.keyframe_insert("influence", frame=f0)
            if b["reach"]:
                tgt, part = b["reach"].split(".")
                # the reacher's left hand goes to the target's right side when they face each other
                other = {"L": "R", "R": "L"}[side]
                e.parent = people[tgt]["arm"]
                e.location = TARGETS[part][other]
                c.influence = 1.0
            else:
                c.influence = 0.0
            c.keyframe_insert("influence", frame=f1)
    if "walk" in b:
        arm.keyframe_insert("location", frame=f0)
        arm.location = (b["walk"][0], b["walk"][1], 0)
        arm.keyframe_insert("location", frame=f1)
    if "turn" in b:
        arm.keyframe_insert("rotation_euler", frame=f0)
        t = b["turn"]
        here = arm.location
        arm.rotation_euler = (0, 0, facing_angle(here, people[t]["arm"].location) if isinstance(t, str) else math.radians(float(t)))
        arm.keyframe_insert("rotation_euler", frame=f1)

# ---------------------------------------------------------------- the camera
cs = SPEC.get("camera") or {}
bpy.ops.object.camera_add(location=cs.get("at") or (1.4, -3.2, 1.5))
cam = bpy.context.object
cam.data.lens = float(cs.get("lens") or 28)
sc.camera = cam
look = bpy.data.objects.new("look", None)
sc.collection.objects.link(look)
look.location = cs.get("look") or (0, 0, 1.3)
tc = cam.constraints.new("TRACK_TO")
tc.target, tc.track_axis, tc.up_axis = look, "TRACK_NEGATIVE_Z", "UP_Y"
cam.keyframe_insert("location", frame=1)
look.keyframe_insert("location", frame=1)
if cs.get("move"):
    mv = cs["move"]
    end = frame(float(mv.get("by") or SECS))
    cam.location = mv.get("to") or cam.location
    cam.keyframe_insert("location", frame=end)
    if mv.get("look"):
        look.location = mv["look"]
        look.keyframe_insert("location", frame=end)
shake = float(cs.get("handheld") or 0)        # metres of handheld drift
if shake:
    for fr in range(1, sc.frame_end + 1, 2):
        sc.frame_set(fr)
        base = cam.location.copy()
        t = fr / FPS
        cam.location = base + Vector((shake * math.sin(t * 2.3), shake * 0.5 * math.sin(t * 3.1), shake * 0.7 * math.sin(t * 1.7 + 1)))
        cam.keyframe_insert("location", frame=fr)

bpy.ops.render.render(animation=True)
