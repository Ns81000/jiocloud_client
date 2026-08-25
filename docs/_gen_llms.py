"""MkDocs build hook: copy llms.txt / llms-full.txt from the repo root into
the generated site so agents can fetch them at the Pages root.

Runs via the mkdocs-gen-files plugin during every docs build (local and CI).
"""
from pathlib import Path

import mkdocs_gen_files

ROOT = Path(__file__).resolve().parent.parent  # repo root (docs/..)

for name in ("llms.txt", "llms-full.txt"):
    src = ROOT / name
    if not src.exists():
        raise FileNotFoundError(f"{src} missing - it must live at the repo root")
    with mkdocs_gen_files.open(name, "w", encoding="utf-8") as dst:
        dst.write(src.read_text(encoding="utf-8"))
print("[gen_llms] copied llms.txt and llms-full.txt into site output")
