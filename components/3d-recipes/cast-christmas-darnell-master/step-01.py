import bpy, math
from mathutils import Vector
sc=bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o,do_unlink=True)
sc.unit_settings.system='METRIC'
col=bpy.data.collections.new('SET_cast-christmas-darnell-master');sc.collection.children.link(col)
def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True
 m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1)
 m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
 return m
grey=mat('LAYOUT_grey',(.42,.42,.42))
skin=mat('LAYOUT_skin_grey',(.3,.3,.3))
bump=mat('LAYOUT_bump_dark',(.12,.12,.12))
bg=mat('ENV_cream',(.78,.72,.6))
rig=bpy.data.objects.new('HERO_darnell_root',None);col.objects.link(rig)
def ell(n,loc,scale,m,rot=(0,0,0)):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=loc,rotation=rot)
 o=bpy.context.object;o.name=n;o.scale=scale;o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o);o.parent=rig;return o
def cyl(n,loc,r,d,m,rot=(0,0,0)):
 bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=d,location=loc,rotation=rot)
 o=bpy.context.object;o.name=n;o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o);o.parent=rig;return o
# 1.78 m, solid slightly soft build (belly forward)
ell('HERO_torso',(0,0,1.22),(.235,.15,.30),grey)
ell('HERO_belly',(0,-.04,1.06),(.215,.155,.17),grey)
ell('HERO_hips',(0,0,.92),(.2,.13,.11),grey)
ell('HERO_neck',(0,-.005,1.545),(.06,.06,.06),skin)
ell('HERO_head',(0,-.01,1.665),(.1,.105,.125),skin)
ell('HERO_jaw',(0,-.03,1.585),(.095,.09,.06),skin)
ell('HERO_hair_fade',(0,.0,1.755),(.098,.1,.04),grey)
for x in (-1,1):
 ell('HERO_ear_%d'%x,(.1*x,0,1.665),(.016,.022,.032),skin)
 cyl('HERO_upperarm_%d'%x,(.27*x,0,1.27),.055,.32,grey,(0,math.radians(-8*x),0))
 cyl('HERO_forearm_%d'%x,(.3*x,-.01,.98),.047,.28,grey,(0,math.radians(-6*x),0))
 ell('HERO_hand_%d'%x,(.315*x,-.01,.8),(.04,.03,.07),skin)
 cyl('HERO_leg_%d'%x,(.1*x,0,.47),.078,.82,grey)
 ell('HERO_slipper_%d'%x,(.1*x,-.06,.035),(.055,.13,.035),grey)
# raised razor bumps on his right jaw and under-chin (his right = -X)
import random;random.seed(4)
for i in range(16):
 a=random.uniform(math.radians(200),math.radians(280));z=random.uniform(1.545,1.6)
 p=Vector((.093*math.cos(a),-.03+.088*math.sin(a),z))
 s=random.uniform(.004,.007);ell('MARK_bump_%d'%i,p,(s,s,s),bump)
rig.rotation_euler=(0,0,math.radians(35))
# stage
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,0));f=bpy.context.object;f.name='ENV_floor';f.data.materials.append(bg)
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,2.5,5),rotation=(math.pi/2,0,0));w=bpy.context.object;w.name='ENV_backdrop';w.data.materials.append(bg)
for o in (f,w):
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o)
bpy.ops.object.camera_add(location=(0,-5.2,1.0));cam=bpy.context.object;cam.name='CAM_cast_master'
cam.rotation_euler=(Vector((0,0,.93))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=50;cam.data.sensor_fit='AUTO'
for c in cam.users_collection:c.objects.unlink(cam)
col.objects.link(cam);sc.camera=cam
for n,loc,e,s in [('LGT_key',(-1.6,-3,2.6),900,2.0),('LGT_fill',(1.8,-2.8,1.8),500,2.0),('LGT_top',(0,-.5,3.5),200,1.5)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=n;o.data.energy=e;o.data.size=s
 o.rotation_euler=(Vector((0,0,1.4))-o.location).to_track_quat('-Z','Y').to_euler()
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o)
sc.world=bpy.data.worlds.new('ENV_world');sc.world.color=(.35,.33,.3)
sc.render.engine='BLENDER_EEVEE';sc.render.resolution_x=810;sc.render.resolution_y=1440;sc.render.resolution_percentage=100
try: sc.eevee.taa_render_samples=8
except Exception: pass
sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
t=artifacts.file(name='darnell-master-blockout.png',media_type='image/png');sc.render.filepath=str(t.path);bpy.ops.render.render(write_still=True);t.publish()
result={'height_m':1.78,'turn_deg':35,'camera':cam.name,'bumps':16,'objects':len(col.objects)}
