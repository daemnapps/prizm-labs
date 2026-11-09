"""Runs inside Blender (motion.py `blocking` and `program` start it): a blocking spec in, the blocking out.

    blender -b -P blocking_blender.py -- <spec.json> <out dir>

Writes into <out dir>: f-0001.png ... (the stand-in render, unless "render": false), pose.json (every person's exact
skeleton per frame, projected through the camera: OpenPose's 18 body points, both hands' 21 points, as fractions of the
frame) and camera.json (the camera's own path per frame). Nothing is guessed back from pictures: the skeletons are the
figures' own joints.

Stand-in people (a jointed figure per person: head with a nose, eyes and ears so the face direction reads, torso, arms,
legs), a floor, simple boxes for set pieces, an optional 3D set (a .glb), a camera, and beats, each {"from": s, "to": s,
"who": NAME, ...one action}:
  "walk": [x, y]                     walk to that spot on the floor (turning to go there)
  "walk_to": NAME                    walk to stand in front of that person, facing them
  "reach": "NAME.cheeks|face|mouth|shoulder|chest" or null, "hands": "both|left|right"
                                     the hands travel to that part of that person; null brings them back down
  "mic": NAME or null                one hand holds a mic out to that person's mouth (the right hand)
  "turn": NAME or degrees            turn to face someone or an angle
  "lean": degrees                    lean the upper body forward (+) or back (-); 0 stands up straight
  "nod": count / "shake": count      the head nods / shakes that many times over the beat
  "tilt": degrees                    the head tilts to one side; 0 straightens it
  "laugh": true                      head back, shoulders bounce
Camera: {"at": [x, y, z], "look": [x, y, z], "lens": mm, "handheld": metres of drift,
         "move": {"to": [x, y, z], "look": [x, y, z], "by": s}, or "follow": [{"from": s, "who": NAME, "offset": [dx, dy, dz]}]}
Sizes in metres; a person is 1.7 m tall; x is across the frame, y is away from the camera. No brand, product or person
is named here.
"""
import json
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HOSTED = "SPEC" in globals()      # run inside a hosted 3D project (Higgsfield 3D Jutsu): the spec is written into the code
if not HOSTED:
    argv = sys.argv[sys.argv.index("--") + 1:]
    SPEC = json.load(open(argv[0]))
    OUT = argv[1]
FPS = int(SPEC.get("fps") or 16)
SECS = float(SPEC.get("seconds") or 5)
W, H = SPEC.get("size") or [480, 854]

if HOSTED:                       # the project keeps its own set; only the last rehearsal is cleared
    for o in [o for o in bpy.data.objects if o.get("rehearsal")]:
        bpy.data.objects.remove(o, do_unlink=True)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
BEFORE = set(bpy.data.objects)
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, max(2, int(round(SECS * FPS)))
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = next((e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in engines), "BLENDER_WORKBENCH")
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"      # true colours: skin against clothes against the set
if not HOSTED:
    sc.render.filepath = OUT.rstrip("/") + "/f-"


def frame(t):
    return 1 + int(round(float(t) * FPS))


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
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
bpy.context.object.data.materials.append(mat("floor", SPEC.get("floor") or [0.76, 0.68, 0.52], 0.9))
for prop in SPEC.get("props") or []:          # boxes for set pieces: {"at": [x, y, z], "size": [w, d, h], "color": [...]}
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
# bone: (head, tail, parent) in the figure's own space; the figure faces -Y before it is turned; .R is the person's right
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
# OpenPose's 18 points, each a rest point riding on one bone
OP18 = [("head", (0, -0.1, 1.62)), ("spine", (0, 0, 1.40)),
        ("upper_arm.R", (-0.20, 0, 1.40)), ("forearm.R", (-0.23, 0.04, 1.12)), ("hand.R", (-0.24, -0.01, 0.87)),
        ("upper_arm.L", (0.20, 0, 1.40)), ("forearm.L", (0.23, 0.04, 1.12)), ("hand.L", (0.24, -0.01, 0.87)),
        ("thigh.R", (-0.10, 0, 0.92)), ("shin.R", (-0.11, -0.02, 0.48)), ("shin.R", (-0.11, 0, 0.06)),
        ("thigh.L", (0.10, 0, 0.92)), ("shin.L", (0.11, -0.02, 0.48)), ("shin.L", (0.11, 0, 0.06)),
        ("head", (-0.038, -0.088, 1.66)), ("head", (0.038, -0.088, 1.66)), ("head", (-0.098, -0.005, 1.63)), ("head", (0.098, -0.005, 1.63))]


def hand_rest(s):
    """A hand's 21 points at rest (hanging, palm in): the wrist, then thumb and four fingers, four points each."""
    x = 0.24 * s
    pts = [(x, -0.01, 0.87)]
    pts += [(x, -0.03, 0.85), (x, -0.045, 0.83), (x, -0.055, 0.81), (x, -0.06, 0.79)]
    for j in range(4):
        y = -0.025 + 0.017 * j
        pts += [(x, y, 0.83), (x, y, 0.80), (x, y, 0.78), (x, y, 0.76)]
    return pts


def facing_angle(at, target_at):
    d = Vector((target_at[0] - at[0], target_at[1] - at[1]))
    return math.atan2(d.x, -d.y)          # a turn about Z that points the figure's front (-Y) along d


def _bind(o, arm, bone):
    mw = o.matrix_world.copy()
    o.parent, o.parent_type, o.parent_bone = arm, "BONE", bone
    o.matrix_world = mw


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
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    people[p["name"]] = {"arm": arm, "spec": p}
    arm.hide_render = True

for name, P in people.items():           # who faces whom at the start
    f = P["spec"].get("face")
    a = P["arm"]
    if isinstance(f, str) and f in people:
        a.rotation_euler = (0, 0, facing_angle(P["spec"]["at"], people[f]["spec"]["at"]))
    elif f is not None:
        a.rotation_euler = (0, 0, math.radians(float(f)))
    a.keyframe_insert("rotation_euler", frame=1)
    a.keyframe_insert("location", frame=1)

# targets: points on a person, in that person's own space (they move with the person); L/R = the target's own side
TARGETS = {"cheeks": {"L": (0.085, -0.04, 1.6), "R": (-0.085, -0.04, 1.6)}, "face": {"L": (0.03, -0.12, 1.62), "R": (-0.03, -0.12, 1.62)},
           "shoulder": {"L": (0.2, -0.08, 1.38), "R": (-0.2, -0.08, 1.38)}, "chest": {"L": (0.07, -0.12, 1.28), "R": (-0.07, -0.12, 1.28)},
           "mouth": {"L": (0.0, -0.3, 1.56), "R": (0.0, -0.3, 1.56)}}
iks = {}


def ik(who, side, tgt, part):
    """One reach target per (person, hand, target): several reaches blend by their weights, so a hand can travel from
    one person's face to the next."""
    key = (who, side, tgt, part)
    if key not in iks:
        arm = people[who]["arm"]
        e = bpy.data.objects.new(f"reach-{who}-{side}-{tgt}-{part}", None)
        sc.collection.objects.link(e)
        e.parent = people[tgt]["arm"]
        e.location = TARGETS[part][{"L": "R", "R": "L"}[side]] if part != "mouth" else TARGETS["mouth"]["L"]
        c = arm.pose.bones["forearm." + side].constraints.new("IK")
        c.target, c.chain_count, c.influence = e, 2, 0.0
        c.keyframe_insert("influence", frame=1)
        iks[key] = c
    return iks[key]


def weigh(c, f0, f1, to):
    c.keyframe_insert("influence", frame=f0)
    c.influence = to
    c.keyframe_insert("influence", frame=f1)


def bone_turn(who, bone, f0, f1, axis, deg):
    pb = people[who]["arm"].pose.bones[bone]
    pb.keyframe_insert("rotation_euler", frame=f0)
    r = list(pb.rotation_euler)
    r[axis] = math.radians(deg)
    pb.rotation_euler = r
    pb.keyframe_insert("rotation_euler", frame=f1)


def wobble(who, bone, f0, f1, axis, count, deg):
    pb = people[who]["arm"].pose.bones[bone]
    base = list(pb.rotation_euler)
    pb.keyframe_insert("rotation_euler", frame=f0)
    steps = max(2, int(count) * 2)
    for k in range(1, steps + 1):
        r = list(base)
        r[axis] = base[axis] + (math.radians(deg) * (1 if k % 2 else -0.4) if k < steps else 0)
        pb.rotation_euler = r
        pb.keyframe_insert("rotation_euler", frame=f0 + round((f1 - f0) * k / steps))


def square(who, tgt, f0, f1):
    arm = people[who]["arm"]
    here, them = where(who, f0), where(tgt, f0)
    want = facing_angle(here, them)
    now = arm.rotation_euler[2]
    turn = (want - now + math.pi) % (2 * math.pi) - math.pi
    if abs(turn) > math.radians(20):
        arm.keyframe_insert("rotation_euler", frame=f0)
        arm.rotation_euler = (0, 0, now + turn)
        arm.keyframe_insert("rotation_euler", frame=f1)


def where(who, f):
    sc.frame_set(f)
    return people[who]["arm"].matrix_world.translation.copy()


beats = sorted(SPEC.get("beats") or [], key=lambda b: float(b["from"]))
for b in beats:
    who = b["who"]
    if who not in people:
        continue
    f0, f1 = frame(b["from"]), max(frame(b["from"]) + 1, frame(b["to"]))
    sc.frame_set(f0)                 # every property at its animated value where this beat starts
    arm = people[who]["arm"]
    if "walk" in b or "walk_to" in b:
        here = where(who, f0)
        if b.get("walk_to") in people:
            them = where(b["walk_to"], f1)
            d = Vector((here.x - them.x, here.y - them.y))
            d = d.normalized() if d.length > 1e-3 else Vector((0, -1))
            dest = (them.x + d.x * 0.5, them.y + d.y * 0.5)
        else:
            dest = tuple(b["walk"])
        arm.keyframe_insert("location", frame=f0)
        arm.keyframe_insert("rotation_euler", frame=f0)
        if math.dist((here.x, here.y), dest) > 0.15:
            arm.rotation_euler = (0, 0, facing_angle((here.x, here.y), dest))
            arm.keyframe_insert("rotation_euler", frame=min(f1, f0 + 4))
        arm.location = (dest[0], dest[1], 0)
        arm.keyframe_insert("location", frame=f1)
        if b.get("walk_to") in people:
            arm.rotation_euler = (0, 0, facing_angle(dest, (them.x, them.y)))
            arm.keyframe_insert("rotation_euler", frame=f1)
    if "reach" in b:
        sides = {"both": ["L", "R"], "left": ["L"], "right": ["R"]}[b.get("hands") or "both"]
        for side in sides:
            for (w, s, t, part), c in iks.items():        # whatever this hand was holding, it lets go
                if w == who and s == side and c.influence > 0:
                    weigh(c, f0, f1, 0.0)
            if b["reach"]:
                tgt, part = (b["reach"].split(".") + ["face"])[:2]
                if tgt in people and part in TARGETS:
                    weigh(ik(who, side, tgt, part), f0, f1, 1.0)
        if b["reach"] and b["reach"].split(".")[0] in people and b["reach"].split(".")[0] != who:
            square(who, b["reach"].split(".")[0], f0, f1)        # people square up to whoever they reach for
    if "mic" in b:
        for (w, s, t, part), c in iks.items():
            if w == who and s == "R" and c.influence > 0:
                weigh(c, f0, f1, 0.0)
        if b["mic"] in people:
            weigh(ik(who, "R", b["mic"], "mouth"), f0, f1, 1.0)
    if "turn" in b:
        t = b["turn"]
        arm.keyframe_insert("rotation_euler", frame=f0)
        here = where(who, f0)
        arm.rotation_euler = (0, 0, facing_angle(here, where(t, f0)) if isinstance(t, str) and t in people else math.radians(float(t)))
        arm.keyframe_insert("rotation_euler", frame=f1)
    if "lean" in b:
        bone_turn(who, "spine", f0, f1, 0, -float(b["lean"]))
    if "tilt" in b:
        bone_turn(who, "head", f0, f1, 2, float(b["tilt"]))
    if "nod" in b:
        wobble(who, "head", f0, f1, 0, b["nod"], -14)
    if "shake" in b:
        wobble(who, "head", f0, f1, 1, b["shake"], 22)
    if b.get("laugh"):
        wobble(who, "head", f0, f1, 0, 3, 16)
        wobble(who, "spine", f0, f1, 0, 3, 5)

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
follow = sorted(cs.get("follow") or [], key=lambda x: float(x.get("from") or 0))
if follow:                                   # the operator walks with a person: same offset, eased, every other frame
    cp, lp = Vector(cam.location), Vector(look.location)
    for fr in range(1, sc.frame_end + 1, 2):
        t = (fr - 1) / FPS
        seg = [x for x in follow if float(x.get("from") or 0) <= t] or follow[:1]
        who = seg[-1]["who"]
        if who not in people:
            continue
        pos = where(who, fr)
        off = Vector(seg[-1].get("offset") or [0.9, -2.6, 1.5])
        flat_off = Vector((off.x, off.y))
        if flat_off.length < 2.2:                                  # a phone held closer than 2.2 m loses the group
            flat_off = (flat_off.normalized() if flat_off.length > 1e-3 else Vector((0, -1))) * 2.2
        want_c = Vector((pos.x + flat_off.x, pos.y + flat_off.y, off.z if off.z > 0.8 else 1.5))   # z: the phone's height
        want_l = Vector((pos.x, pos.y, 1.4))
        cp, lp = cp.lerp(want_c, 0.25), lp.lerp(want_l, 0.35)
        cam.location, look.location = cp, lp
        cam.keyframe_insert("location", frame=fr)
        look.keyframe_insert("location", frame=fr)
shake = float(cs.get("handheld") or 0)        # metres of handheld drift
if shake:
    for fr in range(1, sc.frame_end + 1, 2):
        sc.frame_set(fr)
        base = cam.location.copy()
        t = fr / FPS
        cam.location = base + Vector((shake * math.sin(t * 2.3), shake * 0.5 * math.sin(t * 3.1), shake * 0.7 * math.sin(t * 1.7 + 1)))
        cam.keyframe_insert("location", frame=fr)

# ---------------------------------------------------------------- the skeletons as objects (hosted: rendered to video)
LIMBS = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13), (1, 0),
         (0, 14), (14, 16), (0, 15), (15, 17)]
COLORS = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0),
          (0, 255, 85), (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255),
          (170, 0, 255), (255, 0, 255), (255, 0, 170), (255, 0, 85)]


def flat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1)
    return m


def sticks(name, arm):
    """OpenPose sticks riding the figure's own bones: each limb a two-point mesh bound to its two bones, thickened."""
    for n, (a, b) in enumerate(LIMBS):
        (ba, pa), (bb, pb_) = OP18[a], OP18[b]
        me = bpy.data.meshes.new(f"stick-{name}-{n}")
        me.from_pydata([pa, pb_], [(0, 1)], [])
        o = bpy.data.objects.new(f"stick-{name}-{n}", me)
        sc.collection.objects.link(o)
        o.parent = arm                      # the figure's own space: the bones bend it, the figure carries it
        for k, bone in enumerate((ba, bb)):
            g = o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)
            g.add([k], 1.0, "REPLACE")
        o.modifiers.new("arm", "ARMATURE").object = arm
        o.modifiers.new("skin", "SKIN")
        for v in me.skin_vertices[0].data:
            v.radius = (0.022, 0.022)
        me.materials.append(flat(f"limb-{n}", [c * 0.6 for c in COLORS[n]]))
        o["rehearsal_stick"] = True
        o.hide_render = True
    sc.frame_set(1)                         # every figure at rest where the scene starts
    for j, (bone, rest) in enumerate(OP18):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=arm.matrix_world @ Vector(rest), segments=12, ring_count=6)
        o = bpy.context.object
        o.data.materials.append(flat(f"joint-{j}", COLORS[j]))
        _bind(o, arm, bone)
        o["rehearsal_stick"] = True
        o.hide_render = True


if HOSTED:
    for name, P in people.items():
        sticks(name, P["arm"])
    for o in set(bpy.data.objects) - BEFORE:
        o["rehearsal"] = True
    sc.camera.name = "CAM_rehearsal"
    result = {"people": list(people), "beats": len(beats), "frames": sc.frame_end, "fps": FPS,
              "objects": len(set(bpy.data.objects) - BEFORE)}

# ---------------------------------------------------------------- the exact skeletons and the camera path
if not HOSTED:
    os.makedirs(OUT, exist_ok=True)


    def project(co):
        v = world_to_camera_view(sc, cam, co)
        inside = v.z > 0 and -0.02 <= v.x <= 1.02 and -0.02 <= v.y <= 1.02
        return [round(v.x, 4), round(1 - v.y, 4), 1.0 if inside else 0.0]


    def on_bone(arm, bone, rest):
        pb = arm.pose.bones[bone]
        return arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ Vector(rest)


    frames, campath = [], []
    names = list(people)
    fov_h = 2 * math.atan(36 / 2 / cam.data.lens)
    for fr in range(1, sc.frame_end + 1):
        sc.frame_set(fr)
        cw = cam.matrix_world.translation
        rows = []
        for i, name in enumerate(names):
            arm = people[name]["arm"]
            body = [project(on_bone(arm, b, r)) for b, r in OP18]
            head_c, nose = on_bone(arm, "head", (0, 0, 1.63)), on_bone(arm, "head", (0, -0.1, 1.62))
            fwd, to_cam = (nose - head_c).normalized(), (cw - head_c).normalized()
            if fwd.dot(to_cam) < 0.15:            # facing away: the eyes and nose are not seen
                for j in (0, 14, 15):
                    body[j][2] = 0.0
            for j, s in ((16, -1), (17, 1)):        # an ear on the far side of the head is not seen
                ear = on_bone(arm, "head", (0.098 * s, -0.005, 1.63))
                if (ear - head_c).normalized().dot(to_cam) < -0.25:
                    body[j][2] = 0.0
            hands = [{"side": {"L": "left", "R": "right"}[sd], "points": [project(on_bone(arm, "hand." + sd, q))[:2] for q in hand_rest(s)]}
                     for sd, s in (("L", 1), ("R", -1))]
            xs = [q[0] for q in body if q[2]] or [0.5]
            ys = [q[1] for q in body if q[2]] or [0.5]
            rows.append({"id": i, "name": name, "body": body, "hands": hands, "face": [],
                         "box": [round(min(xs), 4), round(min(ys), 4), round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4)]})
        frames.append({"t": round((fr - 1) / FPS, 3), "people": [r for r in rows if any(q[2] for q in r["body"])]})
        d = (look.matrix_world.translation - cw)
        campath.append([math.atan2(d.x, d.y), math.atan2(d.z, math.hypot(d.x, d.y)), d.length])
    json.dump({"width": W, "height": H, "fps": FPS, "names": names, "frames": frames, "exact": True},
              open(os.path.join(OUT, "pose.json"), "w"), separators=(",", ":"))
    fov_v = fov_h * H / W
    steps = [[0.0, 0.0, 1.0, 0.0, 99]]
    for a, b in zip(campath, campath[1:]):
        steps.append([round((b[0] - a[0]) / fov_h, 5), round(-(b[1] - a[1]) / fov_v, 5), round(a[2] / b[2], 5), 0.0, 99])
    json.dump({"steps": steps}, open(os.path.join(OUT, "camera-steps.json"), "w"))

    if SPEC.get("render", True):
        bpy.ops.render.render(animation=True)
