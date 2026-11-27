import bpy, hashlib
out = {}
for c in bpy.data.collections:
    if c.name != 'SET_bf_timeout':
        continue
    objs = [o for o in c.all_objects if o.type == 'MESH']
    h = hashlib.md5()
    P = F = 0
    for o in sorted(objs, key=lambda o: o.name):
        m = o.data
        P += len(m.vertices)
        F += len(m.polygons)
        for v in m.vertices:
            h.update(("%.4f,%.4f,%.4f;" % tuple(o.matrix_world @ v.co)).encode())
    out[c.name] = {'parts': len(objs), 'points': P, 'faces': F,
                   'mats': sorted({s.material.name for o in objs for s in o.material_slots if s.material}),
                   'hash': h.hexdigest()}
out['hero'] = [(o.name, len(o.data.vertices), len(o.data.polygons)) for o in bpy.data.objects if o.name == 'HERO_flex']
result = out
