"""The shared studio for the product builders (run inside Blender): a camera
framed on the product, two soft lights, a white world, Cycles. Nothing here
names a product."""
import bpy, math


def mat(name, d, img=None, rgb=None, rough=0.4, clear=0.2):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = clear
    if img:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(d / img)); t.extension = "EXTEND"
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = list(rgb[:3]) + [1]
    return m


def lin(c):
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def shoot(objs, H, W, out, RW=800, RH=1000, transparent=False, yaw=0.0, tilt=0.0, save=None):
    for o in objs:
        o.rotation_euler = (math.radians(tilt), 0, math.radians(yaw))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
    dist = max(60, max(H, W * 1.25) * 5.7)
    cam.location = (0, -dist, H / 2); cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = max(H, W * RH / RW) * 1.6   # no perspective: the outline reads true
    bpy.context.scene.camera = cam
    for loc, e in (((-18, -30, 22), 3500), ((20, -20, 8), 1200)):
        k = dist / 60
        l = bpy.data.objects.new("l", bpy.data.lights.new("l", "AREA")); l.data.energy = e * k * k; l.data.size = 25 * k
        l.location = tuple(v * k for v in loc)
        l.rotation_euler = (math.radians(60), 0, math.radians(-30 if loc[0] < 0 else 30)); bpy.context.scene.collection.objects.link(l)
    w = bpy.data.worlds.new("w"); w.use_nodes = True; bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1, 1, 1, 1); bg.inputs["Strength"].default_value = 0.8; bpy.context.scene.world = w
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 96
    sc.render.resolution_x = RW; sc.render.resolution_y = RH; sc.render.film_transparent = transparent
    sc.view_settings.view_transform = "Standard"; sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    if save:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=save)


def args():
    import sys
    a = sys.argv[sys.argv.index("--") + 1:]
    return dict(kit=a[0], out=a[1], yaw=float(a[2]) if len(a) > 2 else 0.0, tilt=float(a[3]) if len(a) > 3 else 0.0,
                RW=int(a[4]) if len(a) > 4 else 800, RH=int(a[5]) if len(a) > 5 else 1000,
                transparent=(a[6] == "1") if len(a) > 6 else False, save=a[7] if len(a) > 7 else None)
