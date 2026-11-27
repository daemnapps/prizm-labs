#!/usr/bin/python3
import os, sys, pathlib  # the mini's door (LD-1 (shared lab door)): lab-run's pairs → run_kit/lab_door.py with lab_door.json beside this
sys.path.append(next(str(d / "components" / "run-kit") for d in pathlib.Path(__file__).resolve().parents if (d / "components" / "run-kit").is_dir()))
from run_kit import lab_door; sys.exit(lab_door.run(pathlib.Path(__file__).with_name("lab_door_v2.json"), sys.argv[1:], os.environ))
