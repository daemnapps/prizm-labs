import bpy, math
from mathutils import Vector
sc=bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o,do_unlink=True)
sc.unit_settings.system='METRIC'
col=bpy.data.collections.new('SET_cast-christmas-nia-master');sc.collection.children.link(col)
def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True
 m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1)
 m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
 return m
grey=mat('LAYOUT_grey',(.42,.42,.42))
skin=mat('LAYOUT_skin_grey',(.3,.3,.3))
bg=mat('ENV_cream',(.78,.72,.6))
rig=bpy.data.objects.new('HERO_nia_root',None);col.objects.link(rig)
def ell(n,loc,scale,m,rot=(0,0,0)):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=loc,rotation=rot)
 o=bpy.context.object;o.name=n;o.scale=scale;o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o);o.parent=rig;return o
def cyl(n,loc,r,d,m,rot=(0,0,0),r2=None):
 if r2 is None:
  bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=d,location=loc,rotation=rot)
 else:
  bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=r,radius2=r2,depth=d,location=loc,rotation=rot)
 o=bpy.context.object;o.name=n;o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o);o.parent=rig;return o
# 1.7 m woman, late 30s, average build: sweater to the hips, straight trousers to the ankle
ell('HERO_torso_sweater',(0,0,1.18),(.19,.13,.25),grey)
ell('HERO_bust',(0,-.045,1.24),(.17,.11,.09),grey)
ell('HERO_hips',(0,0,.95),(.18,.13,.1),grey)
ell('HERO_neck',(0,-.005,1.45),(.05,.05,.05),skin)
ell('HERO_head',(0,-.01,1.57),(.095,.1,.115),skin)
ell('HERO_cheeks_broad',(0,-.035,1.535),(.1,.085,.06),skin)
# short natural curls: a close rounded cap
ell('HERO_hair_curls',(0,.01,1.62),(.11,.11,.075),grey)
# rounded glasses: two rings and a bridge in front of the eyes
for x in (-1,1):
 bpy.ops.mesh.primitive_torus_add(major_radius=.026,minor_radius=.004,location=(.038*x,-.105,1.575),rotation=(math.radians(90),0,0))
 g=bpy.context.object;g.name='PROP_glasses_%d'%x;g.data.materials.append(grey)
 for c in g.users_collection:c.objects.unlink(g)
 col.objects.link(g);g.parent=rig
cyl('PROP_glasses_bridge',(0,-.105,1.578),.003,.024,grey,(0,math.radians(90),0))
# small gift-bow hair clip on one side of the curls
ell('PROP_bow_clip_knot',(.085,-.02,1.65),(.014,.012,.012),grey)
for y in (-1,1):
 ell('PROP_bow_clip_loop_%d'%y,(.09,-.02+.022*y,1.66),(.012,.022,.016),grey)
# arms held away from the torso
for x in (-1,1):
 cyl('HERO_upperarm_%d'%x,(.25*x,0,1.22),.05,.3,grey,(0,math.radians(-25*x),0))
 cyl('HERO_forearm_%d'%x,(.33*x,-.01,.98),.044,.27,grey,(0,math.radians(-20*x),0))
 ell('HERO_hand_%d'%x,(.38*x,-.01,.81),(.035,.026,.06),skin)
 cyl('HERO_leg_trousers_%d'%x,(.085*x,0,.46),.065,.84,grey)
 ell('HERO_shoe_%d'%x,(.085*x,-.05,.03),(.05,.12,.03),grey)
rig.rotation_euler=(0,0,math.radians(35))
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,0));f=bpy.context.object;f.name='ENV_floor';f.data.materials.append(bg)
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,2.5,5),rotation=(math.pi/2,0,0));w=bpy.context.object;w.name='ENV_backdrop';w.data.materials.append(bg)
for o in (f,w):
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o)
bpy.ops.object.camera_add(location=(0,-2.75,.92));cam=bpy.context.object;cam.name='CAM_cast_master'
cam.rotation_euler=(Vector((0,0,.88))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=40;cam.data.sensor_fit='AUTO'
for c in cam.users_collection:c.objects.unlink(cam)
col.objects.link(cam);sc.camera=cam
for n,loc,e,s in [('LGT_key',(-1.6,-3,2.8),120,2.0),('LGT_fill',(1.8,-2.8,1.9),70,2.0),('LGT_top',(0,-.5,3.7),30,1.5)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=n;o.data.energy=e;o.data.size=s
 o.rotation_euler=(Vector((0,0,1.3))-o.location).to_track_quat('-Z','Y').to_euler()
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o)
sc.world=bpy.data.worlds.new('ENV_world');sc.world.color=(.12,.12,.11)
sc.view_settings.view_transform='Standard'
sc.render.engine='BLENDER_EEVEE';sc.render.resolution_x=810;sc.render.resolution_y=1440;sc.render.resolution_percentage=100
try: sc.eevee.taa_render_samples=8
except Exception: pass
sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
t=artifacts.file(name='nia-master-blockout.png',media_type='image/png');sc.render.filepath=str(t.path);bpy.ops.render.render(write_still=True);t.publish()
from bpy_extras.object_utils import world_to_camera_view as w2c
top=w2c(sc,cam,Vector((0,0,1.7)));foot=w2c(sc,cam,Vector((0,0,0)))
result={'height_m':1.7,'turn_deg':35,'head_top_y':round(top.y,3),'feet_y':round(foot.y,3),'objects':len(col.objects)}
