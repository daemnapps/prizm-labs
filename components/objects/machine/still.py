import bpy, sys, os, math
from mathutils import Vector
src, out = sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
mn=Vector((1e9,)*3); mx=Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); mn=Vector(map(min,mn,w)); mx=Vector(map(max,mx,w))
ctr=(mn+mx)/2; r=(mx-mn).length/2
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); bpy.context.scene.collection.objects.link(cam)
cam.data.lens=50; d=r*3.2
cam.location=ctr+Vector((d*0.6,-d*0.8,d*0.25))
cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.context.scene.camera=cam
for loc,e in [((1,-1,1.5),900),((-1.5,-0.5,0.5),300),((0,1.5,1),500)]:
    L=bpy.data.objects.new('l',bpy.data.lights.new('l','AREA')); L.data.energy=e*r*r; L.data.size=r*2
    L.location=ctr+Vector(loc)*r*3; L.rotation_euler=(ctr-L.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.collection.objects.link(L)
w=bpy.data.worlds.new('w'); w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.02,0.02,0.025,1)
bpy.context.scene.world=w
s=bpy.context.scene; s.render.engine='BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
s.render.resolution_x=s.render.resolution_y=900; s.render.filepath=out
bpy.ops.render.render(write_still=True)
