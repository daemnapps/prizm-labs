import bpy, math, random, mathutils
random.seed(11)
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
S = bpy.context.scene
def mat(name, rgb, rough=.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m
SKIN = mat("MAT_skin", (.13, .055, .028), .42); BUMP = mat("MAT_pimple", (.22, .045, .03), .35); SPOT = mat("MAT_spot", (.045, .017, .010), .55); JAW = mat("MAT_beard", (.045, .025, .017), .7)
# each half is a cheek and jaw, about 6 cm wide and 11 cm tall, curving away from the lens at the jaw
def half(tag, cx):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, radius=1, location=(cx, .045, 0))
    c = bpy.context.object; c.name = "HERO_cheek_" + tag; c.scale = (.06, .05, .085); bpy.ops.object.shade_smooth(); c.data.materials.append(SKIN)
    return c
def at(cx, u, v):
    x, z = u * .027, v * .062
    y = .045 - .05 * math.sqrt(max(.02, 1 - (x / .06) ** 2 - (z / .085) ** 2))
    n = mathutils.Vector((x / .06 ** 2, (y - .045) / .05 ** 2, z / .085 ** 2)).normalized()
    return (cx + x, y, z), n
def blob(name, cx, u, v, r, flat, m):
    p, n = at(cx, u, v)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1, location=p)
    o = bpy.context.object; o.name = name; o.scale = (r, r * random.uniform(.85, 1.15), r * flat); o.rotation_euler = n.to_track_quat('Z', 'Y').to_euler(); bpy.ops.object.shade_smooth(); o.data.materials.append(m)
L, R = -.0275, .0275
half("pimples", L); half("spots", R)
pts = []
while len(pts) < 20:
    u, v = random.uniform(-.8, .8), random.uniform(-.35, .85)
    if all((u - a) ** 2 + ((v - b) * 2) ** 2 > .05 for a, b in pts): pts.append((u, v))
for i, (u, v) in enumerate(pts):
    r = random.uniform(.0016, .0034)
    blob("BUMP_%02d" % i, L, u, v, r, .6, BUMP)          # raised, left
    blob("SPOT_%02d" % i, R, u, v, r * 1.15, .03, SPOT)  # same places, flat, right
# the dividing line the swipe has
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -.03, 0)); d = bpy.context.object; d.name = "ENV_divider"; d.scale = (.0006, .001, .3)
wm = mat("MAT_white", (1, 1, 1), .8); d.data.materials.append(wm)
# the gap behind the two halves stays dark
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, .12, 0), rotation=(math.pi / 2, 0, 0)); bg = bpy.context.object; bg.name = "ENV_back"; bg.scale = (1, 1, 1); bg.data.materials.append(JAW)
w = bpy.data.worlds.new("W") if not S.world else S.world; S.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.55, .6, .68, 1); w.node_tree.nodes["Background"].inputs[1].default_value = .5
def lamp(name, kind, loc, e, col, tgt=(0, 0, 0)):
    l = bpy.data.lights.new(name, kind); l.energy = e; l.color = col; o = bpy.data.objects.new(name, l); S.collection.objects.link(o); o.location = loc
    o.rotation_euler = (mathutils.Vector(tgt) - mathutils.Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
k = lamp("LGT_key", "SUN", (-.5, -.4, .5), 3.2, (1, .97, .92)); k.data.angle = .2
lamp("LGT_fill", "SUN", (.5, -.6, .1), .7, (.9, .95, 1))
cam = bpy.data.cameras.new("CAM_main"); co = bpy.data.objects.new("CAM_main", cam); S.collection.objects.link(co); co.location = (0, -.42, .005); co.rotation_euler = (math.pi / 2, 0, 0)
cam.type = 'PERSP'; cam.sensor_fit = 'VERTICAL'; cam.sensor_height = 36; cam.lens = 36 * .42 / .115 ; cam.dof.use_dof = False; S.camera = co
S.render.engine = 'BLENDER_EEVEE'; S.render.resolution_x, S.render.resolution_y = 810, 1440; S.render.resolution_percentage = 100
S.eevee.taa_render_samples = 8
t = artifacts.file(name="set.png", media_type="image/png"); S.render.filepath = str(t.path); S.render.image_settings.media_type = "IMAGE"; S.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True); t.publish()
result = {"objects": len(bpy.data.objects)}
