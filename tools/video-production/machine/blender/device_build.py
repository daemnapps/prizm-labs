# the device face brush, modelled by hand from the studio turntable (the store turntable video: front frame 1,
# side frame 39, back frame 61) and the lit CGI still. Exec'd inside parts.py (custom builder), which
# provides: bpy, bmesh, math, Vector, H, D, d (kit folder), M (model_parts), material(), hexrgb(), sc.
# Every number below is read off those frames, in turntable pixels (front: centre x 570, top y 115,
# bottom y 928; side: reference plane x 600), and scaled to the kit's height.
from mathutils.bvhtree import BVHTree
C = M["custom_spec"]
PX_TOP, PX_BOT, CX, XREF = C["px"]["top"], C["px"]["bot"], C["px"]["cx"], C["px"]["xref"]
k = H / (PX_BOT - PX_TOP)


def zc(y):
    return (PX_BOT - y) * k


def interp(tab, y):
    for (y0, v0), (y1, v1) in zip(tab, tab[1:]):
        if y0 <= y <= y1:
            return v0 + (v1 - v0) * (y - y0) / max(1e-9, y1 - y0)
    return tab[0][1] if y < tab[0][0] else tab[-1][1]


# front view: half-width at each row
HALF = [(y, (r - l) / 2) for y, l, r in C["front"]]
# side view: front surface x and back surface x at each row
FRT = [(y, (XREF - x) * k) for y, x, _ in C["side"]]
BAK = [(y, (x - XREF) * k) for y, _, x in C["side"]]
NF, NB = C.get("n_front", 2.6), C.get("n_back", 2.0)
SEG = C.get("seg", 96)


# THE MEASURED BODY (2026-10-09): when the kit carries `sections` — the cross-sections of the model carved from all
# 120 frames of the store's turntable (98.7% silhouette match across 24 angles, vs 95.8% for the three-view outline)
# — the shell follows them; the hand-built detail (pad, bristles, band, ring, back relief) sits on top.
GS = None
if C.get("sections"):
    import json as _j
    _g = _j.load(open(str(d / C["sections"])))
    GA = _g["A"]; GT = [r["t"] for r in _g["rows"]]; GR = [[(v or 0.0) for v in r["r"]] for r in _g["rows"]]
    GS = True
    # the carved model is a little lumpy (it was cut from video frames): smooth round the section and up the body
    for _ in range(int(C.get("sections_smooth", 0))):
        n_ = len(GR)
        GR = [[(sum(GR[i][(j + dj) % GA] for dj in (-2, -1, 0, 1, 2)) / 5) for j in range(GA)] for i in range(n_)]
        GR = [[(GR[i - 1][j] + 2 * GR[i][j] + GR[i + 1][j]) / 4 if 0 < i < n_ - 1 else GR[i][j] for j in range(GA)] for i in range(n_)]


def g_r(t, theta):
    """radius (cm) of the measured section at height fraction t (0 = bottom), angle theta."""
    t = max(GT[0], min(GT[-1], t))
    lo, hi = 0, len(GT) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if GT[mid] <= t:
            lo = mid
        else:
            hi = mid
    ft = (t - GT[lo]) / max(1e-9, GT[hi] - GT[lo])
    a = (math.degrees(theta) % 360.0) / 360.0 * GA; j0 = int(a) % GA; j1 = (j0 + 1) % GA; fa = a - int(a)
    r0 = GR[lo][j0] * (1 - fa) + GR[lo][j1] * fa; r1 = GR[hi][j0] * (1 - fa) + GR[hi][j1] * fa
    return (r0 * (1 - ft) + r1 * ft) * H


def section(y, theta, grow=0.0):
    """point on the body's cross-section at turntable row y, angle theta (0 = +x, -90deg = front)."""
    if GS:
        r = g_r((PX_BOT - y) / (PX_BOT - PX_TOP), theta) + grow
        return Vector((r * math.cos(theta), r * math.sin(theta), zc(y)))
    a = interp(HALF, y) * k + grow
    c, s = math.cos(theta), math.sin(theta)
    x = a * math.copysign(abs(c) ** (2 / (NF if s < 0 else NB)), c)
    if s < 0:
        yy = -(interp(FRT, y) + grow) * abs(s) ** (2 / NF)
    else:
        yy = (interp(BAK, y) + grow) * abs(s) ** (2 / NB)
    return Vector((x, yy, zc(y)))


def loft(name, rows, grow=0.0, ring_fn=None, close=True):
    me = bpy.data.meshes.new(name); ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    bm = bmesh.new(); rings = []
    for i, y in enumerate(rows):
        rings.append([bm.verts.new(ring_fn(i, y, 2 * math.pi * j / SEG) if ring_fn else section(y, 2 * math.pi * j / SEG, grow)) for j in range(SEG)])
    for i in range(len(rings) - 1):
        for j in range(SEG):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % SEG], rings[i + 1][(j + 1) % SEG], rings[i + 1][j]))
    if close:
        if GS:
            c0_ = sum((v.co for v in rings[0]), Vector()) / SEG; c1_ = sum((v.co for v in rings[-1]), Vector()) / SEG
            top = bm.verts.new(c0_ + Vector((0, 0, 0.01))); bot = bm.verts.new(c1_ - Vector((0, 0, 0.01)))
        else:
            top = bm.verts.new(Vector((0, (interp(BAK, rows[0]) - interp(FRT, rows[0])) / 2, zc(rows[0]) + 0.01)))
            bot = bm.verts.new(Vector((0, (interp(BAK, rows[-1]) - interp(FRT, rows[-1])) / 2, zc(rows[-1]) - 0.01)))
        for j in range(SEG):
            bm.faces.new((top, rings[0][(j + 1) % SEG], rings[0][j]))
            bm.faces.new((bot, rings[-1][j], rings[-1][(j + 1) % SEG]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return ob


# ── the shell ────────────────────────────────────────────────────────────────
rows = [PX_TOP + d_ for d_ in (0.3, 0.8, 1.5, 2.5, 4, 6, 8.5, 11.5, 15)] + [y for y in range(int(PX_TOP) + 20, int(PX_BOT) - 20, C.get("row_px", 6))] + [PX_BOT - d_ for d_ in (15, 11.5, 8.5, 6, 4, 2.5, 1.5, 0.8, 0.3)]
body = loft("device-body", rows)
cs = body.modifiers.new("cs", "CORRECTIVE_SMOOTH"); cs.iterations = 6; cs.smooth_type = "SIMPLE"
bpy.context.view_layer.objects.active = body; bpy.ops.object.modifier_apply(modifier="cs")
sub = body.modifiers.new("sub", "SUBSURF"); sub.levels = sub.render_levels = 2
bpy.context.view_layer.objects.active = body; bpy.ops.object.modifier_apply(modifier="sub")


def saddle(edge, theta):
    """a line that runs round the body higher at front and back than at the sides (as the band edges and the
    light ring do in the front and back views): edge = (row at the front centre, row at the side)."""
    yc, ys = edge[0], edge[1]
    if len(edge) > 3 and edge[3] == "x":
        # by the width across (the ring, 2026-10-09: seen from the front the store's ring is one clean arch — a parabola
        # in x — which the angle around the device's flattened front turned into a wave): u = how far out across the body
        x0 = section(yc, theta).x; a = abs(section(yc, 0.0 if x0 >= 0 else math.pi).x) or 1e-6
        u = min(1.0, abs(x0) / a)
        return yc + (ys - yc) * u ** (edge[2] if len(edge) > 2 else 2.0)
    s = abs(math.sin(theta))
    return ys + (yc - ys) * s ** (edge[2] if len(edge) > 2 else 1.5)   # an optional third number: how late it drops


# materials: soft-touch shell, gloss dome below the light ring
mats_ = M["materials"]
m_shell = material("shell", mats_["shell"]); m_dome = material("dome", mats_["dome"])
body.data.materials.append(m_shell); body.data.materials.append(m_dome)
ring_c = C["ring"]
for p in body.data.polygons:
    ctr = p.center
    th = math.atan2(ctr.y, ctr.x)
    if ctr.z < zc(saddle(ring_c["centre_side"], th)):
        p.material_index = 1

# back: the shallow wave ripples near the crown and the debossed wordmark (a bump on the shell's back)
nt = m_shell.node_tree; b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
wz = nt.nodes.new("ShaderNodeMath"); wz.operation = "MULTIPLY"; wz.inputs[1].default_value = 2 * math.pi / (C["waves"]["pitch_px"] * k)
nt.links.new(sep.outputs["Z"], wz.inputs[0])
wx = nt.nodes.new("ShaderNodeMath"); wx.operation = "MULTIPLY"; wx.inputs[1].default_value = 2 * math.pi / (C["waves"]["wave_px"] * k)
nt.links.new(sep.outputs["X"], wx.inputs[0])
wsx = nt.nodes.new("ShaderNodeMath"); wsx.operation = "SINE"; nt.links.new(wx.outputs[0], wsx.inputs[0])
wadd = nt.nodes.new("ShaderNodeMath"); wadd.operation = "MULTIPLY_ADD"; wadd.inputs[1].default_value = 0.35
nt.links.new(wsx.outputs[0], wadd.inputs[0]); nt.links.new(wz.outputs[0], wadd.inputs[2])
ws = nt.nodes.new("ShaderNodeMath"); ws.operation = "SINE"; nt.links.new(wadd.outputs[0], ws.inputs[0])
zr = nt.nodes.new("ShaderNodeMapRange"); zr.inputs["From Min"].default_value = zc(C["waves"]["to_row"]); zr.inputs["From Max"].default_value = zc(C["waves"]["from_row"])
zr.clamp = True; nt.links.new(sep.outputs["Z"], zr.inputs["Value"])
yb = nt.nodes.new("ShaderNodeMapRange"); _bm = C.get("back_mask_cm", [0.0, 0.6])   # the back relief fades out before the sides (it bled round onto the sides at true size)
yb.inputs["From Min"].default_value = _bm[0]; yb.inputs["From Max"].default_value = _bm[1]; nt.links.new(sep.outputs["Y"], yb.inputs["Value"])
mw = nt.nodes.new("ShaderNodeMath"); mw.operation = "MULTIPLY"; nt.links.new(ws.outputs[0], mw.inputs[0]); nt.links.new(zr.outputs[0], mw.inputs[1])
mw2 = nt.nodes.new("ShaderNodeMath"); mw2.operation = "MULTIPLY"; nt.links.new(mw.outputs[0], mw2.inputs[0]); nt.links.new(yb.outputs[0], mw2.inputs[1])
# wordmark on the back: mark.png projected from behind (mirrored so it reads from the back)
mk = C["mark"]
u = nt.nodes.new("ShaderNodeMapRange"); u.inputs["From Min"].default_value = mk["w_cm"] / 2; u.inputs["From Max"].default_value = -mk["w_cm"] / 2
v = nt.nodes.new("ShaderNodeMapRange"); v.inputs["From Min"].default_value = zc(mk["row"]) - mk["h_cm"] / 2; v.inputs["From Max"].default_value = zc(mk["row"]) + mk["h_cm"] / 2
nt.links.new(sep.outputs["X"], u.inputs["Value"]); nt.links.new(sep.outputs["Z"], v.inputs["Value"])
cmb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(u.outputs[0], cmb.inputs[0]); nt.links.new(v.outputs[0], cmb.inputs[1])
ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(str(d / mk["image"])); ti.image.colorspace_settings.name = "Non-Color"; ti.extension = "CLIP"
nt.links.new(cmb.outputs[0], ti.inputs["Vector"])
mb = nt.nodes.new("ShaderNodeMath"); mb.operation = "MULTIPLY"; nt.links.new(ti.outputs["Color"], mb.inputs[0]); nt.links.new(yb.outputs[0], mb.inputs[1])
neg = nt.nodes.new("ShaderNodeMath"); neg.operation = "MULTIPLY_ADD"; neg.inputs[1].default_value = -2.0
nt.links.new(mb.outputs[0], neg.inputs[0]); nt.links.new(mw2.outputs[0], neg.inputs[2])
mc = nt.nodes.new("ShaderNodeMix"); mc.data_type = "RGBA"; mc.inputs[6].default_value = hexrgb(mats_["shell"]["base"]); mc.inputs[7].default_value = hexrgb(mk.get("tone", "#2C2C30"))
nt.links.new(mb.outputs[0], mc.inputs[0]); nt.links.new(mc.outputs[2], b.inputs["Base Color"])
if C.get("back_image"):
    bu = nt.nodes.new("ShaderNodeMapRange"); bu.inputs["From Min"].default_value = C["back_w_cm"] / 2; bu.inputs["From Max"].default_value = -C["back_w_cm"] / 2
    bv_ = nt.nodes.new("ShaderNodeMapRange"); bv_.inputs["From Min"].default_value = 0.0; bv_.inputs["From Max"].default_value = H
    nt.links.new(sep.outputs["X"], bu.inputs["Value"]); nt.links.new(sep.outputs["Z"], bv_.inputs["Value"])
    bc = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(bu.outputs[0], bc.inputs[0]); nt.links.new(bv_.outputs[0], bc.inputs[1])
    bi = nt.nodes.new("ShaderNodeTexImage"); bi.image = bpy.data.images.load(str(d / C["back_image"])); bi.image.colorspace_settings.name = "Non-Color"; bi.extension = "CLIP"
    nt.links.new(bc.outputs[0], bi.inputs["Vector"])
    bm_ = nt.nodes.new("ShaderNodeMath"); bm_.operation = "MULTIPLY"; nt.links.new(bi.outputs["Color"], bm_.inputs[0]); nt.links.new(yb.outputs[0], bm_.inputs[1])
    neg = bm_
    mc.inputs[0].default_value = 0.0
    try:
        nt.links.remove(mc.inputs[0].links[0])
    except Exception:
        pass
bp = nt.nodes.new("ShaderNodeBump")
if nt.nodes.get("grain_bump"):
    nt.links.new(nt.nodes["grain_bump"].outputs["Normal"], bp.inputs["Normal"])
bp = bp; bp.inputs["Strength"].default_value = C.get("back_bump", 0.5); bp.inputs["Distance"].default_value = C.get("back_bump_d", 0.04)
nt.links.new(neg.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])

objs_c = [body]


def strip(name, edge_lo, edge_hi, grow, mat, n=6):
    """a band round the body between two saddle lines, standing proud of the shell by `grow`."""
    def ring_fn(i, y, th):
        t = i / (n - 1)
        yy = saddle(edge_hi, th) + (saddle(edge_lo, th) - saddle(edge_hi, th)) * t
        return section(yy, th, grow)
    ob = loft(name, list(range(n)), ring_fn=ring_fn, close=False)
    sol = ob.modifiers.new("sol", "SOLIDIFY"); sol.thickness = grow * 0.9; sol.offset = -1
    bv = ob.modifiers.new("bev", "BEVEL"); bv.width = grow * 0.35; bv.segments = 2
    ob.data.materials.append(mat)
    return ob


band = C["band"]
m_band = material("band", mats_["band"])
objs_c.append(strip("band", band["bottom"], band["top"], band["proud_cm"], m_band, n=10))
# THE LIGHT CHANGES COLOUR (the owner, 2026-10-09: white, red and green): kit `light_colours` names them; KIT_LIGHT picks one
import os as _os2
LIGHT_HEX = (M.get("light_colours") or {}).get(_os2.environ.get("KIT_LIGHT", ""), mats_["light"]["base"])
m_light = bpy.data.materials.new("light"); m_light.use_nodes = True; ln = m_light.node_tree; ln.nodes.clear()
lo = ln.nodes.new("ShaderNodeOutputMaterial"); le = ln.nodes.new("ShaderNodeEmission"); le.inputs["Color"].default_value = hexrgb(LIGHT_HEX)
le.inputs["Strength"].default_value = mats_["light"].get("strength", 6.0); ln.links.new(le.outputs[0], lo.inputs[0])
objs_c.append(strip("light-ring", ring_c["bottom"], ring_c["top"], ring_c["proud_cm"], m_light, n=4))
if ring_c.get("halo", 0) > 0:      # the glow the ring throws on the shell either side of it (the store frames' soft falloff)
    m_halo = bpy.data.materials.new("halo"); m_halo.use_nodes = True; hn = m_halo.node_tree; hn.nodes.clear()
    ho = hn.nodes.new("ShaderNodeOutputMaterial"); he = hn.nodes.new("ShaderNodeEmission"); he.inputs["Color"].default_value = hexrgb(LIGHT_HEX)
    he.inputs["Strength"].default_value = ring_c["halo"]
    tr = hn.nodes.new("ShaderNodeBsdfTransparent"); mx = hn.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = ring_c.get("halo_alpha", 0.25)
    hn.links.new(tr.outputs[0], mx.inputs[1]); hn.links.new(he.outputs[0], mx.inputs[2]); hn.links.new(mx.outputs[0], ho.inputs[0])
    gp = ring_c.get("halo_px", 6)
    objs_c.append(strip("ring-halo", [ring_c["bottom"][0] + gp, ring_c["bottom"][1] + gp] + list(ring_c["bottom"][2:]), [ring_c["top"][0] - gp, ring_c["top"][1] - gp] + list(ring_c["top"][2:]), ring_c["proud_cm"] * 0.6, m_halo, n=4))

# band detail: the chevron grooves and the three icons (− ⏻ +), as thin dark inlays on the band's front
m_ink = material("groove", mats_["groove"])


def on_band(x_px, y_px, grow, back=False):
    th = -math.pi / 2 + 0.0
    # find theta for this x on the front: x = a cos(theta) -> theta
    if GS:      # the angle whose section point sits at this x, on the front (or back) half
        xc = (x_px - CX) * k
        cands = [(-math.pi + math.pi * i / 360.0) * (-1 if back else 1) for i in range(1, 360)]
        th = min(cands, key=lambda t_: abs(section(y_px, t_).x - xc))
        return section(y_px, th, grow)
    a = interp(HALF, y_px) * k
    xx = max(-0.999, min(0.999, (x_px - CX) * k / a))
    th = math.acos(xx) if back else -math.acos(xx)
    return section(y_px, th, grow)


def polyline(name, pts_px, width_cm, grow, back=False):
    me = bpy.data.meshes.new(name); ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    bm = bmesh.new(); prev = None
    for (x0, y0), (x1, y1) in zip(pts_px, pts_px[1:]):
        steps = max(2, int(math.hypot(x1 - x0, y1 - y0) / 4))
        for s in range(steps + 1):
            x = x0 + (x1 - x0) * s / steps; y = y0 + (y1 - y0) * s / steps
            p = on_band(x, y, grow, back)
            # the stroke's width lies across the stroke, on the surface (a vertical stroke — the ⏻ stem, the
            # sides of its ring — keeps its width; before 2026-10-09 every stroke was widened up-and-down only)
            tan_ = Vector(((x1 - x0) * k, 0.0, -(y1 - y0) * k)); nrm_ = Vector((p.x, p.y, 0.0))
            wv = tan_.cross(nrm_).normalized() * (width_cm / 2) if tan_.length > 1e-9 and nrm_.length > 1e-9 else Vector((0, 0, width_cm / 2))
            l = bm.verts.new(p + wv); r = bm.verts.new(p - wv)
            if prev:
                bm.faces.new((prev[0], prev[1], r, l))
            prev = (l, r)
        prev = None
    bm.to_mesh(me); bm.free(); ob.data.materials.append(m_ink)
    return ob


g = band["proud_cm"] + 0.004
for line in band.get("grooves", []):
    objs_c.append(polyline("groove", line, band["groove_w_cm"], g))
for line in band.get("back_grooves", []):          # the back carries the same chevrons, no icons (store back frame)
    objs_c.append(polyline("groove", line, band["groove_w_cm"], g, back=True))


def arc_t(name, pts, width_cm, grow):
    """a stroke on the body given as (theta, row) points: width across the stroke, on the surface."""
    me = bpy.data.meshes.new(name); ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    bm = bmesh.new(); prev = None
    P3 = [section(yy, th, grow) for th, yy in pts]
    for i_, p in enumerate(P3):
        q0 = P3[max(0, i_ - 1)]; q1 = P3[min(len(P3) - 1, i_ + 1)]
        tan_ = q1 - q0; nrm_ = Vector((p.x, p.y, 0.0))
        wv = tan_.cross(nrm_).normalized() * (width_cm / 2) if tan_.length > 1e-9 else Vector((0, 0, width_cm / 2))
        l = bm.verts.new(p + wv); r = bm.verts.new(p - wv)
        if prev:
            bm.faces.new((prev[0], prev[1], r, l))
        prev = (l, r)
    bm.to_mesh(me); bm.free(); ob.data.materials.append(m_ink)
    return ob


def theta_at(x_px, y_px, back=False):
    xc = (x_px - CX) * k
    cands = [(-math.pi + math.pi * i / 720.0) * (-1 if back else 1) for i in range(1, 720)]
    return min(cands, key=lambda t_: abs(section(y_px, t_).x - xc))


# THE EYE (2026-10-09, store side frame): each front chevron and the back one opposite are the two ends of one
# eye-shaped pair of grooves that runs round the side of the band — top arc up to its peak at the side, bottom arc
# down — so the side of the band shows a tall lens, and the front shows the chevron.
for e_ in band.get("eyes", []):
    tf = theta_at(e_["tip_x"], e_["tip_y"]); tb = theta_at(e_["tip_x"], e_["tip_y"], back=True)
    if e_["tip_x"] < CX:          # the left side: from the front tip the long way round through 180 degrees
        tb = tb - 2 * math.pi if tb > tf else tb
        if tb > tf:
            tb -= 2 * math.pi
    else:
        if tb < tf:
            tb += 2 * math.pi
    for key_, sgn in (("top_y", -1), ("bot_y", 1)):
        pts_ = []
        for q in range(0, 121):
            u = q / 120; th = tf + (tb - tf) * u
            yy = e_["tip_y"] + (e_[key_] - e_["tip_y"]) * math.sin(math.pi * u) ** e_.get("power", 0.8)
            pts_.append((th, yy))
        objs_c.append(arc_t("eye", pts_, band["groove_w_cm"], band["proud_cm"] + 0.004))

# THE BUTTONS (2026-10-09, the owner: "the plus minus and power button need to be protruded more"): − ⏻ + are raised
# strokes standing off the band, in their own lighter satin so their edges catch the light as in the store frame
ip = band.get("icon_proud_cm", 0.0)
m_icon = material("icon", mats_.get("icon", mats_["groove"])) if mats_.get("icon") else m_ink
gi = g + ip / 2


def raise_(ob):
    if ip > 0:
        ob.data.materials.clear(); ob.data.materials.append(m_icon)
        so = ob.modifiers.new("raise", "SOLIDIFY"); so.thickness = ip; so.offset = 0.0
        bv = ob.modifiers.new("round", "BEVEL"); bv.width = ip * 0.35; bv.segments = 2; bv.limit_method = "ANGLE"
    return ob


for icon in band["icons"]:
    kind, x, y, s = icon["kind"], icon["x"], icon["y"], icon["size_px"]
    if kind in ("minus", "plus"):
        objs_c.append(raise_(polyline("icon", [(x - s / 2, y), (x + s / 2, y)], band["icon_w_cm"], gi)))
    if kind == "plus":
        # the vertical stroke, drawn the same way so it stands as proud as the rest
        objs_c.append(raise_(polyline("icon", [(x, y - s / 2), (x, y + s / 2)], band["icon_w_cm"], gi)))
    if kind == "power":
        r = s / 2
        arc = [(x + r * math.sin(math.radians(t)), y - r * math.cos(math.radians(t))) for t in range(35, 330, 12)]
        objs_c.append(raise_(polyline("icon", arc, band["icon_w_cm"], gi)))
        objs_c.append(raise_(polyline("icon", [(x, y - r * 1.05), (x, y - r * 0.05)], band["icon_w_cm"], gi)))

# ── the bristle field: a raised silicone pad (the shell grown by its thickness, cut to the pad's outline),
#    then real nubs on it — fine and dense, the coarse triangle at the crown ───────────────────────────
P = C["pad"]
PADO = P["outline"]
if P.get("xscale"):   # the pad's true width on the face: narrower than its front-view look, which the fanned edge bristles widen
    PADO = [(y_, CX + (l_ - CX) * P["xscale"], CX + (r_ - CX) * P["xscale"]) for y_, l_, r_ in PADO]
    P = dict(P); P["outline"] = [list(r_) for r_ in PADO]
# the pad stands proud of the shell (store side frame): push the shell's front out inside the pad outline,
# with a soft shoulder at its edge
_l0 = [(y, l) for y, l, _ in PADO]; _r0 = [(y, r) for y, _, r in PADO]
pt = P.get("plate_cm", 0.0); edge = P.get("plate_edge_px", 10.0)
if GS and P.get("inset_blur_px"):
    # THE SMOOTH STEP (2026-10-09, side close-up against the store frame): the shell under the bristles sits back by
    # the bristle length, eased by a blurred copy of the pad's outline, so the surface has no crease, no shoulder
    # line and no crown notch; deep inside the pad the bristle tips meet the carved front, at its edge they fade in.
    import numpy as _np
    st_ = 3.0; gx = _np.arange(CX - 520, CX + 520, st_); gy = _np.arange(PX_TOP - 30, PX_BOT + 30, st_)
    Mk = _np.zeros((len(gy), len(gx)))
    for i_, yv in enumerate(gy):
        if PADO[0][0] <= yv <= PADO[-1][0]:
            Mk[i_, (gx >= interp(_l0, yv)) & (gx <= interp(_r0, yv))] = 1.0
    sg = P["inset_blur_px"] / st_; kx = _np.arange(-int(3 * sg) - 1, int(3 * sg) + 2); kk = _np.exp(-kx ** 2 / (2 * sg * sg)); kk /= kk.sum()
    Bm = _np.apply_along_axis(lambda r_: _np.convolve(r_, kk, "same"), 1, Mk)
    Bm = _np.apply_along_axis(lambda c2: _np.convolve(c2, kk, "same"), 0, Bm)
    Bm = _np.clip(Bm * P.get("inset_gain", 1.0), 0.0, 1.0)
    Rw = _np.clip(_np.convolve((Mk.max(axis=1) > 0).astype(float), kk, "same") * P.get("inset_gain", 1.0), 0.0, 1.0)   # the rows the pad spans, eased
    if P.get("inset_top_ramp_px"):   # over the crown the face is not recessed: it rounds over, and the short top bristles sit on it
        rr_ = _np.clip((gy - PADO[0][0]) / P["inset_top_ramp_px"], 0.0, 1.0); Rw = Rw * rr_ * rr_ * (3 - 2 * rr_)
        Bm = Bm * (rr_ * rr_ * (3 - 2 * rr_))[:, None]
    Lin = P.get("tip_inset_cm", P["fine_len_cm"])
    for v in body.data.vertices:
        c_ = v.co
        if c_.y >= 0:
            continue
        yp = PX_BOT - c_.z / k; xp = c_.x / k + CX
        fi = (yp - gy[0]) / st_; fj = (xp - gx[0]) / st_
        i0 = int(max(0, min(len(gy) - 2, fi))); j0 = int(max(0, min(len(gx) - 2, fj))); a_ = min(1, max(0, fi - i0)); b_ = min(1, max(0, fj - j0))
        bv = (Bm[i0, j0] * (1 - a_) + Bm[i0 + 1, j0] * a_) * (1 - b_) + (Bm[i0, j0 + 1] * (1 - a_) + Bm[i0 + 1, j0 + 1] * a_) * b_
        if P.get("inset_face"):
            # THE FLAT FACE (store side frame: the bristles rise out of a flat front that meets the shell flush, no step
            # visible from the side): the whole front-facing surface is recessed, by how squarely it faces front, over
            # the rows the pad spans — the pad's own outline then only decides where bristles stand
            fa, fb = P["inset_face"]
            fs = -c_.y / max(1e-9, math.hypot(c_.x, c_.y))
            wa = max(0.0, min(1.0, (fs - fa) / (fb - fa))); wa = wa * wa * (3 - 2 * wa)
            ri = int(max(0, min(len(gy) - 1, round(fi)))); bv = wa * float(Rw[ri])
        if bv > 1e-4:
            v.co.y += min(Lin * bv, P.get("inset_cap", 0.45) * max(0.0, -c_.y))
elif pt > 0:
    for v in body.data.vertices:
        c_ = v.co; yp = PX_BOT - c_.z / k; xp = c_.x / k + CX
        if c_.y < 0 and PADO[0][0] <= yp <= PADO[-1][0]:
            l_, r_ = interp(_l0, yp), interp(_r0, yp)
            dist = min(xp - l_, r_ - xp, yp - PADO[0][0], PADO[-1][0] - yp)
            shp = P.get("shoulder_px", 0.0) if GS else 0.0
            if GS:
                # on the measured body the front surface inside the pad is the bristle TIPS: the shell sits back by
                # the bristle length plus the plate, the plate stands out of it with a soft rounded edge (the store
                # side frame), and just outside the pad the shell eases back from the carved bristle envelope to its
                # own surface over a shoulder, so there is no lip and no step round the pad
                back_ = P.get("tip_inset_cm", P["fine_len_cm"]) + pt
                if dist > 0:
                    f = min(1.0, dist / edge); f = f * f * (3 - 2 * f)
                    f *= min(1.0, max(0.0, (yp - PADO[0][0]) / P.get("crown_rise_measured_px", 8.0)))
                    dy_ = back_ - pt * f
                elif shp > 0 and dist > -shp:
                    s_ = 1.0 + dist / shp; s_ = s_ * s_ * (3 - 2 * s_)
                    dy_ = back_ * s_ * P.get("shoulder_frac", 1.0)
                else:
                    continue
                # never more than a share of the shell's own front depth (at the crown the body is thin)
                v.co.y += min(dy_, P.get("inset_cap", 0.45) * max(0.0, -c_.y))
                continue
            if dist > 0:
                f = min(1.0, dist / edge); f = f * f * (3 - 2 * f)
                f *= min(1.0, max(0.0, (yp - PADO[0][0]) / P.get("crown_rise_px" if not GS else "crown_rise_measured_px", 60.0 if not GS else 8.0)))   # the pad rises out of the crown, no step at the top
                # on the measured body the bristle tips ARE the front surface: the shell steps back by the tip depth
                v.co.y += (P.get("tip_inset_cm", P["fine_len_cm"]) * f) if GS else (-pt * f)
# the pad is the shell's own front, inside the pad outline, in the pad's silicone (no separate plate:
# in the studio the field sits flush, its edge read only where the nubs stop)
m_pad = material("pad", mats_.get("pad", mats_["bristle"])); body.data.materials.append(m_pad)
_l = [(y, l) for y, l, _ in PADO]; _r = [(y, r) for y, _, r in PADO]
for poly in body.data.polygons:
    c_ = poly.center; yp = PX_BOT - c_.z / k; xp = c_.x / k + CX
    if c_.y < 0 and PADO[0][0] <= yp <= PADO[-1][0] and interp(_l, yp) <= xp <= interp(_r, yp):
        poly.material_index = 2
bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
PAD = [(y, l, r) for y, l, r in P["outline"]]


def in_pad(xp, yp):
    if yp < PAD[0][0] or yp > PAD[-1][0]:
        return False
    l = interp([(y, l) for y, l, _ in PAD], yp); r = interp([(y, r) for y, _, r in PAD], yp)
    return l <= xp <= r


apex = P["apex"]; arm = P["arm_top"]


def coarse(xp, yp):
    # above both lines of the V from the apex up to the arms' top ends
    (ax, ay), (lx, ly), (rx, ry) = apex, arm[0], arm[1]
    if yp > ay:
        return False
    xl = ax + (lx - ax) * (ay - yp) / (ay - ly); xr = ax + (rx - ax) * (ay - yp) / (ay - ry)
    return xl <= xp <= xr


me = bpy.data.meshes.new("bristles"); nob = bpy.data.objects.new("bristles", me); sc.collection.objects.link(nob)
bm = bmesh.new()


def nub(p, n, r, L, sides=10):
    """a silicone bristle: a short column with a domed tip (the dome is what catches the light)."""
    n = n.normalized(); t1 = n.orthogonal().normalized(); t2 = n.cross(t1)
    ring = lambda h, rr: [bm.verts.new(p + n * h + (t1 * math.cos(2 * math.pi * i / sides) + t2 * math.sin(2 * math.pi * i / sides)) * rr) for i in range(sides)]
    if P.get("tip_dome"):    # a full round cap (the store frames light the whole tip as a soft round dot, not a pin-point)
        rings_ = [ring(-0.01, r)] + [ring(L - r + r * math.sin(a_), r * math.cos(a_)) for a_ in (0.0, 0.35, 0.7, 1.0, 1.25, 1.45)]
    else:
        rings_ = [ring(-0.01, r), ring(L - r * 0.9, r * 0.92), ring(L - r * 0.45, r * 0.75), ring(L - r * 0.12, r * 0.4)]
    tip = bm.verts.new(p + n * L)
    ncap = 3 if P.get("tip_dome") else 2      # the last bands of the column are the cap (the lit tip); the rest is the shaft
    for bi, (a_, b_) in enumerate(zip(rings_, rings_[1:])):
        for i in range(sides):
            j = (i + 1) % sides; f_ = bm.faces.new((a_[i], a_[j], b_[j], b_[i]))
            f_.material_index = 1 if bi >= len(rings_) - 1 - ncap else 0
    for i in range(sides):
        j = (i + 1) % sides; f_ = bm.faces.new((rings_[-1][i], rings_[-1][j], tip)); f_.material_index = 1


count = {"fine": 0, "coarse": 0}


def grid_points(sp_px):
    """the plain hex grid (rows across the pad), gently bowed with the egg."""
    out = []; rowi = 0; y = PAD[0][0]
    while y <= PAD[-1][0]:
        off = (sp_px / 2) if rowi % 2 else 0.0
        x = CX - 400 + off
        while x < CX + 400:
            out.append((x, y + P.get("row_bow_px", 0.0) * ((x - CX) / 300.0) ** 2)); x += sp_px
        y += sp_px * 0.866; rowi += 1
    return out


def y_points(sp_px):
    """THE Y (the owner, 2026-10-09: "the front is not mimicking the Y shape down the middle"): on the real pad the
    fine bristles stand in columns that run alongside each arm of the coarse V and then straight down either side
    of the centre seam, so the field itself draws a Y. Each column is an offset of the Y's half-line (arm top →
    apex → down the seam), rounded at the apex; the points along it are one pitch apart (y_stagger: alternate
    columns half a pitch out of step; row_bow_px: rows bow with the egg)."""
    out = []
    for side in (-1, 1):
        ax, ay = apex; tx, ty = arm[0] if side < 0 else arm[1]
        # the half-line, bottom to top: down the seam, the rounded apex, up the arm, carried on past the arm's end
        dx, dy = tx - ax, ty - ay; dl = math.hypot(dx, dy); ux, uy = dx / dl, dy / dl
        R_ = P.get("y_round_px", 40.0)
        line = [(CX + side * 0.0, PAD[-1][0] + 40)]
        line += [(CX, ay + R_)]
        for q in range(1, 8):           # quadratic blend through the apex
            t = q / 8; p0 = (CX, ay + R_); p1 = (ax, ay); p2 = (ax + ux * R_, ay + uy * R_)
            line.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
        line += [(ax + ux * (dl + 300), ay + uy * (dl + 300))]
        # resample the half-line evenly, with the outward normal (away from the V and the seam) at each point
        dense = []
        for (x0, y0), (x1, y1) in zip(line, line[1:]):
            n_ = max(1, int(math.hypot(x1 - x0, y1 - y0) / 2))
            for q in range(n_):
                dense.append((x0 + (x1 - x0) * q / n_, y0 + (y1 - y0) * q / n_))
        dense.append(line[-1])
        arc = [0.0]
        for (x0, y0), (x1, y1) in zip(dense, dense[1:]):
            arc.append(arc[-1] + math.hypot(x1 - x0, y1 - y0))
        def at(sv):
            q = max(0, min(len(arc) - 2, next((i_ for i_ in range(len(arc) - 1) if arc[i_ + 1] >= sv), len(arc) - 2)))
            (x0, y0), (x1, y1) = dense[q], dense[q + 1]; f_ = (sv - arc[q]) / max(1e-9, arc[q + 1] - arc[q])
            tx_, ty_ = x1 - x0, y1 - y0; tl = math.hypot(tx_, ty_) or 1.0
            nx_, ny_ = (ty_ / tl, -tx_ / tl) if side < 0 else (-ty_ / tl, tx_ / tl)
            return x0 + tx_ * f_, y0 + ty_ * f_, nx_, ny_
        col = 0
        while True:
            off = P["seam_px"] / 2 + sp_px * (0.5 + col)
            if off > 420:
                break
            sv = (sp_px / 2) * (col % 2) if P.get("y_stagger", True) else 0.0   # the store front reads as a square grid (FFT: 10.5‰ across and down)
            # rows bow gently with the egg: locally square, but no two columns share a height across the pad,
            # so from the side the field closes into the store's dense comb instead of separate pins
            sv = (sv + P.get("row_bow_px", 0.0) * (off / 300.0) ** 2) % sp_px
            while sv < arc[-1]:
                x_, y_, nx_, ny_ = at(sv); out.append((x_ + nx_ * off, y_ + ny_ * off)); sv += sp_px
            col += 1
    return out


for kind, sp_px, r_cm, L_cm in (("fine", P["fine_px"], P["fine_r_cm"], P["fine_len_cm"]), ("coarse", P["coarse_px"], P["coarse_r_cm"], P["coarse_len_cm"])):
    pts_ = y_points(sp_px) if (kind == "fine" and P.get("y_flow")) else grid_points(sp_px)
    taken = {}                       # one nub per spot: where offset columns crowd (inside the apex turn) the extras drop
    cell = sp_px * 0.8
    for x, yb_ in pts_:
        if not (in_pad(x, yb_) and (coarse(x, yb_) == (kind == "coarse")) and abs(x - CX) > P["seam_px"] / 2):
            continue
        key = (int(x // cell), int(yb_ // cell))
        if any(math.hypot(x - ox, yb_ - oy) < cell for kk in ((key[0] + a_, key[1] + b_) for a_ in (-1, 0, 1) for b_ in (-1, 0, 1)) for ox, oy in taken.get(kk, ())):
            continue
        taken.setdefault(key, []).append((x, yb_))
        hit = bvh.ray_cast(Vector(((x - CX) * k, -20.0, zc(yb_))), Vector((0, 1, 0)))
        if hit[0] is not None:
            nrm = Vector((0, -1, 0))   # silicone bristles stand straight out of the pad plane (store side frame)
            if P.get("fan_xy", 0.0) > 0 and hit[1] is not None:
                # THE FAN (store three-quarter and side frames): toward the pad's edge the bristles lean outward with the
                # body's curve — sideways only, never up or down — which is what makes the side read as a deep comb
                hn = Vector((hit[1].x, hit[1].y, 0.0))
                if hn.length > 1e-6:
                    nrm = nrm.lerp(hn.normalized(), P["fan_xy"]).normalized()
            if P.get("normal_follow", 0.0) > 0 and hit[1] is not None:
                # where the pad curves away (the crown, the edges) they lean with it, as the store frames show
                nrm = nrm.lerp(hit[1].normalized(), P["normal_follow"]).normalized()
            l_ = interp([(yy, ll) for yy, ll, _ in PAD], yb_); r_ = interp([(yy, rr) for yy, _, rr in PAD], yb_)
            ed = min(x - l_, r_ - x, yb_ - PAD[0][0], PAD[-1][0] - yb_)
            t_ = max(0.0, min(1.0, ed / (P.get("edge_rows", 2.5) * sp_px))); t_ = t_ * t_ * (3 - 2 * t_)
            sh = P.get("edge_min", 0.55) + (1 - P.get("edge_min", 0.55)) * t_      # bristles shorten and thin toward the pad's edge
            if P.get("top_min") is not None:   # and over the crown, where the pad turns away, they stay low (never poke over the top)
                tt = max(0.0, min(1.0, (yb_ - PAD[0][0]) / (P.get("top_rows", 4) * sp_px))); tt = tt * tt * (3 - 2 * tt)
                sh = min(sh, P["top_min"] + (1 - P["top_min"]) * tt)
            L_use = L_cm * sh
            if GS and P.get("tips_to_outline"):
                # every bristle ends at the measured outline: as long as the dip under it, never longer (at the crown and
                # the edges the dip is shallow, so the bristles there are short — they never poke past the real shape)
                hp_ = hit[0]; th_ = math.atan2(hp_.y, hp_.x); hull_ = section(yb_, th_)
                dip = max(0.0, Vector((hull_.x, hull_.y, 0)).length - Vector((hp_.x, hp_.y, 0)).length)
                L_use = max(L_cm * P.get("tips_min", 0.25), min(L_use, dip + P.get("tip_over_cm", 0.03)))
            nub(hit[0], nrm, r_cm * (0.8 + 0.2 * sh), L_use); count[kind] += 1
bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = True
# the shaft and the tip: the store frames light only the round tips; the shafts stay dark between them
nob.data.materials.append(material("bristle", mats_.get("bristle_shaft", mats_["bristle"])))
nob.data.materials.append(material("bristle-tip", mats_["bristle"]))
objs_c.append(nob)
print("NUBS", count)

# the seam: a thin raised ridge down the middle of the field (lit as a bright line in the renders)
pts = []
for y in range(int(apex[1]), int(PAD[-1][0]) - 6, 6):
    hit = bvh.ray_cast(Vector((0.0, -20.0, zc(y))), Vector((0, 1, 0)))
    if hit[0] is not None:
        pts.append((hit[0], hit[1]))
if len(pts) > 2 and P.get("seam_h_cm", 0) > 0:
    me2 = bpy.data.meshes.new("seam"); so = bpy.data.objects.new("seam", me2); sc.collection.objects.link(so); bm2 = bmesh.new(); prev = None
    w = P["seam_w_cm"]
    for p, n in pts:
        l = bm2.verts.new(p + Vector((-w / 2, 0, 0)) - n * 0.0); r = bm2.verts.new(p + Vector((w / 2, 0, 0))); t = bm2.verts.new(p + n * P["seam_h_cm"])
        if prev:
            bm2.faces.new((prev[0], prev[2], t, l)); bm2.faces.new((prev[2], prev[1], r, t))
        prev = (l, r, t)
    bm2.to_mesh(me2); bm2.free(); so.data.materials.append(material("seam", mats_["bristle"])); objs_c.append(so)

custom_objs = objs_c
