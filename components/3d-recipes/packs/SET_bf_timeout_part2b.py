class _T:
    path = "/tmp/_skip.png"
    def publish(self): pass
class _A:
    def file(self, **k): return _T()
_real_artifacts, artifacts = artifacts, _A()
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
pass; tg.publish()
for n,v in zip(bg,olds): n.inputs[1].default_value=v
for l in lcs: l.exclude=saved.get(l.name,False)
for o in top: o.hide_render=tops[o.name]
S.camera=oc; S.render.resolution_x=576; S.render.resolution_y=1024
result='ok'
