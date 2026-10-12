"""Kokoro-82M on MLX (mlx-audio). Stock voices only — no cloning."""
import argparse, time, json
import numpy as np, soundfile as sf
from mlx_audio.tts.utils import load_model
ap = argparse.ArgumentParser(); ap.add_argument("text"); ap.add_argument("output")
ap.add_argument("--voice", default="am_michael"); ap.add_argument("--model", default="mlx-community/Kokoro-82M-bf16"); ap.add_argument("--speed", type=float, default=1.0)
a = ap.parse_args()
m = load_model(a.model)
t = time.time()
chunks = [np.array(r.audio) for r in m.generate(text=a.text, voice=a.voice, speed=a.speed, lang_code=a.voice[0])]
gen = time.time() - t
audio = np.concatenate(chunks)
sf.write(a.output, audio, 24000)
print(json.dumps({"audio_seconds": round(len(audio) / 24000, 2), "gen_seconds": round(gen, 2)}))
