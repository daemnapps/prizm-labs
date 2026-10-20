"""The files that leave the machine: the full-size phone copy (1080x1920, 24 fps, H.264 high ~8.2 Mbps, AAC 192k,
faststart, under 30 MB — the person posts straight from their phone, so never send a preview) and a 540x960 page copy.
Usage: deliver.py CUT.mp4 "<name>" [--copy-to DIR] [--page-copy PATH]"""
import argparse, os, shutil, subprocess
ap = argparse.ArgumentParser(); ap.add_argument("cut"); ap.add_argument("name"); ap.add_argument("--copy-to"); ap.add_argument("--page-copy")
A = ap.parse_args()
def ff(*a): subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)
phone = f"{A.name} 1080x1920.mp4"
ff("-i", A.cut, "-c:v", "libx264", "-profile:v", "high", "-b:v", "8200k", "-maxrate", "9000k", "-bufsize", "16000k",
   "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", phone)
mb = os.path.getsize(phone) / 1e6; print(f"{phone}: {mb:.1f} MB" + ("  ** over 30 MB: lower -b:v **" if mb > 30 else ""))
if A.copy_to: shutil.copy(phone, os.path.expanduser(A.copy_to))
if A.page_copy:
    ff("-i", A.cut, "-vf", "scale=540:960", "-c:v", "libx264", "-crf", "24", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", A.page_copy)
