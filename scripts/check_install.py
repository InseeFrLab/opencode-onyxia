#!/usr/bin/env python3
"""Check what `install.sh` (full) and `install.sh --bare` write, without touching the real ~/.config/opencode.

    python3 -I scripts/check_install.py

Every case runs `install.sh` with OPENCODE_CONFIG_DIR and HOME pointing at throw-away directories. The last case
loads the bare config in a private opencode service (isolated HOME/port, via the Sandbox of check_permissions.py) and
is skipped when `opencode` is not installed. Exit code 1 on any failure.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CUSTOM_AGENTS = {"python-ds", "r-ds", "mlops", "reviewer", "dataviz-vision"}


def load_jsonc(text: str) -> dict:
    """Parse JSONC (comments and trailing commas), string-aware."""
    out, i, in_str = [], 0, False
    while i < len(text):
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\":
                out.append(text[i + 1])
                i += 1
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        else:
            out.append(ch)
        i += 1
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", "".join(out)))


def install(src: Path, dest: Path, home: Path, *args: str) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(home), "OPENCODE_CONFIG_DIR": str(dest)}
    return subprocess.run(
        ["bash", str(src / "install.sh"), *args], env=env, capture_output=True, text=True, check=False, timeout=120
    )


def tree(path: Path) -> list[str]:
    return sorted(str(p.relative_to(path)) for p in path.rglob("*")) if path.exists() else []


results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not ok else ""), flush=True)


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="opencode-install-"))
    try:
        full_cfg = load_jsonc((REPO / "opencode.jsonc").read_text())

        # 1. full install ----------------------------------------------------------------------------------------
        dest, home = work / "full" / "cfg", work / "full" / "home"
        home.mkdir(parents=True)
        r = install(REPO, dest, home)
        have = {p.name for p in dest.iterdir()} if dest.exists() else set()
        want = {"opencode.jsonc", "AGENTS.md", "prompts", "skills", "commands"}
        check(
            "full install writes config, AGENTS.md, prompts, skills, commands",
            r.returncode == 0 and want <= have,
            str(have),
        )

        # 2. bare install: only the models ---------------------------------------------------------------------
        dest, home = work / "bare" / "cfg", work / "bare" / "home"
        home.mkdir(parents=True)
        r = install(REPO, dest, home, "--bare")
        check("bare install succeeds", r.returncode == 0, r.stderr.strip()[-200:])
        check(
            "bare writes ONLY opencode.jsonc (no temp files, skills, prompts, commands, AGENTS.md)",
            tree(dest) == ["opencode.jsonc"],
            str(tree(dest)),
        )
        bare = load_jsonc((dest / "opencode.jsonc").read_text())
        check(
            "bare top-level keys are $schema, providers, model, agents",
            set(bare) == {"$schema", "providers", "model", "agents"},
            str(sorted(bare)),
        )
        check(
            "bare agents contain only the title model",
            set(bare.get("agents", {})) == {"title"},
            str(bare.get("agents")),
        )
        check(
            "bare has no permissions, policies, mcp or default_agent",
            not ({"permissions", "policies", "mcp", "default_agent", "update"} & set(bare)),
        )
        check("bare providers == full providers (drift guard)", bare.get("providers") == full_cfg["providers"])
        check("bare model == full model", bare.get("model") == full_cfg["model"])
        check("bare title model == full title model", bare["agents"]["title"] == full_cfg["agents"]["title"])
        check(
            "bare does not call itself a v1-compatible file",
            "not readable by opencode v1" in (dest / "opencode.jsonc").read_text(),
        )

        # 3. bare over an existing config -------------------------------------------------------------------
        dest, home = work / "over" / "cfg", work / "over" / "home"
        (dest / "skills" / "mine").mkdir(parents=True)
        home.mkdir(parents=True)
        (dest / "opencode.jsonc").write_text("// my own config\n{}\n")
        (dest / "AGENTS.md").write_text("my agents file\n")
        (dest / "skills" / "mine" / "SKILL.md").write_text("my skill\n")
        r = install(REPO, dest, home, "--bare")
        backups = sorted(dest.glob("backup-*"))
        check(
            "bare over an existing config backs it up",
            len(backups) == 1 and (backups[0] / "opencode.jsonc").read_text() == "// my own config\n{}\n",
            str(tree(dest)),
        )
        check(
            "bare leaves AGENTS.md and skills untouched",
            (dest / "AGENTS.md").read_text() == "my agents file\n"
            and (dest / "skills" / "mine" / "SKILL.md").read_text() == "my skill\n",
        )
        check("bare does not back up AGENTS.md (not touched)", not (backups and (backups[0] / "AGENTS.md").exists()))
        check(
            "bare prints a note about the files it left in place",
            "left untouched" in r.stdout and "AGENTS.md" in r.stdout,
            r.stdout[-300:],
        )
        check("the replaced config is the bare one", "providers" in load_jsonc((dest / "opencode.jsonc").read_text()))

        # 4. --bare --claude is refused --------------------------------------------------------------------
        dest, home = work / "claude" / "cfg", work / "claude" / "home"
        home.mkdir(parents=True)
        r = install(REPO, dest, home, "--bare", "--claude")
        check(
            "--bare --claude exits 2 and writes nothing",
            r.returncode == 2 and not dest.exists() and not (home / ".claude").exists(),
            f"rc={r.returncode} {tree(home)}",
        )

        # 5. missing markers: fail loudly, existing config untouched ----------------------------------------
        src = work / "nomarkers"
        src.mkdir()
        shutil.copy(REPO / "install.sh", src / "install.sh")
        stripped = re.sub(
            r"^.*(>>>|<<<) bare(-title)?:(begin|end).*\n", "", (REPO / "opencode.jsonc").read_text(), flags=re.MULTILINE
        )
        (src / "opencode.jsonc").write_text(stripped)
        dest, home = work / "nomarkers-dest" / "cfg", work / "nomarkers-dest" / "home"
        dest.mkdir(parents=True)
        home.mkdir(parents=True)
        (dest / "opencode.jsonc").write_text("// keep me\n{}\n")
        r = install(src, dest, home, "--bare")
        check(
            "without the markers the bare install fails (exit 1) and says why",
            r.returncode == 1 and "bare" in r.stderr,
            f"rc={r.returncode} {r.stderr.strip()[-160:]}",
        )
        check(
            "... and the existing config is untouched, with no backup or temp file left",
            tree(dest) == ["opencode.jsonc"] and (dest / "opencode.jsonc").read_text() == "// keep me\n{}\n",
            str(tree(dest)),
        )

        # 6. the bare config loads in a real opencode service -------------------------------------------------
        if shutil.which("opencode") is None:
            print("skip bare config loaded by opencode (opencode not on PATH)")
        else:
            spec = importlib.util.spec_from_file_location(
                "check_permissions", REPO / "scripts" / "check_permissions.py"
            )
            cp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cp)
            sb = cp.Sandbox(None, False, install_args=("--bare",), project_config=None, ready_marker='"build"')
            try:
                sb.start()
                warn = sb.run("debug", "config").stderr.strip()
                check("opencode loads the bare config without warnings", warn == "", warn[:200])
                models = {m["id"] for m in sb.get_data("/api/model") if m.get("providerID") == "onyxia"}
                check(
                    "the 3 onyxia models are available",
                    models == set(full_cfg["providers"]["onyxia"]["models"]),
                    str(sorted(models)),
                )
                agents = {a["id"]: a for a in sb.get_data("/api/agent")}
                check(
                    "none of the shipped custom agents exist",
                    not (CUSTOM_AGENTS & set(agents)),
                    str(sorted(set(agents) & CUSTOM_AGENTS)),
                )
                title = (agents.get("title") or {}).get("model") or {}
                check(
                    "the title agent uses the small model",
                    (title.get("providerID"), title.get("id")) == ("onyxia", "gemma4-26b-moe"),
                    str(title),
                )
                default = sb.get_data("/api/model/default")
                flat = json.dumps(default)
                check("the default model is onyxia/qwen3-8-27b", "qwen3-8-27b" in flat and "onyxia" in flat, flat[:200])
            finally:
                sb.stop()
    finally:
        shutil.rmtree(work, ignore_errors=True)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
