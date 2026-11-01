"""
Finishing step for make3d: TRELLIS.2 raw output -> clean textured GLB.

Replaces trellis-mac's KDTree texture baker, which on this Mac (no Metal
toolchain) produced a patchy camouflage texture, washed-out colour (extra
gamma) and a model lying on its back (Z-up instead of glTF Y-up).

  1. decimate the ~2M-face decoder mesh to `target_faces` (default 300K)
  2. clean it: merge verts, drop tiny floating bits, orient every face
     outward (flood-filled voxel shell decides inside vs outside)
  3. Blender: colour each vertex from the TRELLIS.2 voxel colour field
     (k-NN), UV unwrap, bake to a texture, export GLB (Blender's exporter
     also converts TRELLIS's Z-up to glTF's Y-up)
"""
import os
import subprocess
import tempfile

import numpy as np


def finish(verts, faces, coords, attrs, origin, voxel_size, out_glb,
           target_faces=300_000, texture_size=2048, remesh_voxel=0.0, blender="blender"):
    import fast_simplification
    import trimesh
    from scipy import ndimage

    verts = np.asarray(verts, np.float32)
    faces = np.asarray(faces, np.int64)
    if len(faces) > target_faces:
        verts, faces = fast_simplification.simplify(verts, faces, 1 - target_faces / len(faces))

    m = trimesh.Trimesh(verts, faces, process=True)
    # drop small floating fragments (< 0.2% of faces)
    parts = m.split(only_watertight=False)
    if len(parts) > 1:
        keep = [p for p in parts if len(p.faces) >= 0.002 * len(m.faces)]
        if keep:
            m = trimesh.util.concatenate(keep)
    trimesh.repair.fix_normals(m, multibody=True)

    vs = float(voxel_size)
    origin = np.asarray(origin, np.float32)
    coords = np.asarray(coords)
    pts = coords.astype(np.float32) * vs + origin + vs * 0.5
    attrs = np.asarray(attrs, np.float32)
    rough = float(np.clip(np.median(attrs[:, 4]), 0.05, 1.0)) if attrs.shape[1] > 4 else 0.8

    # The decoder's triangle winding is inconsistent, so some faces point
    # inward and smooth-shade as dark blotches/cracks. Orient every face
    # against the object's actual outside: rasterise the voxel shell,
    # flood-fill the air around it, and flip any face whose front side
    # lands inside the object while its back side is out in the air.
    R = int(round(1.0 / vs)) + 8
    occ = np.zeros((R, R, R), bool)
    ci = coords.astype(np.int64) + 4
    occ[ci[:, 0], ci[:, 1], ci[:, 2]] = True
    occ = ndimage.binary_dilation(occ, iterations=2)
    lab, _ = ndimage.label(~occ)
    air = lab == lab[0, 0, 0]
    del lab, occ

    def is_air(p):
        g = np.floor((p - origin) / vs).astype(np.int64) + 4
        g = np.clip(g, 0, R - 1)
        return air[g[:, 0], g[:, 1], g[:, 2]]

    cen, nor = m.triangles_center, m.face_normals
    step = 4 * vs
    front_air, back_air = is_air(cen + nor * step), is_air(cen - nor * step)
    flip = back_air & ~front_air
    if flip.any():
        f = m.faces.copy()
        f[flip] = f[flip][:, ::-1]
        m = trimesh.Trimesh(m.vertices, f, process=False)
    print(f"  oriented: flipped {int(flip.sum()):,} of {len(flip):,} faces")
    verts, faces = np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.int64)

    with tempfile.TemporaryDirectory() as td:
        npz = os.path.join(td, "mesh.npz")
        np.savez(npz, verts=verts, faces=faces, points=pts,
                 point_colors=np.clip(attrs[:, :3], 0, 1),
                 target_faces=target_faces, remesh_voxel=remesh_voxel)
        here = os.path.dirname(os.path.abspath(__file__))
        r = subprocess.run([blender, "-b", "-P", os.path.join(here, "bake_blender.py"), "--",
                            npz, out_glb, str(texture_size), f"{rough:.3f}"],
                           capture_output=True, text=True)
        if r.returncode != 0 or "BAKED" not in r.stdout:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise RuntimeError("Blender bake failed")
    faces_out = [l for l in r.stdout.splitlines() if l.startswith("FACES")]
    return int(faces_out[-1].split()[1]) if faces_out else -1


if __name__ == "__main__":
    # test harness: finish.py <raw.obj> <voxels.npz> <out.glb>
    import sys, time, trimesh
    t = time.time()
    mesh = trimesh.load(sys.argv[1], process=False)
    d = np.load(sys.argv[2])
    n = finish(mesh.vertices, mesh.faces, d["coords"], d["attrs"], d["origin"], d["voxel_size"], sys.argv[3])
    print(f"finished {n} faces in {time.time() - t:.0f}s")
