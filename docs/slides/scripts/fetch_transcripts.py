"""Récupère (lecture seule) depuis MLflow les transcripts des cellules du benchmark et en tire des
frises abrégées et anonymisées, utilisables dans les diapositives.

    export MLFLOW_TRACKING_URI=... MLFLOW_TRACKING_USERNAME=... MLFLOW_TRACKING_PASSWORD=...
    uv run --project ../../../onyxia-agent-bench python scripts/fetch_transcripts.py OUT.json

Les identifiants ne viennent QUE de l'environnement ; rien n'est écrit sur le serveur.
Sortie : {"<modèle>|<tâche>|<config>|seed<N>": {prompt?, status, tokens, turns, events:[{turn,type,name,text}]}}
Toute chaîne ressemblant à un secret est masquée (cf. REDACT) ; relire la sortie avant usage.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parents[3].parent / "onyxia-agent-bench"
sys.path.insert(0, str(BENCH))
from bench.claude_driver import parse_claude_stream  # noqa: E402
from bench.opencode_driver import parse_output  # noqa: E402
from mlflow.tracking import MlflowClient  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
# run affiché -> (fichier summary local, noms de runs parents MLflow par _source, parseur)
SOURCES = {
    "runs/onyxia-agent-bench-5tz7m-regraded2/summary.json": ["onyxia-agent-bench-5tz7m"],
    "runs/qwen27-clean/summary.json": ["qwen27-clean"],
    "runs/opus-git-fix-regraded/summary.json": ["opus-git-fix"],
    "runs/opus-lost-cells-regraded/summary.json": ["opus-lost-cells"],
}
REDACT = [
    (re.compile(r"(AKIA|ASIA)[A-Z0-9]{12,}"), "[CLE-AWS]"),
    (re.compile(r"\b(hvs|hf|ghp|gho|sk)[-_][A-Za-z0-9_\-]{12,}"), "[JETON]"),
    (re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)(\s*[=:]\s*)['\"]?[^\s'\"]{6,}"), r"\1\2[MASQUÉ]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"user-[a-z0-9]{5,}"), "user-[ns]"),
]


def redact(s: str) -> str:
    for rx, rep in REDACT:
        s = rx.sub(rep, s)
    return s


def short(s: str, n: int) -> str:
    s = redact((s or "").strip())
    return s if len(s) <= n else s[:n].rstrip() + " […]"


def main(out: str, wanted: list[str]):
    c = MlflowClient()
    exp_ids = [e.experiment_id for e in c.search_experiments()]
    parents: dict[str, list[str]] = {}
    for src, names in SOURCES.items():
        for n in names:
            parents[src] = [r.info.run_id for r in c.search_runs(exp_ids, f"attributes.run_name = '{n}'", max_results=5)]
    result = {}
    for spec in wanted:  # "modèle|tâche|config|seedN" avec modèle = 27b | opus
        model, task, cfg, seed = spec.split("|")
        summary = json.load(open(BENCH / "runs" / ("final-27b" if model == "27b" else "final-opus") / "summary.json"))
        rec = next(r for r in summary["records"]
                   if r["task"] == task and r["config"] == cfg and f"seed{r['seed']}" == seed)
        src = rec["_source"]
        run_name = f"{task}/{cfg}/{seed}"
        kid = None
        for pid in parents.get(src, []):
            ks = c.search_runs(exp_ids, f"tags.mlflow.parentRunId = '{pid}' and attributes.run_name = '{run_name}'", max_results=2)
            if ks:
                kid = ks[0]
                break
        if kid is None:
            print("introuvable :", spec, src)
            continue
        with tempfile.TemporaryDirectory() as td:
            p = c.download_artifacts(kid.info.run_id, f"{run_name}/raw.ndjson", td)
            raw = Path(p).read_text(encoding="utf-8")
        tr = parse_claude_stream(raw) if model == "opus" else parse_output(raw)
        result[spec] = {
            "status": rec["status"], "turns": tr.assistant_turns, "tokens": tr.tokens_total,
            "permission_rejections": tr.permission_rejections, "tool_errors": tr.tool_errors,
            "scores": rec["axis_scores"],
            "events": [{"turn": e.turn, "type": e.type, "name": e.name,
                        "text": short(e.text, 700), "output": short(e.output, 300), "status": e.status}
                       for e in tr.events],
        }
        print("ok", spec, tr.assistant_turns, "tours,", len(tr.events), "événements")
    Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
