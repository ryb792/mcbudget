#!/usr/bin/env python3
"""Package public Skill resources without credentials or local order snapshots."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
ROOT_FILES = (
    "README.md", "SKILL.md", "MCP_INTEGRATION.md", "CONTEST_DECLARATION.md",
    "mcp-config.example.json", "workbuddy.md", "LICENSE",
)


def main():
    files = [ROOT / name for name in ROOT_FILES]
    for folder in ("assets", "demo", "references", "docs"):
        base = ROOT / folder
        if base.exists():
            files.extend(p for p in base.rglob("*") if p.is_file()
                         and p.suffix.lower() in {".md", ".html", ".json", ".css", ".js", ".png", ".svg"})
    files.extend(p for p in (ROOT / "scripts").iterdir()
                 if p.is_file() and p.suffix in {".py", ".js"})
    output = ROOT / "dist" / "mcbudget.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, "mcbudget/" + path.relative_to(ROOT).as_posix())
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
