"""Reusable Blender sets for product stills in the 3D Jutsu NOVA project (cb659331-a37b-4316-ae3f-b34139c20c3c).

Installed in that project as the text block `product_sets`, so a later session calls it in one line instead of building a set by hand:

    g = {}; exec(bpy.data.texts["product_sets"].as_string(), g); result = g["make"](artifacts, PARAMS)

Run it with scene_builder_3d_run_python. PARAMS for each ad and the fixed print words live in scene_templates.py.
This file runs inside Blender only. If the project ever loses the text block, paste this file in and run it once.
"""
import bpy, math, random
from mathutils import Vector, Matrix

CM = 0.01

def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _mat(name, hexv, rough=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    h = hexv.lstrip("#")
    b.inputs["Base Color"].default_value = (*[_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)], 1)
    b.inputs["Roughness"].default_value = rough
    return m

def _set(name):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o)
    else:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c

def _mesh(coll, name, verts, faces, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o

def _box(coll, name, w, h, t, mat):
    x, y = w / 2, h / 2
    v = [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0), (-x, -y, t), (x, -y, t), (x, y, t), (-x, y, t)]
    return _mesh(coll, name, v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], mat)

def _nova(coll, name, matrix):
    # a linked copy of the true-size product; the copy must not carry the project's asset id
    o = bpy.data.objects["HERO_nova"].copy()
    if "hf_id" in o:
        del o["hf_id"]
    coll.objects.link(o)
    o.name = name
    o.hide_render = False
    o.hide_viewport = False
    o.matrix_world = matrix
    return o

def _cam(coll, name, loc, target, lens):
    d = bpy.data.cameras.new(name)
    d.lens = lens
    o = bpy.data.objects.new(name, d)
    coll.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o

def _sun(coll, name, euler, energy, angle=18):
    d = bpy.data.lights.new(name, "SUN")
    d.energy = energy
    d.angle = math.radians(angle)
    o = bpy.data.objects.new(name, d)
    coll.objects.link(o)
    o.rotation_euler = [math.radians(a) for a in euler]

def _disc(coll, name, r, t, mat, hole=0.0, n=36):
    v, f = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        v += [(r * c, r * s, 0), (r * c, r * s, t), (hole * c, hole * s, 0), (hole * c, hole * s, t)]
        j, k = 4 * i, 4 * ((i + 1) % n)
        f += [(j + 1, k + 1, k + 3, j + 3), (j, j + 2, k + 2, k), (j, k, k + 1, j + 1), (j + 2, j + 3, k + 3, k + 2)]
    return _mesh(coll, name, v, f, mat)

def _dress(c, p, W, H, place):
    """The concept's world, from the brief. props [{shape: box|disc|ring, x, y, w, h, color, spin}] in fractions of the
    frame (w and h of its width); bits {count, colors, seed, clear: [[top, bottom], ...]}: no bit lands in a clear band,
    which is how the text area stays clean."""
    for i, q in enumerate(p.get("props") or []):
        m = _mat("set_prop%d_%s" % (i, p["name"]), q["color"], 0.5)
        w = q["w"] * W
        if q["shape"] == "box":
            o = _box(c, "prop%d" % i, w, q.get("h", q["w"]) * W, 0.002, m)
        else:
            o = _disc(c, "prop%d" % i, w / 2, 0.002, m, hole=w * 0.42 if q["shape"] == "ring" else 0)
        place(o, q["x"], q["y"], q.get("spin", 0))
    b = p.get("bits")
    if b:
        rnd = random.Random(b.get("seed", 7))
        n = 0
        while n < b["count"]:
            fx, fy = rnd.uniform(.02, .98), rnd.uniform(.02, .98)
            if any(t <= fy <= u for t, u in b.get("clear") or []):
                continue
            s = rnd.uniform(0.0015, 0.005)
            o = _box(c, "bit%d" % n, s, s, 0.0005, _mat("set_bit%d_%s" % (n % len(b["colors"]), p["name"]), b["colors"][n % len(b["colors"])]))
            place(o, fx, fy, rnd.uniform(0, 180))
            n += 1

def _flat_view(p, tilt, rolls):
    """A product seen face-on and flat, turned only in its own plane: a side or over-the-top angle makes it read thicker
    than it is. Any other view has to be asked for by name."""
    if p.get("view", "flat") == "flat" and (tilt > 3 or any(rolls)):
        raise ValueError("flat view: the camera stays square to the product and the product does not roll")

def tabletop(p):
    """Overhead or high-angle surface shot. frame_w_cm, ground (hex), lens, tilt (degrees off square),
    notes [{x, y, w, h, spin, color}] and products [{x, y, spin, roll}] in fractions of the frame."""
    c = _set("SET_" + p["name"])
    W = p["frame_w_cm"] * CM
    H = W * 16 / 9
    lens = p.get("lens", 100)
    _flat_view(p, p.get("tilt", 0), [f.get("roll", 0) for f in p.get("products") or []])
    tilt = math.radians(p.get("tilt", 0))
    d = H * lens / 36
    g = _box(c, "ground", W * 4, H * 4, 0.0001, _mat("set_ground_" + p["name"], p["ground"], 0.75))
    g.location.z = -0.0001
    xy = lambda f: ((f["x"] - 0.5) * W, (0.5 - f["y"]) * H)
    for i, n in enumerate(p.get("notes") or []):
        o = _box(c, "note%d" % i, n["w"] * W, n["h"] * H, 0.0003, _mat("set_note_" + p["name"], n["color"], 0.8))
        o.location = (*xy(n), 0.0001)
        o.rotation_euler.z = math.radians(n.get("spin", 0))
    for i, f in enumerate(p.get("products") or []):
        m = Matrix.Rotation(math.radians(f.get("spin", 0)), 4, "Z") @ Matrix.Rotation(math.radians(f.get("roll", 0)), 4, "Y") \
            @ Matrix.Rotation(math.radians(-90), 4, "X")
        m.translation = (*xy(f), bpy.data.objects["HERO_nova"].dimensions.y / 2)
        _nova(c, "nova%d" % i, m)
    def place(o, fx, fy, spin):
        o.location = ((fx - 0.5) * W, (0.5 - fy) * H, 0.0004)
        o.rotation_euler.z = math.radians(spin)
    _dress(c, p, W, H, place)
    _sun(c, "sun", p.get("sun", (32, -28, 0)), p.get("energy", 3.0))
    cam = _cam(c, "CAM_" + p["name"], (0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), lens)
    return c, cam

def float_hero(p):
    """A product floating upright in front of a flat backdrop. frame_w_cm, backdrop (hex), lens, x, y (fractions),
    tilt (degrees), optional ribbon {radius_cm, width_cm, tilt, color} and particles {count, colors, seed}."""
    c = _set("SET_" + p["name"])
    W = p["frame_w_cm"] * CM
    H = W * 16 / 9
    lens = p.get("lens", 135)
    _flat_view(p, 0, [])
    d = H * lens / 36
    b = _box(c, "backdrop", W * 5, H * 5, 0.0001, _mat("set_ground_" + p["name"], p["backdrop"], 0.9))
    b.rotation_euler.x = math.radians(90)
    b.location.y = 0.12
    px, pz = (p["x"] - 0.5) * W, (0.5 - p["y"]) * H
    m = Matrix.Rotation(math.radians(p.get("tilt", 0)), 4, "Y")
    m.translation = (px, 0, pz)
    _nova(c, "nova0", m)
    r = p.get("ribbon")
    if r:
        a, w, n = r["radius_cm"] * CM, r["width_cm"] * CM, 72
        tilt = Matrix.Rotation(math.radians(r.get("tilt", 14)), 4, "Y")
        v = []
        for i in range(n):
            t = 2 * math.pi * i / n
            for s in (-0.5, 0.5):
                q = tilt @ Vector((a * math.cos(t), a * 0.8 * math.sin(t), s * w + 0.008 * math.sin(2 * t)))
                v.append((q.x + px, q.y, q.z + pz - 0.02))
        f = [(2 * i, 2 * i + 1, (2 * i + 3) % (2 * n), (2 * i + 2) % (2 * n)) for i in range(n)]
        _mesh(c, "ribbon", v, f, _mat("set_ribbon_" + p["name"], r["color"], 0.4))
    def place(o, fx, fy, spin):
        o.location = ((fx - 0.5) * W, -0.03, (0.5 - fy) * H)
        o.rotation_euler = (math.radians(90), math.radians(spin), 0)
    _dress(c, p, W, H, place)
    q = p.get("particles")
    if q:
        rnd = random.Random(q.get("seed", 7))
        for i in range(q["count"]):
            s = rnd.uniform(0.0015, 0.005)
            o = _box(c, "bit%d" % i, s, s, 0.0005, _mat("set_bit%d_%s" % (i % len(q["colors"]), p["name"]), q["colors"][i % len(q["colors"])]))
            t = rnd.uniform(0, 2 * math.pi)
            o.location = (px + rnd.uniform(0.3, 1) * W * 0.5 * math.cos(t), -0.02, pz + rnd.uniform(0.3, 1) * 0.09 * math.sin(t))
            o.rotation_euler = [rnd.uniform(0, 6) for _ in range(3)]
    _sun(c, "sun", p.get("sun", (40, -32, 0)), p.get("energy", 3.2))
    return c, _cam(c, "CAM_" + p["name"], (0, -d, 0), (0, 0, 0), lens)

def render(artifacts, name, set_name, cam, product_only=False, px=(576, 1024), samples=8):
    """Render one set alone; every other set and the loose hero are hidden for the render and restored after.
    The worker allows five minutes per call: render one set per call, at low samples."""
    s = bpy.context.scene
    keep = []
    def flip(x, attr, v):
        keep.append((x, attr, getattr(x, attr)))
        setattr(x, attr, v)
    for c in bpy.data.collections:
        if c.name.startswith("SET_"):
            flip(c, "hide_render", c.name != set_name)
    for o in s.collection.objects:
        if o.type in ("MESH", "LIGHT"):
            flip(o, "hide_render", True)
    if product_only:
        for o in bpy.data.collections[set_name].objects:
            if o.type == "MESH" and not o.name.startswith("nova"):
                flip(o, "is_holdout", True)
        flip(s.render, "film_transparent", True)
    flip(s, "camera", cam)
    flip(s.render, "resolution_x", px[0])
    flip(s.render, "resolution_y", px[1])
    flip(s.eevee, "taa_render_samples", samples)
    try:
        t = artifacts.file(name=name, media_type="image/png")
        s.render.image_settings.media_type = "IMAGE"
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_mode = "RGBA" if product_only else "RGB"
        s.render.filepath = t.path
        s.render.use_file_extension = False
        bpy.ops.render.render(write_still=True)
        t.publish()
    finally:
        for x, attr, v in reversed(keep):
            setattr(x, attr, v)

KINDS = {"tabletop": tabletop, "float_hero": float_hero}

def make(artifacts, p):
    """One call per brief: build the set and render the blockout."""
    c, cam = KINDS[p["kind"]](p)
    render(artifacts, p["name"] + "-render.png", c.name, cam)
    return {"set": c.name, "camera": cam.name, "objects": len(c.objects)}

def product_pass(artifacts, name, px=(864, 1536)):
    """The true product alone from the set's camera, transparent around it, for laying back over the print."""
    render(artifacts, name + "-product.png", "SET_" + name, bpy.data.objects["CAM_" + name], product_only=True, px=px)
