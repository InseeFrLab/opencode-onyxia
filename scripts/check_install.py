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
import tarfile
import tempfile
import time
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


def clean_tree(path: Path) -> list[str]:
    """tree() without local bytecode caches, which a repo checkout may hold but a release never ships."""
    return [p for p in tree(path) if "__pycache__" not in p]


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

        # 6. release tarball: only the MANIFEST paths, installs like the repo ---------------------------------
        dist = work / "dist"
        r = subprocess.run(
            ["bash", str(REPO / "scripts" / "build_dist.sh"), "v0.0.0-test", str(dist)],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        check("build_dist.sh succeeds", r.returncode == 0, r.stderr.strip()[-200:])
        manifest = [
            ln.strip() for ln in (REPO / "MANIFEST").read_text().splitlines() if ln.strip() and not ln.startswith("#")
        ]
        tracked = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "--", *manifest],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        with tarfile.open(dist / "opencode-onyxia.tar.gz") as tf:
            names = sorted(m.name.split("/", 1)[1] for m in tf.getmembers() if m.isfile())
            src = work / "dist-src"
            tf.extractall(src, filter="data")
        check(
            "tarball holds exactly the tracked MANIFEST files + VERSION",
            names == sorted([*tracked, "VERSION"]),
            str(sorted(set(names) ^ {*tracked, "VERSION"}))[:200],
        )
        check(
            "tarball ships no dev scripts",
            not any(n.startswith("scripts/") for n in names),
        )
        src = next(src.iterdir())
        check(
            "VERSION file holds the version",
            (src / "VERSION").read_text().strip() == "v0.0.0-test",
        )
        for args, label in (((), "full"), (("--bare",), "bare")):
            d_repo, d_dist, h = (
                work / f"cmp-{label}-repo",
                work / f"cmp-{label}-dist",
                work / f"cmp-{label}-home",
            )
            h.mkdir()
            install(REPO, d_repo, h, *args)
            install(src, d_dist, h, *args)
            check(
                f"{label} install from the tarball == from the repo",
                clean_tree(d_repo) == tree(d_dist) and tree(d_dist) != [],
                str(sorted(set(clean_tree(d_repo)) ^ set(tree(d_dist))))[:200],
            )
        r2 = subprocess.run(
            [
                "bash",
                str(REPO / "scripts" / "build_dist.sh"),
                "v0.0.0-test",
                str(work / "dist2"),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        check(
            "the build is reproducible (same sha256 twice)",
            r2.returncode == 0
            and (dist / "opencode-onyxia.tar.gz.sha256").read_text()
            == (work / "dist2" / "opencode-onyxia.tar.gz.sha256").read_text(),
        )

        # 7. onyxia-init.sh: installs from a release, refuses a bad checksum, never fails the service ---------
        def init(base: Path, home: Path, dest: Path, *args: str) -> subprocess.CompletedProcess:
            env = {
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "HOME": str(home),
                "OPENCODE_CONFIG_DIR": str(dest),
                "OPENCODE_ONYXIA_URL": base.as_uri(),
                "OPENCODE_ONYXIA_SKIP_OPENCODE": "1",
            }
            home.mkdir(parents=True, exist_ok=True)
            return subprocess.run(
                ["bash", "-s", "--", *args],
                input=(REPO / "onyxia-init.sh").read_text(),
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )

        dest, home = work / "init" / "cfg", work / "init" / "home"
        r = init(dist, home, dest)
        check(
            "init script (piped like Onyxia) installs the full config",
            r.returncode == 0 and tree(dest) == clean_tree(work / "cmp-full-repo"),
            (r.stdout + r.stderr)[-300:],
        )
        check(
            "init script logs to ~/.cache",
            (home / ".cache" / "opencode-onyxia-init.log").exists(),
        )
        dest = work / "init-bare" / "cfg"
        r = init(dist, work / "init-bare" / "home", dest, "--version", "v9", "--bare")
        check(
            "init script passes --bare to install.sh",
            tree(dest) == ["opencode.jsonc"],
            str(tree(dest)),
        )
        bad = work / "bad"
        shutil.copytree(dist, bad)
        (bad / "opencode-onyxia.tar.gz.sha256").write_text(f"{'0' * 64}  opencode-onyxia.tar.gz\n")
        dest = work / "init-bad" / "cfg"
        r = init(bad, work / "init-bad" / "home", dest)
        check(
            "bad checksum: nothing installed, exit 0, error reported",
            r.returncode == 0 and not dest.exists() and "checksum mismatch" in r.stdout + r.stderr,
            f"rc={r.returncode} {tree(dest)}",
        )
        r = init(work / "missing", work / "init-404" / "home", work / "init-404" / "cfg")
        check(
            "unreachable release: exit 0, error reported",
            r.returncode == 0 and "download failed" in r.stdout + r.stderr,
            (r.stdout + r.stderr)[-200:],
        )

        # 8. the bare config loads in a real opencode service -------------------------------------------------
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
                # The first request for a directory starts a fresh opencode instance, which (seen with v2.4.2)
                # can answer /api/model before the config-defined `onyxia` provider is registered: poll.
                want_models = set(full_cfg["providers"]["onyxia"]["models"])
                deadline = time.monotonic() + 30
                while True:
                    models = {m["id"] for m in sb.get_data("/api/model") if m.get("providerID") == "onyxia"}
                    if models == want_models or time.monotonic() > deadline:
                        break
                    time.sleep(0.5)
                check("the 3 onyxia models are available", models == want_models, str(sorted(models)))
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
