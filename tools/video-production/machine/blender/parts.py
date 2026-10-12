"""A round product built PART BY PART at its real size: each part (base, body, shoulder, collar,
cap, pump, nozzle) is its own lathe from its own measured outline, with its own material
(metal / dielectric, colour, roughness, coat) and the printed wrap on the part that carries it.
Run by Blender:
  blender -b -P parts.py -- <kit.json> <out.png> [yaw] [tilt] [w] [h] [transparent] [save.blend]
Everything comes from kit.json["model_parts"]; nothing here names a product.

model_parts = {
  "units": "cm", "height": H, "diameter": D,
  "parts": [ {"name", "z0", "z1" (fractions of H from the bottom), "r" (fraction of D/2, or
              "profile": [[t, r_frac], ...] t 0..1 bottom->top inside the part),
              "fillet_bottom", "fillet_top" (fractions of D), "section_depth" (oval: y/x),
              "material": name, "wrap": optional {"mask": path, "seam_deg"}, "cap_top": bool, "cap_bottom": bool} ],
  "materials": {name: {"base": "#hex", "metallic", "roughness", "coat", "print": {"base": "#hex", "metallic", "roughness"}}},
  "features": [ {"type": "slot", ...}, {"type": "nozzle", ...} ]
}"""
import bpy, bmesh, math, sys, json, os
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
kit_p = Path(argv[0]); out = argv[1]
yaw = float(argv[2]) if len(argv) > 2 else 0.0; tilt = float(argv[3]) if len(argv) > 3 else 0.0
RW = int(argv[4]) if len(argv) > 4 else 1000; RH = int(argv[5]) if len(argv) > 5 else 1250
transparent = (argv[6] == "1") if len(argv) > 6 else True; save = argv[7] if len(argv) > 7 else None
kit = json.loads(kit_p.read_text()); d = kit_p.parent
import os as _os
M = kit.get("model_parts_" + _os.environ["KIT_VARIANT"]) if _os.environ.get("KIT_VARIANT") else kit["model_parts"]; H = M["height"]; D = M["diameter"]; R = D / 2
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def hexrgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c] + [1.0]


def material(name, spec, wrap=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexrgb(spec["base"])
    b.inputs["Metallic"].default_value = spec.get("metallic", 0.0)
    b.inputs["Roughness"].default_value = spec.get("roughness", 0.3)
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = spec.get("coat", 0.0)
        b.inputs["Coat Roughness"].default_value = spec.get("coat_roughness", 0.05)
    if "specular" in spec and "Specular IOR Level" in b.inputs:     # how much a dielectric reflects (0.5 = plain plastic; low = dead-matte rubber)
        b.inputs["Specular IOR Level"].default_value = spec["specular"]
    if spec.get("transmission") and "Transmission Weight" in b.inputs:
        # a smoky see-through plastic (2026-10-09, the owner: the black bottles are slightly translucent — the serum shows
        # through); the printed foil stays opaque (the wrap mask switches transmission off under the print, below)
        b.inputs["Transmission Weight"].default_value = spec["transmission"]
        b.inputs["IOR"].default_value = spec.get("ior", 1.49)
    if spec.get("anisotropic") and "Anisotropic" in b.inputs:
        b.inputs["Anisotropic"].default_value = spec["anisotropic"]
    if spec.get("sheen") and "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = spec["sheen"]
    if wrap and wrap.get("image"):            # a full-colour printed wrap (label art in colour)
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(d / wrap["image"])); t.interpolation = "Cubic"
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if wrap and spec.get("print") and wrap.get("mask"):
        p = spec["print"]
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(d / wrap["mask"])); t.image.colorspace_settings.name = "Non-Color"
        t.interpolation = "Cubic"
        for key, a, bb in (("Base Color", hexrgb(spec["base"]), hexrgb(p["base"])),):
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
            mix.inputs[6].default_value = a; mix.inputs[7].default_value = bb
            nt.links.new(t.outputs["Color"], mix.inputs[0]); nt.links.new(mix.outputs[2], b.inputs[key])
        for key, a, bb in (("Metallic", spec.get("metallic", 0.0), p.get("metallic", 1.0)),
                           ("Roughness", spec.get("roughness", 0.3), p.get("roughness", 0.3))):
            mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = a; mr.inputs["To Max"].default_value = bb
            nt.links.new(t.outputs["Color"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs[key])
        if spec.get("transmission") and "Transmission Weight" in b.inputs:
            mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = spec["transmission"]; mr.inputs["To Max"].default_value = 0.0
            nt.links.new(t.outputs["Color"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Transmission Weight"])
        if p.get("coat") is not None and "Coat Weight" in b.inputs:
            mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = spec.get("coat", 0.0); mr.inputs["To Max"].default_value = p["coat"]
            nt.links.new(t.outputs["Color"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Coat Weight"])
        if p.get("bump"):
            bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = p["bump"]; bump.inputs["Distance"].default_value = 0.002
            nt.links.new(t.outputs["Color"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if spec.get("grain"):                    # surface micro-texture: a fine grain in the normal + a little roughness variation
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = spec.get("grain_scale", 400.0)
        nz.inputs["Detail"].default_value = 4.0; nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        gb = nt.nodes.new("ShaderNodeBump"); gb.name = "grain_bump"; gb.inputs["Strength"].default_value = spec["grain"]; gb.inputs["Distance"].default_value = spec.get("grain_depth", 0.002)
        nt.links.new(nz.outputs["Fac"], gb.inputs["Height"]); nt.links.new(gb.outputs["Normal"], b.inputs["Normal"])
        if "Coat Normal" in b.inputs and spec.get("coat_smooth", True):
            pass                                  # the clear coat stays glassy over the grain (piano-black / dome)
        if spec.get("rough_var"):
            nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = spec.get("grain_scale", 400.0) / 8
            nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
            mr = nt.nodes.new("ShaderNodeMapRange"); r0 = spec.get("roughness", 0.3); dv = spec["rough_var"]
            mr.inputs["To Min"].default_value = r0 - dv; mr.inputs["To Max"].default_value = r0 + dv
            nt.links.new(nz2.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    if spec.get("dots"):                     # sub-pixel bristle field: a dense dot relief + glossy dot tips (the fine sheen between real bristles)
        tc = nt.nodes.new("ShaderNodeTexCoord"); vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = spec["dots"]
        nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
        inv = nt.nodes.new("ShaderNodeMapRange"); inv.inputs["From Min"].default_value = 0.0; inv.inputs["From Max"].default_value = 0.35
        inv.inputs["To Min"].default_value = 1.0; inv.inputs["To Max"].default_value = 0.0; nt.links.new(vo.outputs["Distance"], inv.inputs["Value"])
        db = nt.nodes.new("ShaderNodeBump"); db.inputs["Strength"].default_value = spec.get("dots_strength", 0.8); db.inputs["Distance"].default_value = 0.01
        nt.links.new(inv.outputs["Result"], db.inputs["Height"]); nt.links.new(db.outputs["Normal"], b.inputs["Normal"])
    return m


mats = {k: v for k, v in M["materials"].items()}
N = M.get("segments", 192)


def outline(part):
    """[(z, r)] bottom -> top for one part, with its fillets."""
    z0, z1 = part["z0"] * H, part["z1"] * H
    if "profile" in part:
        pts = [(z0 + t * (z1 - z0), rf * R) for t, rf in part["profile"]]
    else:
        pts = [(z0, part.get("r", 1.0) * R), (z1, part.get("r", 1.0) * R)]
    fb = part.get("fillet_bottom", 0.0) * D; ft = part.get("fillet_top", 0.0) * D
    res = []
    if fb > 0:
        r0 = pts[0][1]
        for i in range(9):
            a = math.pi / 2 * (1 - i / 8)
            res.append((z0 + fb - fb * math.sin(a), r0 - fb + fb * math.cos(a)))
        pts = [(z, r) for z, r in pts if z > z0 + fb]
    res += pts if fb <= 0 else pts
    if ft > 0:
        r1 = res[-1][1]
        res = [(z, r) for z, r in res if z < z1 - ft]
        for i in range(9):
            a = math.pi / 2 * i / 8
            res.append((z1 - ft + ft * math.sin(a), r1 - ft + ft * math.cos(a)))
    return res


def ellipse_perim(a, b):
    return math.pi * (3 * (a + b) - math.sqrt(max(0.0, (3 * a + b) * (a + 3 * b))))


def squeeze_b(a, perim):
    """A squeeze tube keeps its wall's length: at half-width a, the depth b that gives the same perimeter
    (round where a <= the tube's own radius, flat at the crimp)."""
    r0 = perim / (2 * math.pi)
    if a <= r0:
        return a
    lo, hi = 0.0, a
    for _ in range(50):
        mid = (lo + hi) / 2
        if ellipse_perim(a, mid) > perim:
            hi = mid
        else:
            lo = mid
    return max(lo, part_min_b)


part_min_b = 0.0


def slab(part):
    """A flat band (a tube's crimp seal): width from r, thickness a fraction of D, ribbed by a bump."""
    global part_min_b
    z0, z1 = part["z0"] * H, part["z1"] * H; w = part.get("r", 1.0) * R * 2; t = part.get("thickness", 0.04) * D
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, (z0 + z1) / 2)); ob = bpy.context.active_object; ob.name = part["name"]
    ob.scale = (w, t, z1 - z0); bpy.ops.object.transform_apply(scale=True)
    bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = min(t * 0.45, 0.03); bv.segments = 3
    spec = dict(mats[part["material"]])
    m = material(part["name"] + "-" + part["material"], spec)
    if part.get("ribs"):
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = part["ribs"] / w * 2 * math.pi
        nt.links.new(sep.outputs["X"], mul.inputs[0])
        sn = nt.nodes.new("ShaderNodeMath"); sn.operation = "SINE"; nt.links.new(mul.outputs[0], sn.inputs[0])
        # ribs run down the top part of the band only (the photo: ridges over its upper two thirds)
        ramp = nt.nodes.new("ShaderNodeMapRange"); ramp.inputs["From Min"].default_value = z0 + (z1 - z0) * part.get("rib_from", 0.3)
        ramp.inputs["From Max"].default_value = z0 + (z1 - z0) * (part.get("rib_from", 0.3) + 0.08)
        nt.links.new(sep.outputs["Z"], ramp.inputs["Value"])
        mm = nt.nodes.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; nt.links.new(sn.outputs[0], mm.inputs[0]); nt.links.new(ramp.outputs[0], mm.inputs[1])
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = part.get("rib_strength", 1.0); bump.inputs["Distance"].default_value = part.get("rib_depth", 0.06)
        nt.links.new(mm.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    ob.data.materials.append(m)
    return ob


def panel(part):
    """Soft goods laid flat (a folded towel): a rounded slab W x thickness x H, cloth crinkle as a bump,
    an embroidered mark on the front face from a mask (white = thread), a lighter overlock edge, an optional loop."""
    W = part["width"] * D; T = part["thickness"] * D; z0, z1 = part["z0"] * H, part["z1"] * H; HH = z1 - z0
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, part.get("offset_y", 0.0) * D, z0 + HH / 2)); ob = bpy.context.active_object; ob.name = part["name"]
    ob.scale = (W, T, HH); bpy.ops.object.transform_apply(scale=True)
    bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = T * part.get("round", 0.3); bv.segments = 6
    s1 = ob.modifiers.new("dice", "SUBSURF"); s1.subdivision_type = "SIMPLE"; s1.levels = s1.render_levels = 5
    if part.get("wave", 0) > 0:        # cloth is never flat: a soft low-frequency wave through the whole piece
        tx = bpy.data.textures.new("wave", "CLOUDS"); tx.noise_scale = part.get("wave_scale", 0.35) * D; tx.noise_depth = 2
        dp = ob.modifiers.new("wave", "DISPLACE"); dp.texture = tx; dp.strength = part["wave"] * T; dp.mid_level = 0.5; dp.texture_coords = "LOCAL"
    sd = ob.modifiers.new("sub", "SUBSURF"); sd.levels = 1; sd.render_levels = 1
    for p_ in ob.data.polygons:
        p_.use_smooth = True
    spec = mats[part["material"]]
    m = bpy.data.materials.new(part["name"]); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = spec.get("roughness", 0.95)
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = spec.get("sheen", 0.5); b.inputs["Sheen Roughness"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    cloth = hexrgb(spec["base"]); thread = hexrgb(spec.get("thread", "#E6E6E4")); edge = hexrgb(spec.get("edge", spec["base"]))
    col = nt.nodes.new("ShaderNodeMix"); col.data_type = "RGBA"; col.inputs[6].default_value = cloth; col.inputs[7].default_value = edge
    # overlock edge: within edge_w of the side or bottom/top borders
    def near(axis_out, lo, hi, w):
        a = nt.nodes.new("ShaderNodeMath"); a.operation = "LESS_THAN"; a.inputs[1].default_value = lo + w
        bb = nt.nodes.new("ShaderNodeMath"); bb.operation = "GREATER_THAN"; bb.inputs[1].default_value = hi - w
        nt.links.new(axis_out, a.inputs[0]); nt.links.new(axis_out, bb.inputs[0])
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; nt.links.new(a.outputs[0], mx.inputs[0]); nt.links.new(bb.outputs[0], mx.inputs[1]); return mx
    ew = part.get("edge_w", 0.0) * D
    if ew > 0:
        sides = part.get("edge_sides", "lrbt")
        ex = near(sep.outputs["X"], -W / 2 if "l" in sides else -1e6, W / 2 if "r" in sides else 1e6, ew)
        ez = near(sep.outputs["Z"], z0 if "b" in sides else -1e6, z1 if "t" in sides else 1e6, ew)
        e = nt.nodes.new("ShaderNodeMath"); e.operation = "MAXIMUM"; nt.links.new(ex.outputs[0], e.inputs[0]); nt.links.new(ez.outputs[0], e.inputs[1])
        nt.links.new(e.outputs[0], col.inputs[0])
    else:
        col.inputs[0].default_value = 0.0
    out_col = col.outputs[2]
    if part.get("mark"):
        mk = part["mark"]
        u = nt.nodes.new("ShaderNodeMapRange"); u.inputs["From Min"].default_value = -W / 2; u.inputs["From Max"].default_value = W / 2
        v = nt.nodes.new("ShaderNodeMapRange"); v.inputs["From Min"].default_value = z0; v.inputs["From Max"].default_value = z1
        nt.links.new(sep.outputs["X"], u.inputs["Value"]); nt.links.new(sep.outputs["Z"], v.inputs["Value"])
        cmb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(u.outputs[0], cmb.inputs[0]); nt.links.new(v.outputs[0], cmb.inputs[1])
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(d / mk)); t.image.colorspace_settings.name = "Non-Color"; t.extension = "CLIP"
        nt.links.new(cmb.outputs[0], t.inputs["Vector"])
        front = nt.nodes.new("ShaderNodeMath"); front.operation = "LESS_THAN"; front.inputs[1].default_value = 0.0; nt.links.new(sep.outputs["Y"], front.inputs[0])
        mm = nt.nodes.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; nt.links.new(t.outputs["Color"], mm.inputs[0]); nt.links.new(front.outputs[0], mm.inputs[1])
        c2 = nt.nodes.new("ShaderNodeMix"); c2.data_type = "RGBA"; nt.links.new(mm.outputs[0], c2.inputs[0]); nt.links.new(out_col, c2.inputs[6]); c2.inputs[7].default_value = thread
        out_col = c2.outputs[2]
        thr = mm
    nt.links.new(out_col, b.inputs["Base Color"])
    # cloth crinkle (+ the thread stands up a little)
    nz = nt.nodes.new("ShaderNodeTexVoronoi"); nz.inputs["Scale"].default_value = part.get("crinkle", 9.0)   # microfiber's pebbled cells
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = part.get("crinkle", 9.0) * 0.4; nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    hx = nt.nodes.new("ShaderNodeMath"); hx.operation = "MULTIPLY_ADD"; hx.inputs[1].default_value = 1.0
    nt.links.new(nz.outputs["Distance"], hx.inputs[0]); nt.links.new(nz2.outputs["Fac"], hx.inputs[2])
    nz = hx
    h = hx.outputs[0]
    if part.get("mark"):
        add = nt.nodes.new("ShaderNodeMath"); add.operation = "MULTIPLY_ADD"; add.inputs[1].default_value = 1.5
        nt.links.new(thr.outputs[0], add.inputs[0]); nt.links.new(hx.outputs[0], add.inputs[2]); h = add.outputs[0]
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = part.get("crinkle_strength", 0.45); bump.inputs["Distance"].default_value = part.get("crinkle_depth", 0.05)
    nt.links.new(h, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    ob.data.materials.append(m)
    objs_extra = []
    if part.get("loop"):
        lp = part["loop"]; r = lp["r"] * D
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=lp.get("cord", 0.012) * D, location=(lp["x"] * W / 2, 0, z0 - r * 0.75),
                                         rotation=(math.radians(90), 0, 0), major_segments=48, minor_segments=12)
        lo = bpy.context.active_object; lo.name = "loop"; lo.scale = (0.45, 1.0, 1.0)
        lm = bpy.data.materials.new("loop"); lm.use_nodes = True; lm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = edge
        lm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9; lo.data.materials.append(lm)
        objs_extra.append(lo)
    ob["extra"] = [o.name for o in objs_extra]
    return ob


def lathe(part):
    if part.get("kind") == "panel":
        return panel(part)
    if part.get("kind") == "slab":
        return slab(part)
    global part_min_b
    prof = outline(part); dep = part.get("section_depth", 1.0)
    sq = part.get("section") == "squeeze"; perim = math.pi * D * part.get("perimeter_d", 1.0); part_min_b = part.get("min_depth", 0.02) * D / 2
    me = bpy.data.meshes.new(part["name"]); ob = bpy.data.objects.new(part["name"], me); sc.collection.objects.link(ob)
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    wrap = part.get("wrap"); seam = (wrap or {}).get("seam_deg", 90.0)
    zw0, zw1 = part["z0"] * H, part["z1"] * H
    rings = []
    for z, r in prof:
        ring = []
        for j in range(N + 1):
            deg = seam + 360.0 * j / N                          # column j sits at this azimuth (0 = front)
            a = math.radians(deg)
            bb = squeeze_b(r, perim) if sq else dep * r
            ring.append(bm.verts.new((r * math.sin(a), -bb * math.cos(a), z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(N):
            f = bm.faces.new((rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]))
            for lp, (jj, ii) in zip(f.loops, ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1))):
                z = prof[ii][0]
                lp[uv].uv = (jj / N, (z - zw0) / max(1e-9, zw1 - zw0))
    if part.get("cap_bottom", True) and prof[0][1] > 1e-4:
        c = bm.verts.new((0, 0, prof[0][0])); [bm.faces.new((c, rings[0][j + 1], rings[0][j])) for j in range(N)]
    if part.get("cap_top", True) and prof[-1][1] > 1e-4:
        c = bm.verts.new((0, 0, prof[-1][0])); [bm.faces.new((c, rings[-1][j], rings[-1][j + 1])) for j in range(N)]
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)      # weld the seam: a closed solid (UVs live on the loops)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    m = material(part["name"] + "-" + part["material"], mats[part["material"]], wrap)
    if part.get("ribs"):                      # vertical knurl ribs round the part (a screw cap's grip)
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
        at = nt.nodes.new("ShaderNodeMath"); at.operation = "ARCTAN2"; nt.links.new(sep.outputs["Y"], at.inputs[0]); nt.links.new(sep.outputs["X"], at.inputs[1])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = part["ribs"]; nt.links.new(at.outputs[0], mul.inputs[0])
        sn = nt.nodes.new("ShaderNodeMath"); sn.operation = "SINE"; nt.links.new(mul.outputs[0], sn.inputs[0])
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = part.get("rib_strength", 0.6); bump.inputs["Distance"].default_value = 0.01
        nt.links.new(sn.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    me.materials.append(m)
    if part.get("liquid"):
        # THE SERUM: what the see-through wall shows — the same outline, inset by the wall, filled to a level
        lq = part["liquid"]; inset = lq.get("wall_cm", 0.12); top = zw0 + (zw1 - zw0) * lq.get("fill", 0.85)
        def r_at(z):
            for (za, ra), (zb, rb) in zip(prof, prof[1:]):
                if za <= z <= zb or zb <= z <= za:
                    return ra + (rb - ra) * (z - za) / ((zb - za) or 1e-9)
            return prof[0][1] if abs(z - prof[0][0]) < abs(z - prof[-1][0]) else prof[-1][1]
        pts = [(z, max(1e-3, r_at(z) - inset)) for z in [zw0 + inset + (top - zw0 - inset) * q / 24 for q in range(25)]]
        if len(pts) >= 2:
            me2 = bpy.data.meshes.new(part["name"] + "-serum"); ob2 = bpy.data.objects.new(part["name"] + "-serum", me2); sc.collection.objects.link(ob2)
            bm2 = bmesh.new(); rr = []
            for z, r in pts:
                rr.append([bm2.verts.new((r * math.sin(2 * math.pi * j / 96), -(dep * r) * math.cos(2 * math.pi * j / 96), z)) for j in range(96)])
            for i in range(len(rr) - 1):
                for j in range(96):
                    bm2.faces.new((rr[i][j], rr[i][(j + 1) % 96], rr[i + 1][(j + 1) % 96], rr[i + 1][j]))
            bm2.faces.new(list(reversed(rr[0]))); bm2.faces.new(rr[-1])
            bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces); bm2.to_mesh(me2); bm2.free()
            for pp in me2.polygons:
                pp.use_smooth = True
            me2.materials.append(material(part["name"] + "-serum", mats[lq.get("material", "serum")]))
            ob2.parent = ob
    return ob


objs = [lathe(p) for p in M.get("parts", [])]
if M.get("custom"):                            # a product modelled by hand in its own script (the device, the case)
    _g = dict(globals()); exec(open(str((Path(__file__).resolve().parent / M["custom"]))).read(), _g)
    objs += _g["custom_objs"]
objs += [bpy.data.objects[n] for o in objs for n in (o.get("extra") or [])]


def cutter_slot(f):
    """A U-shaped recess cut into a part's front face from its top: width w, down to depth_z, set in by inset."""
    w = f["width"] * D; zt = f["z_top"] * H + 0.05; zb = f["z_top"] * H - f["drop"] * D; inset = f["inset"] * D
    me = bpy.data.meshes.new("slot"); ob = bpy.data.objects.new("slot", me); sc.collection.objects.link(ob)
    bm = bmesh.new()
    # 2D U outline in x-z, extruded along -y from the recess floor out past the surface
    pts = [(-w / 2, zt)]
    for i in range(17):
        a = math.pi + math.pi * i / 16
        pts.append((w / 2 * math.cos(a), zb + w / 2 + w / 2 * math.sin(a)))
    pts.append((w / 2, zt))
    yf = -(R - inset); yo = -(R + 1.0)
    front = [bm.verts.new((x, yf, z)) for x, z in pts]; back = [bm.verts.new((x, yo, z)) for x, z in pts]
    bm.faces.new(front); bm.faces.new(list(reversed(back)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts); bm.faces.new((front[j], front[i], back[i], back[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return ob


for f in M.get("features", []):
    host = next(o for o in objs if o.name == f["on"])
    if f["type"] == "slot":
        cut = cutter_slot(f)
        mod = host.modifiers.new("slot", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = cut; mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = host; bpy.ops.object.modifier_apply(modifier="slot")
        bpy.data.objects.remove(cut); print("SLOT cut into", host.name, len(host.data.vertices))
    elif f["type"] == "nozzle":
        ro, ri = f["r_out"] * D, f["r_in"] * D; zc = f["z"] * H; y0 = -(R - f["inset"] * D); L = f["length"] * D
        bpy.ops.mesh.primitive_cylinder_add(radius=ro, depth=L, location=(0, y0 - L / 2, zc), rotation=(math.radians(90), 0, 0), vertices=48)
        nz = bpy.context.active_object; nz.name = "nozzle"
        bpy.ops.mesh.primitive_cylinder_add(radius=ri, depth=L * 3, location=(0, y0 - L / 2, zc), rotation=(math.radians(90), 0, 0), vertices=48)
        hole = bpy.context.active_object
        mod = nz.modifiers.new("hole", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = hole; mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = nz; bpy.ops.object.modifier_apply(modifier="hole"); bpy.data.objects.remove(hole)
        bpy.ops.mesh.primitive_cylinder_add(radius=ri * 1.02, depth=L * 0.7, location=(0, y0 - L * 0.45, zc), rotation=(math.radians(90), 0, 0), vertices=48)   # the bore: a dark plug, no daylight through the tube
        dark = bpy.context.active_object; dark.name = "nozzle-bore"
        dark.data.materials.append(material("bore", {"base": "#050505", "roughness": 0.9}))
        for p in nz.data.polygons:
            p.use_smooth = True
        nz.data.materials.clear()                 # the boolean leaves an empty slot that renders white
        nz.data.materials.append(material("nozzle-" + f["material"], mats[f["material"]]))
        for p_ in nz.data.polygons:
            p_.material_index = 0
        objs += [nz, dark]

root = bpy.data.objects.new("product", None); sc.collection.objects.link(root)
for o in objs:
    if o.parent is None:
        o.parent = root
root.rotation_mode = "ZXY"      # yaw about the product's own up axis first, then the camera's elevation (tilt), then roll about the view axis
root.rotation_euler = (math.radians(tilt), math.radians(float(os.environ.get("KIT_ROLL", 0))), math.radians(yaw))

# ── the studio: a neutral sweep the metal can reflect (soft boxes left and right, dark flags between,
#    a bright ceiling) — the studio renders' look, not a white void that turns gold into white
st = dict(M.get("studio", {}))
import os
if os.environ.get("KIT_STUDIO"):          # compare renders can ask for the studio render's own look
    st["mode"] = os.environ["KIT_STUDIO"]
if os.environ.get("KIT_STUDIO_JSON"):     # light-solve experiments: override any studio number
    st.update(json.loads(os.environ["KIT_STUDIO_JSON"]))
w = bpy.data.worlds.new("w"); w.use_nodes = True; bg = w.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = hexrgb(st.get("world", "#d9d9d6")); bg.inputs["Strength"].default_value = st.get("world_strength", 0.6); sc.world = w
k = max(H, D * 3)


def panel(name, loc, rot, size, strength, color="#ffffff"):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    p = bpy.context.active_object; p.name = name; p.scale = size
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = hexrgb(color); e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], o.inputs[0]); p.data.materials.append(m)
    p.visible_camera = False
    return p


zc = H / 2
if st.get("mode") == "dark":   # the turntable's look: black set, rim light from behind both sides, a soft top
    bg.inputs["Color"].default_value = (0, 0, 0, 1); bg.inputs["Strength"].default_value = 0.0
    for side in (-1, 1):
        panel("rim%d" % side, (side * k * 1.0, k * 0.6, zc), (0, math.radians(90), math.radians(side * -35)), (H * 1.8, k * 0.35, 1), st.get("rim", 12.0))
    panel("top", (0, 0, H + k * 0.9), (0, 0, 0), (k * 1.2, k * 1.2, 1), st.get("top", 2.0))
    panel("front", (0, -k * 2.2, zc), (math.radians(90), 0, 0), (k * 0.9, H * 1.4, 1), st.get("front", 0.35))
    # the big soft source above and in front that paints the silver gradient down the turntable's shell
    panel("key", (0, -k * 0.5, H + k * 1.1), (math.radians(20), 0, 0), (k * 1.4, k * 0.8, 1), st.get("keypanel", 4.0))
def facing(name, az_deg, el_deg, dist, size, strength):
    """a soft box at azimuth az (0 = camera side, 180 = behind), elevation el, facing the product's centre."""
    a, e = math.radians(az_deg), math.radians(el_deg)
    loc = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist + Vector((0, 0, zc))
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc); p = bpy.context.active_object; p.name = name; p.scale = size
    p.rotation_euler = (Vector((0, 0, zc)) - loc).to_track_quat("-Z", "Y").to_euler()
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], o.inputs[0]); p.data.materials.append(m); p.visible_camera = False


if st.get("mode") == "white":   # the store's white-sweep turntable: white all round, tall boxes at the sides, a front fill, a top
    bg.inputs["Color"].default_value = (1, 1, 1, 1); bg.inputs["Strength"].default_value = st.get("ws", 0.35)
    for side in (-1, 1):
        facing("side%d" % side, side * st.get("side_az", 100), st.get("side_el", 10), k * 2.0, (k * st.get("side_w", 0.5), H * 2.2, 1), st.get("side", 4.0) * (st.get("side_r", 1.0) if side > 0 else st.get("side_l", 1.0)))
    facing("front", st.get("front_az", -15), st.get("front_el", 20), k * 3.0, (k * 1.2, H * 1.6, 1), st.get("front", 1.0))
    facing("top", 0, 80, k * 2.0, (k * 1.5, k * 1.5, 1), st.get("top", 2.0))
    for i_, kb in enumerate(st.get("keys", [])):    # extra soft boxes: [az, el, width (x k), strength]
        facing("key%d" % i_, kb[0], kb[1], k * 2.5, (k * kb[2], H * 2.0, 1), kb[3])
    if st.get("axis", 0) > 0:      # a soft box right behind the camera, a little above: the sparkle on every bristle tip
        facing("axis", 0, st.get("axis_el", 12), k * 3.5, (k * st.get("axis_w", 0.8), k * st.get("axis_w", 0.8), 1), st["axis"])
        ax_ = bpy.context.active_object
        if st.get("axis_spec_only"):   # seen only in reflections: a big sparkle on every rounded tip without flooding the matte shell
            ax_.visible_diffuse = False
        if st.get("axis_only_on"):     # light-linked: the sparkle box lights only the named parts (the bristles), never the shell
            rc_ = bpy.data.collections.new("axis-receivers")
            for o_ in list(sc.objects):
                if o_.type == "MESH" and any(o_.name.startswith(n_) for n_ in st["axis_only_on"]):
                    rc_.objects.link(o_)
            ax_.light_linking.receiver_collection = rc_
for side in ((-1, 1) if st.get("mode") not in ("dark", "white") else ()):   # tall soft boxes either side, a little behind: the vertical highlights on metal
    panel("box%d" % side, (side * k * 1.1, -k * 0.35, zc), (0, math.radians(90), math.radians(side * 20)), (H * 1.6, k * 0.5, 1), st.get("box", 6.0))
    panel("flag%d" % side, (side * k * 0.55, -k * 1.2, zc), (math.radians(90), 0, math.radians(side * 25)), (k * 0.35, H * 1.8, 1), 0.0, "#000000")
if st.get("mode") not in ("dark", "white"):
    panel("top", (0, 0, H + k * 0.9), (0, 0, 0), (k * 1.6, k * 1.6, 1), st.get("top", 3.0))
    panel("front", (0, -k * 2.2, zc), (math.radians(90), 0, 0), (k * 0.9, H * 1.4, 1), st.get("front", 1.2))
for loc, e in (((-0.6, -1.0, 0.8), st.get("key", 900)), ((0.7, -0.8, 0.3), st.get("fill", 350))) if st.get("mode") not in ("dark", "white") else ((((0.0, -1.0, 0.4), st.get("key", 120)),) if st.get("mode") == "dark" else ()):
    l = bpy.data.objects.new("l", bpy.data.lights.new("l", "AREA")); l.data.energy = e * (k / 10) ** 2; l.data.size = k * 0.8
    l.location = Vector(loc) * k * 1.6 + Vector((0, 0, zc)); sc.collection.objects.link(l)
    l.rotation_euler = (Vector((0, 0, zc)) - l.location).to_track_quat("-Z", "Y").to_euler()

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
cam.location = (0, -k * 6, zc); cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.type = "ORTHO"   # no perspective: the outline reads true. Auto sensor fit: the scale spans the longer side
W_ext = max(D, M.get("width", D)); fit = M.get("frame", 1.12)
cam.data.ortho_scale = max(H * fit, W_ext * fit * RH / RW) if RH >= RW else max(W_ext * fit, H * fit * RW / RH)
if M.get("autofit") or os.environ.get("KIT_AUTOFIT"):     # frame whatever the posed product occupies (an open case is wider than closed)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == "MESH" and o.visible_camera for c in o.bound_box]
    x0_, x1_ = min(p.x for p in pts), max(p.x for p in pts); z0_, z1_ = min(p.z for p in pts), max(p.z for p in pts)
    cam.location = ((x0_ + x1_) / 2, -k * 6, (z0_ + z1_) / 2)
    ww, hh = (x1_ - x0_) * fit, (z1_ - z0_) * fit
    cam.data.ortho_scale = max(ww, hh * RW / RH) if RW >= RH else max(hh, ww * RH / RW)
if M.get("perspective") or os.environ.get("KIT_LENS"):   # a perspective camera when the reference was shot with one
    cam.data.type = "PERSP"; cam.data.lens = float(os.environ.get("KIT_LENS", M.get("perspective", 85)))
    cam.data.sensor_fit = "AUTO"; cam.data.sensor_width = 36
    import mathutils
    ext = cam.data.ortho_scale
    dist = ext / 36 * cam.data.lens * 1.0
    cam.location = (cam.location.x, -dist, cam.location.z)
    cam.data.clip_end = dist * 10
sc.camera = cam
sc.render.engine = "CYCLES"; sc.cycles.samples = int(os.environ.get("KIT_SAMPLES", st.get("samples", 160))); sc.cycles.use_denoising = True
try:
    sc.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "METAL"; prefs.get_devices()
    for dv in prefs.devices:
        dv.use = True
except Exception:
    pass
sc.render.resolution_x = RW; sc.render.resolution_y = RH; sc.render.film_transparent = transparent
sc.view_settings.view_transform = st.get("view", "Standard"); sc.render.filepath = out
bpy.ops.render.render(write_still=True)
if save:
    bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=save)
