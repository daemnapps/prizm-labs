import bpy, math
from mathutils import Vector
sc=bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o,do_unlink=True)
sc.unit_settings.system='METRIC'
col=bpy.data.collections.new('SET_cast-christmas-grandma-master');sc.collection.children.link(col)
def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True
 m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1)
 m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
 return m
grey=mat('LAYOUT_grey',(.42,.42,.42))
skin=mat('LAYOUT_skin_grey',(.3,.3,.3))
bg=mat('ENV_cream',(.78,.72,.6))
rig=bpy.data.objects.new('HERO_grandma_root',None);col.objects.link(rig)
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
# 1.55 m, short sturdy build: wide torso, full hips, A-line skirt to mid-calf
ell('HERO_torso',(0,0,1.06),(.22,.15,.24),grey)
ell('HERO_bust',(0,-.05,1.12),(.2,.12,.1),grey)
ell('HERO_hips',(0,0,.84),(.22,.15,.12),grey)
cyl('HERO_skirt',(0,0,.56),.3,.5,grey,r2=.21)
ell('HERO_neck',(0,-.005,1.315),(.055,.055,.05),skin)
ell('HERO_head',(0,-.01,1.42),(.1,.1,.11),skin)
ell('HERO_cheeks',(0,-.035,1.385),(.1,.085,.06),skin)
ell('HERO_hair_curls',(0,.01,1.48),(.105,.105,.06),grey)
# enormous gift bow on top of the head: two loops and a knot
ell('PROP_bow_knot',(0,0,1.555),(.035,.03,.03),grey)
for x in (-1,1):
 ell('PROP_bow_loop_%d'%x,(.075*x,0,1.575),(.075,.03,.045),grey,(0,math.radians(20*x),0))
# arms held away from the torso
for x in (-1,1):
 cyl('HERO_upperarm_%d'%x,(.29*x,0,1.08),.058,.28,grey,(0,math.radians(-28*x),0))
 cyl('HERO_forearm_%d'%x,(.38*x,-.01,.86),.05,.25,grey,(0,math.radians(-22*x),0))
 ell('HERO_hand_%d'%x,(.43*x,-.01,.7),(.04,.03,.065),skin)
 cyl('HERO_calf_%d'%x,(.09*x,0,.17),.055,.3,skin)
 ell('HERO_shoe_%d'%x,(.09*x,-.05,.03),(.05,.11,.03),grey)
rig.rotation_euler=(0,0,math.radians(35))
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,0));f=bpy.context.object;f.name='ENV_floor';f.data.materials.append(bg)
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,2.5,5),rotation=(math.pi/2,0,0));w=bpy.context.object;w.name='ENV_backdrop';w.data.materials.append(bg)
for o in (f,w):
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o)
bpy.ops.object.camera_add(location=(0,-2.45,.85));cam=bpy.context.object;cam.name='CAM_cast_master'
cam.rotation_euler=(Vector((0,0,.82))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=40;cam.data.sensor_fit='AUTO'
for c in cam.users_collection:c.objects.unlink(cam)
col.objects.link(cam);sc.camera=cam
for n,loc,e,s in [('LGT_key',(-1.6,-3,2.6),120,2.0),('LGT_fill',(1.8,-2.8,1.8),70,2.0),('LGT_top',(0,-.5,3.5),30,1.5)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=n;o.data.energy=e;o.data.size=s
 o.rotation_euler=(Vector((0,0,1.2))-o.location).to_track_quat('-Z','Y').to_euler()
 for c in o.users_collection:c.objects.unlink(o)
 col.objects.link(o)
sc.world=bpy.data.worlds.new('ENV_world');sc.world.color=(.12,.12,.11)
sc.view_settings.view_transform='Standard'
sc.render.engine='BLENDER_EEVEE';sc.render.resolution_x=810;sc.render.resolution_y=1440;sc.render.resolution_percentage=100
try: sc.eevee.taa_render_samples=8
except Exception: pass
sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
t=artifacts.file(name='grandma-master-blockout.png',media_type='image/png');sc.render.filepath=str(t.path);bpy.ops.render.render(write_still=True);t.publish()
from bpy_extras.object_utils import world_to_camera_view as w2c
top=w2c(sc,cam,Vector((0,0,1.6)));foot=w2c(sc,cam,Vector((0,0,0)))
result={'height_m':1.55,'turn_deg':35,'head_top_y':round(top.y,3),'feet_y':round(foot.y,3),'objects':len(col.objects)}
