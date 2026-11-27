"""The non-picture, non-clip model sheets (components/model-inputs/inputs/<model>.json), checked at the door that
calls the model: voice, voice design, music, Suno, upscale, judge (3D lives in components/3d/sheet_check.py). clip_limits.py does the same for the clip models.

    raise_on_errors(voice_text("eleven-v3", line))        # a SystemExit naming every broken rule, before anything is sent
    raise_on_errors(music_request(request))
    raise_on_errors(suno_boxes(style, lyrics, title, exclude))
    raise_on_errors(upscale("real-esrgan", clip, scale=3))
    raise_on_errors(judge_files("gemini-3.1-pro-preview", [take, picture]))

Every number is read from the sheet; none is typed here. A finding is {id, level: "error"|"warn", say}; an error stops the
door, a warning is shown and the call goes on. No network, no spend. Python 3.9.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
_CL = []


def _clip_limits():
    if not _CL:
        sp = importlib.util.spec_from_file_location("sheet_gates_clip_limits", HERE / "clip_limits.py")
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _CL.append(m)
    return _CL[0]


def limits(model):
    return _clip_limits().limits(model)


def raise_on_errors(findings, who=""):
    return _clip_limits().raise_on_errors(findings, who)


class _F(list):
    def add(self, id_, level, say):
        self.append({"id": id_, "level": level, "say": say})


def _ext(p):
    return Path(str(p)).suffix.lower().lstrip(".")


# ------------------------------------------------------------------ voice (eleven-v3, eleven-ttv-v3)

def voice_text(model, text):
    L, out = limits(model), _F()
    n = len((text or "").strip())
    if not n:
        out.add("empty-text", "error", f"nothing to say: {model} needs the words of the line.")
    if n > L.get("max_prompt_chars", 10 ** 9):
        out.add("text-too-long", "error", f"the line is {n} characters; {model} takes at most {L['max_prompt_chars']} (one read per line, never the whole piece).")
    elif n and L.get("min_prompt_chars_advised") and n < L["min_prompt_chars_advised"]:
        out.add("text-short", "warn", f"the line is {n} characters; under {L['min_prompt_chars_advised']} can come out inconsistent.")
    return out


def voice_design(model, description, text=None, auto_text=False, guidance_scale=None, loudness=None):
    L, out = limits(model), _F()
    if not (description or "").strip():
        out.add("voice-description", "error", f"{model} needs the voice described in words.")
    lo, hi = L.get("text_chars", [0, 10 ** 9])
    if not auto_text and not lo <= len((text or "").strip()) <= hi:
        out.add("text-chars", "error", f"the sample text is {len((text or '').strip())} characters; {model} takes {lo} to {hi} (or auto-generate).")
    if loudness is not None and not -1 <= float(loudness) <= 1:
        out.add("loudness", "error", f"loudness {loudness} is outside -1 to 1.")
    return out


# ------------------------------------------------------------------ music (eleven-music-v2.5)

def music_request(request, model="eleven-music-v2.5"):
    L, out = limits(model), _F()
    chunks = ((request.get("body") or {}).get("composition_plan") or {}).get("chunks") or []
    if not chunks:
        out.add("no-sections", "error", "the music request has no sections.")
    if len(chunks) > L["sections_max"]:
        out.add("sections-max", "error", f"{len(chunks)} sections is more than {model} takes ({L['sections_max']}).")
    slo, shi = L["section_seconds"]
    total = 0
    for i, c in enumerate(chunks, 1):
        s = c.get("duration_ms", 0) / 1000
        total += c.get("duration_ms", 0)
        if not slo <= s <= shi:
            out.add("section-seconds", "error", f"section {i} is {s:g} s; {model} takes {slo} to {shi} s a section.")
        if len(c.get("positive_styles") or []) > L["styles_per_section_max"]:
            out.add("styles-max", "error", f"section {i} has more than {L['styles_per_section_max']} styles.")
        if len(c.get("negative_styles") or []) > L["negative_styles_per_section_max"]:
            out.add("negative-styles-max", "error", f"section {i} has more than {L['negative_styles_per_section_max']} excluded styles.")
        lines = [x for x in (c.get("text") or "").split("\n") if x.strip()]
        if len(lines) > L["lines_max_house"]:
            out.add("lines-max", "error", f"section {i} has {len(lines)} lines; the house limit is {L['lines_max_house']}.")
        if any(len(x) > L["chars_per_line_max_house"] for x in lines):
            out.add("line-chars", "error", f"section {i} has a line over {L['chars_per_line_max_house']} characters.")
    mlo, mhi = L["music_length_ms"]
    if chunks and not mlo <= total <= mhi:
        out.add("music-length", "error", f"the song runs {total / 1000:g} s; {model} makes {mlo / 1000:g} to {mhi / 1000:g} s.")
    want = (L.get("house") or {}).get("context_adherence")
    for i, c in enumerate(chunks, 1):
        if want and c.get("context_adherence") not in (None, want):
            out.add("context-adherence", "warn", f"section {i} is {c.get('context_adherence')!r}; the house sets {want!r}.")
    return out


# ------------------------------------------------------------------ Suno (by hand: the boxes the chain writes)

def suno_boxes(style, lyrics, title="", exclude="", model="suno"):
    L, out = limits(model), _F()
    if not (style or "").strip():
        out.add("style-empty", "error", "the Suno style box is empty.")
    if not (lyrics or "").strip():
        out.add("lyrics-empty", "error", "the Suno lyrics box is empty (never empty).")
    if len(style or "") > 1000:
        out.add("style-chars", "error", f"the style box is {len(style)} characters; Suno cuts silently past about 1,000.")
    if len(lyrics or "") > 2500:
        out.add("lyrics-chars", "error", f"the lyrics box is {len(lyrics)} characters; stay at or under 2,500.")
    if len(title or "") > 100:
        out.add("title-chars", "error", f"the title is {len(title)} characters; about 100 at most.")
    tags = [t for t in (style or "").split(",") if t.strip()]
    if len(tags) > 20:
        out.add("style-descriptors", "warn", f"{len(tags)} style descriptors; about 20 is the maximum, 4 to 7 the sweet spot.")
    ex = [t for t in (exclude or "").split(",") if t.strip()]
    if len(ex) > 3:
        out.add("exclusions", "warn", f"{len(ex)} excluded styles; 2 to 3 is reliable.")
    return out


def suno_sliders(sliders):
    out = _F()
    for k, v in (sliders or {}).items():
        try:
            ok = 0 <= float(v) <= 100
        except (TypeError, ValueError):
            ok = False
        if not ok:
            out.add("slider", "error", f"slider {k} = {v!r} is not 0 to 100.")
    return out


# ------------------------------------------------------------------ upscale (real-esrgan, bytedance-upscaler-video)

def upscale(model, clip, scale=None, target=None, input_res=None, fps=None):
    L, out = limits(model), _F()
    p = Path(str(clip))
    if not p.is_file() or p.stat().st_size == 0:
        out.add("input-missing", "error", f"the clip to upscale is missing or empty: {p.name}.")
    if model == "real-esrgan":
        ok = list(L.get("formats") or []) + ["mp4", "mov", "m4v", "webm"]
        if _ext(p) not in ok:
            out.add("input-format", "error", f"{p.name} is .{_ext(p)}; {model} takes frames ({', '.join(L.get('formats') or [])}) or a video.")
        if scale is not None and not 1 <= float(scale) <= 8:
            out.add("scale", "error", f"scale {scale} is not a sane factor for a x{L['native_scale']} model (1 to 8).")
    else:
        if _ext(p) not in L["formats"]:
            out.add("input-format", "error", f"{p.name} is .{_ext(p)}; {model} takes {', '.join(L['formats'])}.")
        if target is not None and target not in L["target_resolutions"]:
            out.add("target-resolution", "error", f"target {target!r} is not one of {', '.join(L['target_resolutions'])} (8K is claimed by one page only; 4K is the safe ceiling).")
        if input_res is not None and input_res not in L["input_resolutions"]:
            out.add("input-resolution", "error", f"input {input_res!r} is not one of {', '.join(L['input_resolutions'])}.")
        if fps is not None and float(fps) > L["frame_rate_max"]:
            out.add("frame-rate", "error", f"{fps} fps is over {L['frame_rate_max']}.")
    return out


# ------------------------------------------------------------------ judge (gemini-3.1-pro-preview)

def judge_files(model, files):
    L, out = limits(model), _F()
    files = [Path(str(f)) for f in files if f]
    videos = [f for f in files if _ext(f) in L["formats"]]
    if len(videos) > L["videos_per_request"]:
        out.add("videos-max", "error", f"{len(videos)} videos in one request; {model} takes {L['videos_per_request']}.")
    total = sum(f.stat().st_size for f in files if f.is_file())
    if total > L["request_total_mb_inline"] * 1024 * 1024:
        out.add("inline-size", "error", f"the files total {total / 1048576:.1f} MB inline; over {L['request_total_mb_inline']} MB the request must go through the File API.")
    return out
