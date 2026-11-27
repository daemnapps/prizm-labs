class _T:
    path = "/tmp/_skip.png"
    def publish(self): pass
class _A:
    def file(self, **k): return _T()
_real_artifacts, artifacts = artifacts, _A()
# step 1
import bpy, bmesh, math
from mathutils import Vector

sc = bpy.context.scene
H, W, D = 0.1115, 0.0698, 0.0365   # FLEX true size (m): 111.5 x 69.8 x 36.5 mm

def mat(name, rgb, rough, metal=0.0, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 6.0
    return m

M_body = mat("MAT_shell_matte_black", (0.025, 0.025, 0.027), 0.55)
M_pad = mat("MAT_bristle_face", (0.012, 0.012, 0.013), 0.95)
M_band = mat("MAT_control_band", (0.04, 0.04, 0.042), 0.45)
M_line = mat("MAT_light_line", (1, 1, 1), 0.3, emit=(1, 1, 1))
M_base = mat("MAT_dome_base_gloss", (0.06, 0.06, 0.065), 0.08, metal=0.7)
M_floor = mat("MAT_backdrop_white", (0.95, 0.95, 0.95), 0.9)

# the pod: an egg, narrower at the top, flatter front-to-back, rounded dome bottom
bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=96, radius=1.0)
o = bpy.context.active_object; o.name = "HERO_flex"
for v in o.data.vertices:
    x, y, z = v.co
    w = 1.0 - 0.20 * z                         # teardrop: wider low, narrow at the tip
    dy = D / 2 * w * (0.80 if y < 0 else 1.0)  # bristle front flatter than the rounded back
    v.co = Vector((x * W / 2 * w, y * dy, z * H / 2))
for m in (M_body, M_pad, M_band, M_line, M_base):
    o.data.materials.append(m)
for p in o.data.polygons:
    c = p.center; t = c.z / (H / 2)
    if t < -0.66:
        p.material_index = 4                    # glossy dome base
    elif t < -0.60:
        p.material_index = 3                    # thin white light line
    elif t < -0.45:
        p.material_index = 2                    # control band (minus, power, plus)
    elif p.normal.y < -0.45 and t > -0.40:
        p.material_index = 1                    # bristle face, front only
    else:
        p.material_index = 0
bpy.ops.object.shade_smooth()
o.location = (0, 0, H / 2)                      # stands on its dome bottom at the origin

bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0, 0, 0))
f = bpy.context.active_object; f.name = "ENV_backdrop"; f.data.materials.append(M_floor)

world = bpy.data.worlds.new("WORLD_studio"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.6

bpy.ops.object.light_add(type="SUN", location=(0.3, -0.4, 0.6)); k = bpy.context.active_object
k.name = "LGT_key"; k.data.energy = 3.0; k.rotation_euler = (math.radians(45), 0, math.radians(30))
bpy.ops.object.light_add(type="POINT", location=(-0.3, -0.3, 0.2)); fl = bpy.context.active_object
fl.name = "LGT_fill"; fl.data.energy = 25

target = bpy.data.objects.new("TGT_flex", None); sc.collection.objects.link(target); target.location = (0, 0, H / 2)
R = 0.45
cams = {"CAM_front": (0, -R, H / 2), "CAM_three_quarter": (R * math.sin(math.radians(35)), -R * math.cos(math.radians(35)), H / 2),
        "CAM_side": (R, 0, H / 2), "CAM_back": (0, R, H / 2),
        "CAM_above": (0, -0.12, H / 2 + 0.43), "CAM_below": (0, -0.30, H / 2 - 0.33)}
for n, loc in cams.items():
    cd = bpy.data.cameras.new(n); cd.lens = 85
    c = bpy.data.objects.new(n, cd); sc.collection.objects.link(c); c.location = loc
    tc = c.constraints.new("TRACK_TO"); tc.target = target; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
f.hide_render = False

sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 768; sc.render.resolution_y = 768
sc.view_settings.view_transform = "Standard"
out = {}
for n in ("CAM_front", "CAM_side", "CAM_above", "CAM_below"):
    sc.camera = bpy.data.objects[n]
    if n == "CAM_below":
        f.hide_render = True                    # looking up from under the backdrop
    tgt = artifacts.file(name=n.lower() + ".png", media_type="image/png")
    sc.render.filepath = str(tgt.path); sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
    pass; tgt.publish(); out[n] = "rendered"
    f.hide_render = False
d = o.dimensions
result = {"dims_mm": [round(d.x * 1000, 1), round(d.y * 1000, 1), round(d.z * 1000, 1)], "renders": out}
artifacts = _real_artifacts
# step 2
import bpy, math
sc = bpy.context.scene
pad = bpy.data.materials["MAT_bristle_face"]
nt = pad.node_tree; b = nt.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.11, 0.11, 0.12, 1); b.inputs["Roughness"].default_value = 1.0
vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 1400.0
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.9
nt.links.new(vor.outputs["Distance"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
H = 0.1115
for n, loc in {"CAM_above": (0, -0.05, H / 2 + 0.44), "CAM_below": (0, -0.10, H / 2 - 0.42)}.items():
    bpy.data.objects[n].location = loc
bpy.data.objects["ENV_backdrop"].hide_render = True
w = sc.world.node_tree.nodes["Background"]; w.inputs[0].default_value = (1, 1, 1, 1); w.inputs[1].default_value = 0.9
out = {}
for n in ("CAM_front", "CAM_above", "CAM_below"):
    sc.camera = bpy.data.objects[n]
    t = artifacts.file(name=n.lower() + "-v2.png", media_type="image/png")
    sc.render.filepath = str(t.path); sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True); t.publish(); out[n] = "ok"
result = out
