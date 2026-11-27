import bpy, math
from mathutils import Vector
sc=bpy.context.scene
cam=bpy.data.objects['CAM_cast_master'];cam.location=(0,-2.75,1.0);cam.data.lens=40
cam.rotation_euler=(Vector((0,0,.95))-cam.location).to_track_quat('-Z','Y').to_euler()
for n,e in [('LGT_key',120),('LGT_fill',70),('LGT_top',30)]:bpy.data.objects[n].data.energy=e
sc.world.color=(.12,.12,.11)
for m in bpy.data.materials:
 if m.name.startswith('LAYOUT') or m.name.startswith('ENV'):
  pass
sc.view_settings.view_transform='Standard'
sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
t=artifacts.file(name='darnell-master-blockout-v2.png',media_type='image/png');sc.render.filepath=str(t.path);bpy.ops.render.render(write_still=True);t.publish()
hd=bpy.data.objects['HERO_head'].matrix_world.translation
from bpy_extras.object_utils import world_to_camera_view as w2c
top=w2c(sc,cam,Vector((hd.x,hd.y,1.79)));foot=w2c(sc,cam,Vector((0,0,0)))
result={'head_top_y':round(top.y,3),'feet_y':round(foot.y,3),'turn_deg':math.degrees(bpy.data.objects['HERO_darnell_root'].rotation_euler.z)}
