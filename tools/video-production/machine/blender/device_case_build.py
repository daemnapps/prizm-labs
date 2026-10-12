# the device charging case, modelled by hand from the studio material: the case turntable gif (closed lid frame 37, the base with its
# engraved charging panel frame 49) and the brand's instructional case still (open, 2500px).
# Exec'd inside parts.py. Axes: z = the case's long axis (stood upright like the renders), x = across,
# y = depth; the lid is at -y (toward the camera at yaw 0), the base and its charging panel at +y.
# Hinge on the +x long side, latch button on the -x side (as the open still shows).
import json as _json, os
C = M["custom_spec"]
L, W = H, C["width"]
DB, DL = C["base_depth"], C["lid_depth"]
NS = C.get("outline_n", 2.7)          # superellipse of the closed outline (frame 37: between a stadium and an ellipse)
SEGS = 160


CAP = C.get("cap_frac", 0.23) * L      # frame 37: straight long sides, each end an elliptical cap 0.23 of the length deep


def _inside(x, z, a, hl, cap):
    if abs(x) > a:
        return False
    hz = hl - cap
    if abs(z) <= hz:
        return True
    return (x / a) ** 2 + ((abs(z) - hz) / cap) ** 2 <= 1.0


def outline(u, sx=1.0, sz=1.0):
    """the closed case's outline (a stadium with elliptical ends), scaled; u = angle round the centre."""
    a, hl, cap = (W / 2) * sx, (L / 2) * sz, CAP * sz
    dx, dz = math.cos(u), math.sin(u); lo, hi = 0.0, max(a, hl) * 1.5
    for _ in range(40):
        mid = (lo + hi) / 2
        if _inside(dx * mid, dz * mid, a, hl, cap):
            lo = mid
        else:
            hi = mid
    return dx * lo, dz * lo


def shell(name, depth, sign, m, steps=24, inset=1.0, y0=0.0):
    """half a pebble: the outline at the split plane (y = y0), shrinking as (1 - t^m)^(1/m) to the outer face."""
    me = bpy.data.meshes.new(name); ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    bm = bmesh.new(); rings = []
    for i in range(steps + 1):
        t = i / steps; s = (1 - t ** m) ** (1 / m) if t < 1 else 0.0
        s = max(s, 0.0)
        ring = []
        for j in range(SEGS):
            x, z = outline(2 * math.pi * j / SEGS, s * inset, (1 - (1 - s) * C.get("z_round", 0.55)) * inset)
            ring.append(bm.verts.new((x, y0 + sign * depth * t, z + L / 2)))
        rings.append(ring)
    for i in range(steps):
        for j in range(SEGS):
            jj = (j + 1) % SEGS
            f = (rings[i][j], rings[i][jj], rings[i + 1][jj], rings[i + 1][j])
            bm.faces.new(f if sign < 0 else tuple(reversed(f)))
    bm.faces.new(rings[0] if sign > 0 else list(reversed(rings[0])))          # the split-plane face
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return ob


def cut(host, tool):
    mo = host.modifiers.new("cut", "BOOLEAN"); mo.operation = "DIFFERENCE"; mo.object = tool; mo.solver = "EXACT"
    bpy.context.view_layer.objects.active = host; bpy.ops.object.modifier_apply(modifier="cut"); bpy.data.objects.remove(tool)


mats_ = M["materials"]
m_body = material("case-gloss", mats_["gloss"]); m_in = material("case-inside", mats_["inside"])
m_mirror = material("mirror", mats_["mirror"]); m_panel = material("panel", mats_["panel"])

def profile_solid(name, prof, mats_idx):
    """a closed solid swept round the outline: prof = [(sx, sz, y, mat), ...] from one pole (sx = 0) to the other."""
    me = bpy.data.meshes.new(name); ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    bm = bmesh.new(); uv = bm.loops.layers.uv.new(); rings = []
    for sx, sz, y, _m in prof:
        if sx <= 1e-6:
            rings.append(bm.verts.new((0.0, y, L / 2)))
        else:
            rings.append([bm.verts.new((outline(2 * math.pi * j / SEGS, sx, sz)[0], y, outline(2 * math.pi * j / SEGS, sx, sz)[1] + L / 2)) for j in range(SEGS)])
    for i in range(len(prof) - 1):
        A, B = rings[i], rings[i + 1]; mi = prof[i + 1][3]
        for j in range(SEGS):
            jj = (j + 1) % SEGS
            if isinstance(A, list) and isinstance(B, list):
                f = bm.faces.new((A[j], A[jj], B[jj], B[j]))
            elif isinstance(B, list):
                f = bm.faces.new((A, B[jj], B[j]))
            else:
                f = bm.faces.new((A[j], A[jj], B))
            f.material_index = mi
    for f in bm.faces:
        for lp in f.loops:
            x, _, z = lp.vert.co
            lp[uv].uv = (0.5 + x / (W * C["panel"]["sx"]), (z - L / 2) / (L * C["panel"]["sz"]) + 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return ob


mats_ = M["materials"]
m_body = material("case-gloss", mats_["gloss"]); m_in = material("case-inside", mats_["inside"])
m_mirror = material("mirror", mats_["mirror"]); m_panel = material("panel", mats_["panel"])
ZR = C.get("z_round", 0.55)


def outer(s_, depth, m, sign):
    t = (1 - s_ ** m) ** (1 / m)
    return (s_, 1 - (1 - s_) * ZR, sign * depth * t)


P_ = C["panel"]; MB = C.get("base_m", 3.2); wi = C["well_inset"]; fl_ = DB - C["floor"]
yp = DB * C["panel_y"]
prof = [(0.0, 0.0, yp, 2), (P_["sx"] * 0.5, P_["sz"] * 0.5, yp, 2), (P_["sx"], P_["sz"], yp, 2), (P_["sx"] * 1.0, P_["sz"] * 1.0, yp + 0.0001, 2)]
s0 = max(P_["sx"], P_["sz"]) + 0.03
o0 = outer(s0, DB, MB, +1)
prof += [(P_["sx"] + 0.015, P_["sz"] + 0.015, o0[2], 0)]
for i in range(1, 25):
    s_ = s0 + (1 - s0) * i / 24
    o = outer(s_, DB, MB, +1); prof.append((o[0], o[1], o[2], 0))
prof += [(1.0, 1.0, 0.0, 0), (wi + 0.02, wi + 0.02, 0.0, 0), (wi, wi, 0.04, 1), (wi * 0.98, wi * 0.98, fl_ * 0.6, 1),
         (wi * 0.93, wi * 0.93, fl_ * 0.95, 1), (wi * 0.85, wi * 0.85, fl_, 1), (wi * 0.4, wi * 0.4, fl_, 1), (0.0, 0.0, fl_, 1)]
# the profile ran back-pole -> outside -> rim -> well -> floor-pole: reverse the well part so it's one strip
base = profile_solid("case-base", prof, None)
base.data.materials.append(m_body); base.data.materials.append(m_in); base.data.materials.append(m_panel)
nt = m_panel.node_tree; b = nt.nodes["Principled BSDF"]
ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(str(d / P_["image"])); ti.extension = "EXTEND"
# projected straight from behind in object space (the panel is flat): x -> u (mirrored, seen from the back), z -> v
tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sp.inputs[0])
mu = nt.nodes.new("ShaderNodeMapRange"); mu.inputs["From Min"].default_value = W * P_["sx"] / 2; mu.inputs["From Max"].default_value = -W * P_["sx"] / 2
mv = nt.nodes.new("ShaderNodeMapRange"); mv.inputs["From Min"].default_value = L / 2 - L * P_["sz"] / 2; mv.inputs["From Max"].default_value = L / 2 + L * P_["sz"] / 2
nt.links.new(sp.outputs["X"], mu.inputs["Value"]); nt.links.new(sp.outputs["Z"], mv.inputs["Value"])
cv = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(mu.outputs[0], cv.inputs[0]); nt.links.new(mv.outputs[0], cv.inputs[1]); nt.links.new(cv.outputs[0], ti.inputs["Vector"])
bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(ti.outputs["Color"], bw.inputs[0])
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = P_.get("bump", 0.6); bp.inputs["Distance"].default_value = 0.02
nt.links.new(bw.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = hexrgb(mats_["panel"]["base"]); mx.inputs[7].default_value = hexrgb(P_.get("ink", "#4A4A4E"))
iv = nt.nodes.new("ShaderNodeMapRange"); iv.inputs["From Min"].default_value = P_.get("lo", 0.25); iv.inputs["From Max"].default_value = P_.get("hi", 0.6)
nt.links.new(bw.outputs[0], iv.inputs["Value"]); nt.links.new(iv.outputs[0], mx.inputs[0]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
pn = base
bpy.ops.object.select_all(action="DESELECT")

# the latch button on the -x side of the base, at the split line (frame 37: 18% of the length, centred a little high)
B_ = C["button"]
bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=1, vertices=48, location=(-W / 2 - B_["proud"] / 2 + 0.05, 0.25, L / 2 + B_["z_off"] * L))
bt = bpy.context.active_object; bt.name = "latch"; bt.rotation_euler = (0, math.radians(90), 0)
bt.scale = (B_["len"] * L / 2, B_["thick"] / 2, B_["proud"] + 0.1)
bv = bt.modifiers.new("bev", "BEVEL"); bv.width = 0.04; bv.segments = 3
bt.data.materials.append(m_body)

# ── lid: the shallow domed half; inside it, the mirror ────────────────────────────────────────────────
ML = C.get("lid_m", 2.3); lp_ = [(0.0, 0.0, -DL, 0)]
for i in range(1, 25):
    o = outer(i / 24, DL, ML, -1); lp_.append((o[0], o[1], o[2], 0))
lp_ += [(1.0, 1.0, 0.0, 0), (C["mirror_inset"] + 0.03, C["mirror_inset"] + 0.03, 0.0, 0), (0.0, 0.0, 0.0, 0)]
lid = profile_solid("case-lid", lp_, None); lid.data.materials.append(m_body)
mm_ = bpy.data.meshes.new("mirror"); mr = bpy.data.objects.new("mirror", mm_); sc.collection.objects.link(mr); bm = bmesh.new()
cen = bm.verts.new((0, 0.004, L / 2)); ring = []
for j in range(SEGS):
    x, z = outline(2 * math.pi * j / SEGS, C["mirror_inset"], C["mirror_inset"])
    ring.append(bm.verts.new((x, 0.004, z + L / 2)))
for j in range(SEGS):
    bm.faces.new((cen, ring[j], ring[(j + 1) % SEGS]))
bm.to_mesh(mm_); bm.free(); mr.data.materials.append(m_mirror); mr.parent = lid

objs_c = [base, bt, lid, mr]

# open: the lid swings about the hinge on the +x long side
ang = C.get("open_deg", 0.0)
if ang:
    hinge = bpy.data.objects.new("hinge", None); sc.collection.objects.link(hinge); hinge.location = (W / 2 - 0.15, -0.05, 0)
    lid.parent = hinge; lid.location = (-(W / 2 - 0.15), 0.05, 0)
    hinge.rotation_euler = (0, 0, math.radians(-ang))   # negative open_deg swings the lid out toward the camera
    objs_c.append(hinge)

# open, with the device lying in the tray (its back in the base, bristles toward the lid), from the device's own kit
if ang and C.get("device_kit") and not os.environ.get("KIT_NO_DEVICE"):
    fk = _json.load(open(str((d / C["device_kit"]).resolve())))
    g2 = dict(globals()); g2.update(H=C.get("device_height", fk["model_parts"]["height"]), D=fk["model_parts"]["diameter"], M=fk["model_parts"],
                                     d=(d / C["device_kit"]).resolve().parent)
    before = set(bpy.data.objects.keys())
    exec(open(str(Path(__file__).resolve().parent / fk["model_parts"]["custom"])).read(), g2)
    fl = bpy.data.objects.new("device", None); sc.collection.objects.link(fl)
    for o in g2["custom_objs"]:
        if o.parent is None:
            o.parent = fl
    fl.location = (C["device_x"], C["device_y"], C["device_z"]); fl.rotation_mode = "ZXY"
    fl.rotation_euler = (math.radians(C["device_tilt"]), math.radians(C.get("device_roll", 0)), math.radians(C.get("device_yaw", 0)))
    objs_c.append(fl)

# the lid mirror's picture: the studio still shows the device's bristle field filling the mirror, bright and finely dotted,
# while the device itself faces the camera. A card carrying that field sits where the mirror's reflection looks — seen
# only in reflections (never by the camera, never lighting anything), so it shows in the mirror and nowhere else.
MC = C.get("mirror_card")
if ang and MC:
    bpy.context.view_layer.update()
    mw_ = mr.matrix_world; p0 = mw_ @ Vector((0, 0.004, L / 2))
    n_ = (mw_.to_3x3() @ Vector((0, 1, 0))).normalized()
    from mathutils import Euler
    _R = Euler((math.radians(tilt), math.radians(float(os.environ.get("KIT_ROLL", 0))), math.radians(yaw)), "ZXY").to_matrix()
    dv = (_R.inverted() @ Vector((0, 1, 0))).normalized()   # the camera's view direction, in the case's own frame (the whole product is turned later)
    if n_.dot(-dv) < 0:
        n_ = -n_
    rr = (dv - 2 * dv.dot(n_) * n_).normalized()
    bpy.ops.mesh.primitive_plane_add(size=1, location=p0 + rr * MC.get("dist", 2.0) * W)
    cd_ = bpy.context.active_object; cd_.name = "mirror-card"; cd_.scale = (MC.get("size", 2.5) * W, MC.get("size", 2.5) * W * 1.6, 1)
    cd_.rotation_euler = (p0 - cd_.location).to_track_quat("Z", "Y").to_euler()
    for att in ("visible_camera", "visible_diffuse", "visible_shadow", "visible_transmission", "visible_volume_scatter"):
        setattr(cd_, att, False)
    mc_ = bpy.data.materials.new("mirror-card"); mc_.use_nodes = True; cn = mc_.node_tree; cn.nodes.clear()
    co = cn.nodes.new("ShaderNodeOutputMaterial"); ce = cn.nodes.new("ShaderNodeEmission")
    tc_ = cn.nodes.new("ShaderNodeTexCoord"); vo = cn.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = MC.get("dot_scale", 8.0)
    vo.inputs["Randomness"].default_value = MC.get("dot_random", 0.0)    # the bristles stand in a regular grid
    cn.links.new(tc_.outputs["Object"], vo.inputs["Vector"])
    dm = cn.nodes.new("ShaderNodeMapRange"); dm.inputs["From Min"].default_value = 0.18; dm.inputs["From Max"].default_value = 0.42
    cn.links.new(vo.outputs["Distance"], dm.inputs["Value"])
    mx_ = cn.nodes.new("ShaderNodeMix"); mx_.data_type = "RGBA"; mx_.inputs[6].default_value = hexrgb(MC.get("dot", "#7A7A7C")); mx_.inputs[7].default_value = hexrgb(MC.get("field", "#D4D4D2"))
    cn.links.new(dm.outputs[0], mx_.inputs[0])
    gr = cn.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"; cn.links.new(tc_.outputs["Generated"], gr.inputs["Vector"])
    # generated coords run 0..1 over the card: centre it
    vm = cn.nodes.new("ShaderNodeVectorMath"); vm.operation = "SUBTRACT"; vm.inputs[1].default_value = (0.5, 0.5, 0.5); cn.links.new(tc_.outputs["Generated"], vm.inputs[0])
    vs = cn.nodes.new("ShaderNodeVectorMath"); vs.operation = "SCALE"; vs.inputs["Scale"].default_value = MC.get("falloff", 1.6); cn.links.new(vm.outputs[0], vs.inputs[0])
    cn.links.new(vs.outputs[0], gr.inputs["Vector"])
    st_ = cn.nodes.new("ShaderNodeMath"); st_.operation = "MULTIPLY"; st_.inputs[1].default_value = MC.get("strength", 1.0); cn.links.new(gr.outputs["Fac"], st_.inputs[0])
    cn.links.new(mx_.outputs[2], ce.inputs["Color"]); cn.links.new(st_.outputs[0], ce.inputs["Strength"]); cn.links.new(ce.outputs[0], co.inputs[0])
    cd_.data.materials.append(mc_); objs_c.append(cd_)

custom_objs = objs_c
