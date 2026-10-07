"""Copy the bundled SKILL.md folders into an agent skills directory."""
from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path


def bundled() -> list[str]:
    root = resources.files("district_skills") / "skills"
    return sorted(p.name for p in root.iterdir() if (p / "SKILL.md").is_file())


def install(dest: str | None = None, only: list[str] | None = None) -> dict:
    target = Path(dest).expanduser() if dest else Path.home() / ".claude" / "skills"
    names = bundled()
    if only:
        unknown = [n for n in only if n not in names]
        if unknown:
            raise SystemExit(f"Unknown skill(s): {', '.join(unknown)}. Available: {', '.join(names)}")
        names = only
    root = resources.files("district_skills") / "skills"
    target.mkdir(parents=True, exist_ok=True)
    done = []
    for n in names:
        out = target / n
        if out.exists():
            shutil.rmtree(out)
        with resources.as_file(root / n) as src:
            shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
        done.append(str(out))
    return {"installed": done, "note": "Restart your agent session if it was already running."}
