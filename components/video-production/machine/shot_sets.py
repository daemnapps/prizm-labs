"""SHOT SETS — every shot gets its room built, lit and printed in 3D before a picture is made (owner, 2026-10-28).

owner: "you need to set up 3D cameras and stand-ins for each shot ... the next runs we do are just consistent ... it just
becomes a function of input and output. Not subjectivity, not questionability."

A shot set is what makes a person look like she is really standing in the room (the research behind it:
components/image-production/research/movie-level-depth.md). Per place and per swipe camera, ONE set:

    casting/<person>/worlds/rooms-3d/<room>/sets/<camera key>/
        plate.jpg      the empty room, printed from its 3D model at the swipe's camera, its built light kept
        standin.png    the same room with a grey stand-in on her mark — where her light and shadows fall
        light.json     that light as facts (frame-left / frame-right, never "her left")
        set.json       the camera, the stand-in mark, the lights, the 3D project and revision, the print request

and every shot of the run that uses that swipe camera points at it:

    casting/<person>/worlds/rooms-3d/<room>/shots/<shot>/  →  plate.jpg, standin.png, light.json (copies of its set)

so shots that share a camera share one room and one light: identical, shot to shot. video-production `shot_swaps.py`
reads shots/<shot>/ (the room picture, the light guide, THE LIGHT ON HER); image production does the rest.

The camera key comes from the swipe's frame map (`map.camera`: height · distance · held · move). The 3D build itself runs
through Higgsfield 3D Jutsu (the session's scene_builder_3d tools: run the `bpy` this prints, render, print with
generate_angles, then `put`). The camera presets are the ones proven on the Yai cheek run, 2026-10-28.

    python3 shot_sets.py plan <production run>                 which sets the run needs, which exist, which shots share
    python3 shot_sets.py bpy <production run> <camera key>      the scene code for that set (camera, stand-in, light, haze)
    python3 shot_sets.py prompt <production run> <camera key>   the print prompt for that set
    python3 shot_sets.py put <production run> <camera key> --plate F --standin F [--light light.json]
    python3 shot_sets.py link <production run>                  point every shot at its set (shots/<shot>/)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]

# the swipe camera → our 3D camera (metres, degrees). A person ~1.45 m standing ~1.5 m from the lens, a counter between.
CAMERAS = {
    "eye level·medium": {"loc": [0, -0.05, 1.3], "pitch": 80.5, "lens": 40, "focus": 1.5, "fstop": 1.8},
    "eye level·close":  {"loc": [0, 0.45, 1.32], "pitch": 84.0, "lens": 50, "focus": 1.0, "fstop": 1.8},
    "eye level·wide":   {"loc": [0, -1.05, 1.38], "pitch": 86.5, "lens": 30, "focus": 2.45, "fstop": 2.2},
    # a phone held over the table looking down at hands (2026-11-02): never fall back to an eye-level camera for these
    "above·close":      {"loc": [0, 1.05, 1.42], "pitch": 0.0, "lens": 26, "focus": 0.52, "fstop": 2.8},
    "above·medium":     {"loc": [0, 0.55, 1.75], "pitch": 30.0, "lens": 26, "focus": 1.1, "fstop": 2.8},
}
LIGHT = {
    "key": "warm window daylight from the LEFT of the frame, soft and directional, lighting the frame-left side of her face, "
           "shoulder and arm, the same light that pours through the window and haze in the room picture",
    "shadow side": "the frame-right side of her face and body falls into soft shadow, darker than her lit side, as dark as the room on that side",
    "rim": "a faint warm edge of window light on the frame-left edge of her hair and shoulder",
    "bounce": "warm low bounce from the counter under her chin and hands",
    "contact": "soft contact shadows where her fingers meet what she holds and where her forearms meet her body; her shadow falls toward the frame right",
    "exposure": "no brighter and no sharper than the counter and the room beside her; the same grain",
}


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_ss_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    spec.loader.exec_module(mod)
    return mod


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def camera_key(cam: dict) -> str:
    h = str(cam.get("height") or "eye level").lower()
    d = str(cam.get("distance") or "medium").lower()
    d = "close" if "close" in d else "wide" if ("wide" in d or "long" in d or "full" in d) else "medium"
    h = "eye level" if "eye" in h or not h else h
    return f"{h}·{d}"


def plan(run: Path) -> dict:
    """{camera key: {shots, place, person, room, set_dir, exists}} for the run's shots."""
    run = Path(run)
    sb = json.loads((run / "storyboard.json").read_text())
    SS = _load("shot_swaps")
    out = {}
    for g in sb.get("sections") or []:
        ks = (g.get("swipe") or {}).get("shots") or []
        if not ks:
            continue
        p = SS.brief_parts(run, g["id"])
        if not p["people"] or not p["places"]:
            continue
        cam = ((ks[0].get("camera")) or {})
        key = camera_key(cam)
        who, pl = p["people"][0], p["places"][0]
        room = WS / "runs" / "ai-elements" / p["brand"] / "casting" / who["bank"] / "worlds" / "rooms-3d" / pl["bank"]
        # a room built inside a 3D world names its own sets in room.json (`sets`: {name: {camera, shots}}); a shot it does not
        # list keeps the picture it has, so one camera height never drags a second place's shots onto one set
        named = (json.loads((room / "room.json").read_text()).get("sets") or {}) if (room / "room.json").is_file() else {}
        if named:
            key = next((n for n, x in named.items() if g["id"] in (x.get("shots") or [])), None)
            if not key:
                continue
        sd = room / "sets" / _slug(key)
        e = out.setdefault(key, {"shots": [], "person": who["bank"], "place": pl["bank"], "room": str(room),
                                 "set_dir": str(sd), "exists": (sd / "plate.jpg").is_file(),
                                 "project": (json.loads((room / "room.json").read_text()).get("scene") or {}).get("project_id")
                                 if (room / "room.json").is_file() else None})
        e["shots"].append(g["id"])
    return out


def bpy_code(key: str) -> str:
    c = CAMERAS.get(key)
    if not c:
        raise SystemExit(f"no 3D camera for '{key}': add it to CAMERAS, a shot never borrows another camera's set")
    return f'''import bpy, math
s=bpy.context.scene
cam=bpy.data.objects.get("CAM_swipe")
if cam is None:
    cd=bpy.data.cameras.new("CAM_swipe"); cam=bpy.data.objects.new("CAM_swipe",cd); s.collection.objects.link(cam)
cam.location={tuple(c["loc"])}; cam.rotation_euler=(math.radians({c["pitch"]}),0,0); cam.data.lens={c["lens"]}; cam.data.sensor_width=36
cam.data.dof.use_dof=True; cam.data.dof.focus_distance={c["focus"]}; cam.data.dof.aperture_fstop={c["fstop"]}; s.camera=cam
def mat(n,col,r=0.5):
    m=bpy.data.materials.get(n) or bpy.data.materials.new(n); m.use_nodes=True
    b=m.node_tree.nodes.get("Principled BSDF"); b.inputs["Base Color"].default_value=(*col,1); b.inputs["Roughness"].default_value=r; return m
if "HERO_counter" not in bpy.data.objects:
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,1.05,0.45)); o=bpy.context.active_object; o.name="HERO_counter"; o.scale=(2.4,0.75,0.9)
    o.data.materials.append(mat("MAT_counter_teak",(0.23,0.13,0.07),0.55))
if "STANDIN_body" not in bpy.data.objects:
    g=mat("MAT_standin_grey",(0.5,0.5,0.5),0.7)
    for n,f,a,l in (("STANDIN_body",bpy.ops.mesh.primitive_cylinder_add,dict(radius=0.19,depth=1.18),(0.05,1.45,0.59)),
                    ("STANDIN_head",bpy.ops.mesh.primitive_uv_sphere_add,dict(radius=0.11),(0.05,1.42,1.33))):
        f(location=l,**a); o=bpy.context.active_object; o.name=n; o.data.materials.append(g)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0.05,1.45,1.13)); o=bpy.context.active_object; o.name="STANDIN_shoulders"; o.scale=(0.42,0.2,0.12); o.data.materials.append(g)
for n in ("LGT_key","LGT_fill"):
    if n in bpy.data.objects: bpy.data.objects[n].data.energy=0.6 if n=="LGT_key" else 0.25
if "LGT_window" not in bpy.data.objects:
    w=bpy.data.lights.new("LGT_window","SPOT"); w.energy=900; w.color=(1.0,0.86,0.66); w.spot_size=math.radians(55); w.spot_blend=0.6; w.shadow_soft_size=0.6
    o=bpy.data.objects.new("LGT_window",w); s.collection.objects.link(o)
wo=bpy.data.objects["LGT_window"]; wo.location=(-1.9,1.0,1.9)
wo.rotation_euler=(bpy.data.objects["STANDIN_head"].location-wo.location).to_track_quat('-Z','Y').to_euler()
if "LGT_rim" not in bpy.data.objects:
    r=bpy.data.lights.new("LGT_rim","POINT"); r.energy=140; r.color=(1.0,0.75,0.45); r.shadow_soft_size=0.3
    o=bpy.data.objects.new("LGT_rim",r); s.collection.objects.link(o); o.location=(0.6,2.7,1.8)
wd=s.world; wd.use_nodes=True; nt=wd.node_tree
v=nt.nodes.get("HAZE") or nt.nodes.new("ShaderNodeVolumePrincipled"); v.name="HAZE"; v.inputs["Density"].default_value=0.035
nt.links.new(v.outputs[0],[n for n in nt.nodes if n.type=='OUTPUT_WORLD'][0].inputs["Volume"])
s.render.engine='BLENDER_EEVEE'; s.render.resolution_x=720; s.render.resolution_y=1280; s.render.resolution_percentage=60
pubs=[]
for name,show in (("plate.png",False),("standin.png",True)):
    for o in ("STANDIN_body","STANDIN_shoulders","STANDIN_head"): bpy.data.objects[o].hide_render=not show
    t=artifacts.file(name=name,media_type="image/png"); s.render.filepath=str(t.path)
    s.render.image_settings.media_type="IMAGE"; s.render.image_settings.file_format="PNG"
    bpy.ops.render.render(write_still=True); t.publish(); pubs.append(name)
for o in ("STANDIN_body","STANDIN_shoulders","STANDIN_head"): bpy.data.objects[o].hide_render=True
result={{"renders":pubs,"camera":"{key}"}}'''


def print_prompt(run: Path, key: str) -> str:
    e = plan(run).get(key) or {}
    rj = {}
    rf = Path(e.get("room", "")) / "room.json"
    if rf.is_file():
        rj = json.loads(rf.read_text())
    what = (rj.get("real_reference") or {}).get("what") or "the room in the reference photo"
    amp = rj.get("amplified_with") or ""
    if (rj.get("sets") or {}).get(key):          # a room in a 3D world: its own light and furniture, the render owns them
        return ("A real, unretouched phone photograph of this exact space from this exact camera: keep the render's layout, framing, "
                f"perspective, focus, furniture and its light exactly. It is {what}. Light ceilings, true colours, natural grain. "
                "Every grey block is what the room shows, in its real material. The barber chair is empty and the room has "
                "no one in it. No added lights, no CGI sheen. No people, no hands, no text, no logos.")
    if key.startswith("above"):                  # looking down: the table is the picture, nobody stands in it
        return ("A real, unretouched phone photograph looking down from this exact camera: keep the render's framing, perspective, "
                f"focus and its light exactly, warm window light from the left. Dress it as the reference photo: {what}. The table "
                "top fills the frame in its real worn dark wood, empty and clear for hands and objects. No added lights, no CGI "
                "sheen. True colours, natural grain. No people, no hands, no text, no logos.")
    return ("A real, unretouched phone photograph of this exact space from this exact camera: keep the render's layout, framing, "
            "perspective, focus and its light exactly — the warm window light coming from the left, the far right side falling "
            f"into shadow, the haze in the air, the back of the room soft and out of focus. Dress it as the reference photo: {what}"
            + (f"; {amp}" if amp else "") + ". In the foreground: the counter across the bottom of the frame, empty. The space "
            "behind the counter is empty, ready for a person to stand there. No added lights, no relighting, no CGI sheen. "
            "True colours, natural grain. No people, no text, no logos.")


def put(run: Path, key: str, plate: Path, standin: Path, light: Path | None = None, meta: dict | None = None) -> Path:
    e = plan(run)[key]
    sd = Path(e["set_dir"]); sd.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.open(plate).convert("RGB").save(sd / "plate.jpg", quality=92)
    shutil.copy(standin, sd / "standin.png")
    (sd / "light.json").write_text(Path(light).read_text() if light else json.dumps(LIGHT, indent=1))
    (sd / "set.json").write_text(json.dumps({"camera_key": key, "camera": CAMERAS.get(key), "shots": e["shots"],
                                             "project": e.get("project"), **(meta or {})}, indent=1))
    return sd


def link(run: Path) -> list:
    done = []
    for key, e in plan(run).items():
        sd = Path(e["set_dir"])
        if not (sd / "plate.jpg").is_file():
            continue
        for gid in e["shots"]:
            d = Path(e["room"]) / "shots" / gid
            d.mkdir(parents=True, exist_ok=True)
            for f in ("plate.jpg", "standin.png", "light.json"):
                if (sd / f).is_file():
                    shutil.copy(sd / f, d / f)
            (d / "set.txt").write_text(f"from sets/{sd.name}\n")
            done.append(gid)
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("plan", "link"):
        sub.add_parser(c).add_argument("run")
    for c in ("bpy", "prompt"):
        p = sub.add_parser(c); p.add_argument("run"); p.add_argument("key")
    p = sub.add_parser("put"); p.add_argument("run"); p.add_argument("key")
    p.add_argument("--plate", required=True); p.add_argument("--standin", required=True); p.add_argument("--light")
    a = ap.parse_args(argv)
    run = Path(a.run)
    if a.cmd == "plan":
        print(json.dumps(plan(run), indent=1, ensure_ascii=False))
    elif a.cmd == "bpy":
        print(bpy_code(a.key))
    elif a.cmd == "prompt":
        print(print_prompt(run, a.key))
    elif a.cmd == "put":
        print(put(run, a.key, Path(a.plate), Path(a.standin), Path(a.light) if a.light else None))
    elif a.cmd == "link":
        print(json.dumps(link(run)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
