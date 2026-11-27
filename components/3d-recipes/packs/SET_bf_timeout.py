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
    pass; t.publish(); out[n] = "ok"
result = out
# step 20
import bpy, math
S=bpy.context.scene; O=bpy.data.objects
C=bpy.data.collections.new('SET_bf_timeout'); S.collection.children.link(C)
def mat(n,hexc,rough=.6,metal=0):
    m=bpy.data.materials.new(n); m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value=[pow(int(hexc[i:i+2],16)/255,2.2) for i in (0,2,4)]+[1]
    b.inputs['Roughness'].default_value=rough; b.inputs['Metallic'].default_value=metal
    return m
INK=mat('TO_ink','1A1A1A',.5); CARD=mat('TO_card','F5F2EC',.7); DEEP=mat('TO_deep','908448',.6); STEEL=mat('TO_steel','C8C8C8',.3,1)
# ink to deep gold ground
G=mat('TO_ground','908448',.55); nt=G.node_tree
tc=nt.nodes.new('ShaderNodeTexCoord'); sp=nt.nodes.new('ShaderNodeSeparateXYZ'); mr=nt.nodes.new('ShaderNodeMapRange'); cr=nt.nodes.new('ShaderNodeValToRGB')
nt.links.new(tc.outputs['Object'],sp.inputs[0]); nt.links.new(sp.outputs['Y'],mr.inputs['Value']); mr.inputs['From Min'].default_value=-.24; mr.inputs['From Max'].default_value=.24
nt.links.new(mr.outputs['Result'],cr.inputs['Fac'])
cr.color_ramp.elements[0].color=[pow(x/255,2.2) for x in (0x90,0x84,0x48)]+[1]; cr.color_ramp.elements[1].color=[pow(0x1A/255,2.2)]*3+[1]
nt.links.new(cr.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Base Color'])
def link(o): C.objects.link(o); return o
def f(fr): return .24-fr*.48
def box(name,x0,x1,fa,fb,z,m,h=.0008):
    me=bpy.data.meshes.new(name); y0,y1=f(fb),f(fa)
    v=[(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z),(x0,y0,z+h),(x1,y0,z+h),(x1,y1,z+h),(x0,y1,z+h)]
    me.from_pydata(v,[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]); me.materials.append(m)
    return link(bpy.data.objects.new(name,me))
def txt(name,body,size,x,fr,m,align='CENTER',width=None,bold=.012):
    cu=bpy.data.curves.new(name,'FONT'); cu.body=body; cu.size=size; cu.align_x=align; cu.extrude=.0001; cu.offset=size*bold
    o=link(bpy.data.objects.new(name,cu)); o.location=(x,f(fr),.0022); cu.materials.append(m)
    bpy.context.view_layer.update()
    if width:
        cu.size=size*width/o.dimensions.x; cu.offset=cu.size*bold
    return o
me=bpy.data.meshes.new('TO_ground'); me.from_pydata([(-.54,-.96,0),(.54,-.96,0),(.54,.96,0),(-.54,.96,0)],[],[(0,1,2,3)]); me.materials.append(G); link(bpy.data.objects.new('TO_ground',me))
box('TO_card',-.115,.115,.14,.60,0,CARD,.0012)
# padlock with a curled hair for a shackle
box('TO_lock_body',-.013,.013,.183,.215,.0012,INK,.003)
pts=[]
for i in range(40):
    t=i/39; a=math.pi*t; pts.append((-.0085*math.cos(a), f(.183)+.0005+.0125*math.sin(a)+.002,0.003))
for i in range(1,26):
    t=i/25; a=-t*math.pi*2.6; r=.0065*(1-t*.75); pts.append((.0085+r*(math.cos(a)-1)*-1*0+ r*math.sin(a)*.8, f(.183)+.0025-r+r*math.cos(a)*1, .003))
cu=bpy.data.curves.new('TO_hair','CURVE'); cu.dimensions='3D'; cu.bevel_depth=.0013
sp_=cu.splines.new('POLY'); sp_.points.add(len(pts)-1)
for p,c in zip(sp_.points,pts): p.co=(c[0],c[1],c[2],1)
cu.materials.append(INK); link(bpy.data.objects.new('TO_hair',cu))
txt('TO_head','Razor Bumps Call Timeout',.014,0,.245,INK,width=.196,bold=.02)
txt('TO_sub1','Black Friday at brand_a',.0115,0,.277,INK,width=.15)
txt('TO_sub2','FLEX starting at $46',.0115,0,.302,INK,width=.15,bold=.03)
box('TO_pay_border',-.098,.098,.322,.432,.0012,DEEP,.0002)
box('TO_pay_fill',-.0965,.0965,.325,.429,.0014,CARD,.0002)
txt('TO_denied','DENIED',.05,0,.408,INK,width=.168,bold=.05)
txt('TO_clock_t','NOV 25 TO NOV 28',.012,.011,.48,INK,width=.122,bold=.03)
bpy.ops.mesh.primitive_torus_add(major_radius=.0065,minor_radius=.0011,location=(-.067,f(.4735),.0022)); t=bpy.context.object
for c in list(t.users_collection): c.objects.unlink(t)
C.objects.link(t); t.name='TO_clock'; t.scale.z=.3; t.data.materials.append(INK)
box('TO_clock_h',-.0675,-.0665,.466,.4745,.0022,INK,.0002)
box('TO_clock_m',-.0675,-.062,.4735,.4745,.0022,INK,.0002)
box('TO_btn_a',-.098,-.004,.515,.565,.0012,INK,.0006)
box('TO_btn_b',.004,.098,.515,.565,.0012,DEEP,.0006)
txt('TO_btn_at','SHOP FLEX',.012,-.051,.547,CARD,width=.066,bold=.03)
txt('TO_btn_bt','Cancel',.012,.051,.547,CARD,width=.042)
# FLEX lying flat under the panel, true size, bristle face up
H=O['HERO_flex']; p=H.copy(); C.objects.link(p); p.name='TO_flex_product'
if 'hf_id' in p: del p['hf_id']
p.location=(-.012,f(.735),.0172); p.rotation_euler=(-math.pi/2,0,math.radians(9))
# steel stopwatch at the frame edge
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.03,depth=.012,location=(.122,f(.775),.006)); w=bpy.context.object
for c in list(w.users_collection): c.objects.unlink(w)
C.objects.link(w); w.name='TO_watch'; w.data.materials.append(STEEL)
sd=bpy.data.lights.new('TO_sun','SUN'); sd.energy=5; sd.color=(1,.86,.68); sd.angle=math.radians(1); sun=link(bpy.data.objects.new('TO_sun',sd)); sun.rotation_euler=(math.radians(62),math.radians(-28),0)
cd=bpy.data.cameras.new('CAM_bf_timeout'); cd.lens=100; cd.sensor_width=36
cam=link(bpy.data.objects.new('CAM_bf_timeout',cd)); cam.location=(0,0,1.333)
for o in C.all_objects:
    if 'hf_id' in o: del o['hf_id']
W=S.world; bg=[n for n in W.node_tree.nodes if n.type=='BACKGROUND']
top=list(S.collection.objects); tops={o.name:o.hide_render for o in top}
for o in top: o.hide_render=True
lcs=bpy.context.view_layer.layer_collection.children
saved={l.name:l.exclude for l in lcs}
for l in lcs: l.exclude=(l.name!='SET_bf_timeout')
oc=S.camera; S.camera=cam
olds=[n.inputs[1].default_value for n in bg]
for n in bg: n.inputs[1].default_value=.2
S.render.engine='BLENDER_EEVEE'; S.render.resolution_x=576; S.render.resolution_y=1024
tg=artifacts.file(name='timeout-v1.png',media_type='image/png'); S.render.filepath=str(tg.path)
S.render.image_settings.media_type='IMAGE'; S.render.image_settings.file_format='PNG'
pass; tg.publish()
for n,v in zip(bg,olds): n.inputs[1].default_value=v
for l in lcs: l.exclude=saved.get(l.name,False)
for o in top: o.hide_render=tops[o.name]
S.camera=oc
result='ok'
artifacts = _real_artifacts
# step 21
import bpy, math
S=bpy.context.scene; O=bpy.data.objects
def f(fr): return .24-fr*.48
O['TO_head'].location.y=f(.243)
for n,fr,w in (('TO_sub1',.272,.128),('TO_sub2',.303,.128)):
    o=O[n]; o.location.y=f(fr); bpy.context.view_layer.update()
    o.data.size*=w/o.dimensions.x
O['TO_sun'].rotation_euler=(math.radians(-58),math.radians(-30),0)
W=S.world; bg=[n for n in W.node_tree.nodes if n.type=='BACKGROUND']
top=list(S.collection.objects); tops={o.name:o.hide_render for o in top}
for o in top: o.hide_render=True
lcs=bpy.context.view_layer.layer_collection.children
saved={l.name:l.exclude for l in lcs}
for l in lcs: l.exclude=(l.name!='SET_bf_timeout')
oc=S.camera; S.camera=O['CAM_bf_timeout']
olds=[n.inputs[1].default_value for n in bg]
for n in bg: n.inputs[1].default_value=.2
S.render.engine='BLENDER_EEVEE'; S.render.resolution_x=1152; S.render.resolution_y=2048
tg=artifacts.file(name='timeout-v2.png',media_type='image/png'); S.render.filepath=str(tg.path)
S.render.image_settings.media_type='IMAGE'; S.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True); tg.publish()
for n,v in zip(bg,olds): n.inputs[1].default_value=v
for l in lcs: l.exclude=saved.get(l.name,False)
for o in top: o.hide_render=tops[o.name]
S.camera=oc; S.render.resolution_x=576; S.render.resolution_y=1024
result='ok'
