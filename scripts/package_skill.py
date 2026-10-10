#!/usr/bin/env python3
"""Package the real MCP Skill using an explicit runtime-resource allowlist."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SKILL_FILES = (
    "SKILL.md", "MCP_INTEGRATION.md", "CONTEST_DECLARATION.md", "LICENSE",
    "mcp-config.example.json", "mcp-config.codex.example.toml",
    "docs/GETTING_STARTED.md", "references/mcp_tools.md", "references/data_conventions.md",
    "scripts/budget_engine.py", "scripts/check_mcp.py", "scripts/real_smoke.py",
    "scripts/make_qr.py", "scripts/render_card.py", "assets/result_template.html",
)


def main():
    files = [ROOT / name for name in SKILL_FILES]
    missing = [path.relative_to(ROOT).as_posix() for path in files if not path.is_file()]
    if missing:
        raise SystemExit("Skill resources missing: " + ", ".join(missing))
    output = ROOT / "dist" / "mcbudget.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "mcbudget/" + path.relative_to(ROOT).as_posix())
    print(f"{output} ({len(files)} runtime resources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
