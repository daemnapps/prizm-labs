import bpy, math, bmesh
from mathutils import Vector
sc=bpy.context.scene
col=bpy.data.collections['SET_cast-christmas-marcus-master']
bg=bpy.data.materials['ENV_cream']
for n in ('ENV_floor','ENV_backdrop'):
 o=bpy.data.objects.get(n)
 if o: bpy.data.objects.remove(o,do_unlink=True)
# seamless cyclorama: flat floor curving up into the back wall, no horizon line
me=bpy.data.meshes.new('ENV_cyc');bm=bmesh.new()
R=1.5;cy=1.6
prof2=[]
for i in range(0,12): prof2.append((-6+i*(cy+6)/12,0.0))
for k in range(0,17):
 a=-math.pi/2+k*(math.pi/2)/16
 prof2.append((cy+R*math.cos(a),R+R*math.sin(a)))
prof2.append((cy+R,8.0))
W=8
rows=[]
for (y,z) in prof2:
 rows.append([bm.verts.new((x,y,z)) for x in (-W,W)])
for i in range(len(rows)-1):
 bm.faces.new((rows[i][0],rows[i][1],rows[i+1][1],rows[i+1][0]))
bm.to_mesh(me);bm.free()
cyc=bpy.data.objects.new('ENV_cyc',me);col.objects.link(cyc);me.materials.append(bg)
for p in me.polygons:p.use_smooth=True
# camera a touch further back so head-to-shoes sits inside the centre with clear cream margins
cam=bpy.data.objects['CAM_cast_master'];cam.location=(0,-3.25,0.95);cam.data.lens=40
cam.rotation_euler=(Vector((0,0,.94))-cam.location).to_track_quat('-Z','Y').to_euler()
for n,e in [('LGT_key',150),('LGT_fill',95),('LGT_top',40)]:bpy.data.objects[n].data.energy=e
sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
t=artifacts.file(name='marcus-master-blockout-v2.png',media_type='image/png');sc.render.filepath=str(t.path);bpy.ops.render.render(write_still=True);t.publish()
from bpy_extras.object_utils import world_to_camera_view as w2c
top=w2c(sc,cam,Vector((0,0,1.86)));foot=w2c(sc,cam,Vector((0,-.05,0)))
result={'head_top_y':round(top.y,3),'feet_y':round(foot.y,3)}
