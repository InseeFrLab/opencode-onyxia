#!/usr/bin/env python3
"""Vendor + adapt the MLflow skills from mlflow/skills (pinned in UPSTREAM.lock) for Onyxia.

    python3 -I scripts/vendor_mlflow_skills.py [--dest .opencode/skills] [--src DIR] [--sha SHA]

Without --src the pinned revision is downloaded into a fresh temporary directory (upstream content is treated as
untrusted data: it is only copied/edited, never executed). Every edit asserts that its target text exists, so a
drift in the upstream files fails loudly instead of silently producing a half-adapted skill. Re-running overwrites
the five vendored `mlflow-*` skill directories: put any manual change in this script instead.
Adapted files are Apache-2.0 (see licenses/mlflow-skills.LICENSE and THIRD_PARTY.md).
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--dest", default=str(REPO_ROOT / ".opencode" / "skills"))
ap.add_argument("--src", help="already downloaded checkout of mlflow/skills (skips the download)")
ap.add_argument("--sha", help="override the commit pinned in UPSTREAM.lock")
args = ap.parse_args()


def pinned_sha() -> str:
    for line in (REPO_ROOT / "UPSTREAM.lock").read_text().splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "mlflow-skills":
            return parts[2]
    sys.exit("mlflow-skills not found in UPSTREAM.lock")


SHA = args.sha or pinned_sha()
UP = f"mlflow/skills@{SHA[:7]}"
DST = Path(args.dest)

SKILLS = [
    "mlflow-docs",
    "mlflow-trace-instrumentation",
    "mlflow-trace-retrieval",
    "mlflow-trace-analysis",
    "mlflow-evaluation",
]
EXCLUDE = {
    "mlflow-trace-instrumentation/references/databricks.md",
    "mlflow-trace-instrumentation/references/typescript.md",
    "mlflow-evaluation/references/databricks-online-monitoring.md",
    "mlflow-trace-analysis/agents/openai.yaml",
}


# ---------------------------------------------------------------- fetch (pinned SHA)
def fetch(sha: str, out: Path) -> Path:
    def get(url: str) -> bytes:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.read()

    tree = json.loads(get(f"https://api.github.com/repos/mlflow/skills/git/trees/{sha}?recursive=1"))["tree"]
    wanted = [e["path"] for e in tree if e["type"] == "blob" and e["path"].split("/")[0] in SKILLS]
    for rel in wanted:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(get(f"https://raw.githubusercontent.com/mlflow/skills/{sha}/{rel}"))
    return out


# ---------------------------------------------------------------- copy
SRC = Path(args.src) if args.src else fetch(SHA, Path(tempfile.mkdtemp(prefix="mlflow-skills-")))
for s in SKILLS:
    d = DST / s
    if d.exists():
        shutil.rmtree(d)
    for f in sorted((SRC / s).rglob("*")):
        rel = f.relative_to(SRC).as_posix()
        if f.is_dir() or rel in EXCLUDE:
            continue
        out = DST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, out)
        if f.suffix == ".sh":
            out.chmod(0o755)


# ---------------------------------------------------------------- helpers
def rd(rel):
    return (DST / rel).read_text()


def wr(rel, txt):
    (DST / rel).write_text(txt)


def edit(rel, old, new, count=1):
    t = rd(rel)
    assert t.count(old) == count, f"{rel}: expected {count}x {old[:70]!r}, found {t.count(old)}"
    wr(rel, t.replace(old, new))


def rx(rel, pattern, repl, flags=0):
    t = rd(rel)
    new, n = re.subn(pattern, repl, t, flags=flags)
    assert n >= 1, f"{rel}: regex not matched: {pattern[:70]!r}"
    wr(rel, new)


def drop_line(rel, contains):
    t = rd(rel)
    lines = t.split("\n")
    keep = [l for l in lines if contains not in l]
    assert len(keep) == len(lines) - 1, f"{rel}: drop_line {contains[:60]!r} matched {len(lines) - len(keep)}"
    wr(rel, "\n".join(keep))


def frontmatter(rel, description):
    """Replace the description and add license/provenance metadata."""
    t = rd(rel)
    new, n = re.subn(r"^description:.*$", "description: " + description, t, count=1, flags=re.MULTILINE)
    assert n == 1, rel
    new = new.replace("\n---\n", f"\nlicense: Apache-2.0\nmetadata:\n  upstream: {UP}\n  adapted: onyxia\n---\n", 1)
    wr(rel, new)


GATE = """
## Onyxia prerequisites (check first)

- **Server version gate.** GenAI tracing/evaluation needs an MLflow >=3 server. Check the shared instance
  (read-only, no `curl` prompt needed):
  `uv run python -c "import os,urllib.request as u; print(u.urlopen(os.environ['MLFLOW_TRACKING_URI'].rstrip('/')+'/version').read().decode())"`.
  If `MLFLOW_TRACKING_URI` is unset (launch an MLflow service from the catalog), the server is unreachable or
  it reports a version below 3: **stop and say so**. Do not start another backend or switch provider.
- **Models stay on the platform.** LLM calls (the application, scorers, judges) go through the self-hosted
  gateway: `OPENAI_BASE_URL` / `OPENAI_API_KEY` (set `OPENAI_API_BASE` to the same URL for LiteLLM-based
  judges). Use a platform model such as `openai:/gemma4-26b-moe`. Never send traces or data to an external
  provider (confidentiality rule in `AGENTS.md`).
- Classic ML experiment tracking (params, metrics, model registry) is the `mlflow-tracking` skill, not this one.
- Client: `uv add 'mlflow>=3.8'`. Never print or commit tokens.
"""

GATE_SHORT = """
## Onyxia prerequisites

Needs an MLflow >=3 server at `MLFLOW_TRACKING_URI` (launch MLflow from the catalog; verify with the version
check in the `mlflow-trace-instrumentation` skill). If it is unset, unreachable or older, stop and say so. Traces
contain prompts and outputs: keep them on the platform, never export them to an external service.
"""

# ================================================================= instrumentation
I = "mlflow-trace-instrumentation"
frontmatter(
    f"{I}/SKILL.md",
    "Add or repair MLflow tracing in Python LLM/RAG/agent apps (typically calling the self-hosted gateway): "
    "framework autologging, custom spans, persisted-trace verification, tracing needed for evaluation. "
    "For classic ML experiment tracking use mlflow-tracking.",
)
edit(
    f"{I}/SKILL.md",
    "Reuse working tracing for investigation or evaluation.\n",
    "Reuse working tracing for investigation or evaluation.\n"
    + GATE
    + "- Calls made through the gateway with the OpenAI client are traced by `mlflow.openai.autolog()` "
    '(client built with `base_url=os.environ["OPENAI_BASE_URL"]`).\n',
)
edit(
    f"{I}/SKILL.md",
    "- Read [Python](references/python.md) or [TypeScript](references/typescript.md) for the runtime.",
    "- Read [Python](references/python.md) for the runtime.",
)
rx(
    f"{I}/SKILL.md",
    r"## Step 1: Check the destination \(Databricks only\)\n.*?(?=## Step 2)",
    "## Step 1: Check the destination\n\nKeep the configured backend (the shared Onyxia MLflow at `MLFLOW_TRACKING_URI`) "
    "and proceed to Step 2.\n\n",
    re.DOTALL,
)
edit(
    f"{I}/SKILL.md",
    "`mlflow.get_last_active_trace_id()` in Python; the active span's ID in TypeScript.",
    "`mlflow.get_last_active_trace_id()`.",
)
edit(
    f"{I}/SKILL.md",
    "(`mlflow.flush_trace_async_logging()` / `await mlflow.flushTraces()`)",
    "(`mlflow.flush_trace_async_logging()`)",
)
edit(
    f"{I}/SKILL.md",
    "- Every UC search needs `trace.timestamp_ms`; result limits do not bound scans. Python `search_traces()` has no `start_time` keyword.",
    "- Bound searches with `trace.timestamp_ms`; result limits do not bound scans. Python `search_traces()` has no `start_time` keyword.",
)
edit(
    f"{I}/SKILL.md",
    "- Check experiment/location from returned metadata, or the bound UC location if no experiment ID exists.",
    "- Check the experiment from returned metadata.",
)
edit(f"{I}/SKILL.md", "auth/permission errors, warehouse timeouts, or", "auth/permission errors, or")
edit(
    f"{I}/SKILL.md",
    "repeated agent runs, direct UC SQL, raw REST, alternate credentials, or warehouse fallbacks.",
    "repeated agent runs, raw REST, or alternate credentials.",
)
edit(
    f"{I}/SKILL.md",
    " For Databricks use the [verified trace URL rules](references/databricks.md#link-to-the-verified-trace), not an experiment-only link.",
    "",
)
edit(
    f"{I}/SKILL.md",
    "- Explaining captured behavior: `mlflow-trace-analysis`; implementing a requested behavior fix: `mlflow-agent-improvement`, carrying the trace evidence. These are optional follow-on tasks.",
    "- Explaining captured behavior: `mlflow-trace-analysis` (optional follow-on task).",
)
rx(f"{I}/references/python.md", r" For Databricks, follow \[UC setup\]\(databricks\.md\)[^\n]*insufficient\.", "")
edit(
    f"{I}/references/production.md",
    " Databricks also needs [UC setup](databricks.md); local success does not verify deployed permissions.",
    " Local success does not verify deployed permissions.",
)
edit(f"{I}/references/production.md", ", TypeScript `await mlflow.flushTraces()`", "")
edit(
    f"{I}/references/production.md",
    "instrumentation stays in [Python](python.md) / [TypeScript](typescript.md).",
    "instrumentation stays in [Python](python.md).",
)
edit(
    f"{I}/references/feedback-collection.md", " in Python; `mlflow.getCurrentActiveSpan()?.traceId` in TypeScript)", ")"
)
edit(
    f"{I}/references/distributed-tracing.md",
    "([Python](python.md), [Databricks](databricks.md))",
    "([Python](python.md))",
)

# ================================================================= retrieval
R = "mlflow-trace-retrieval"
frontmatter(
    f"{R}/SKILL.md",
    "Retrieve MLflow traces by ID or search by run, session, user, status, time, tags, feedback, or span fields. "
    "Use for trace lookup and filtering of LLM/agent apps; retrieval alone does not require diagnosis.",
)
edit(f"{R}/SKILL.md", "# Retrieve MLflow traces\n", "# Retrieve MLflow traces\n" + GATE_SHORT)
rx(f"{R}/SKILL.md", r"For Databricks UC traces, first read[^\n]*\n\n", "")
edit(
    f"{R}/SKILL.md",
    "Every UC search needs a `trace.timestamp_ms` lower bound;",
    "Bound searches with a `trace.timestamp_ms` lower bound;",
)
edit(f"{R}/SKILL.md", "before a broad UC search.", "before a broad search.")

# ================================================================= analysis
A = "mlflow-trace-analysis"
frontmatter(
    f"{A}/SKILL.md",
    "Analyze MLflow traces, agent failures, and multi-turn chat sessions of LLM/agent apps. Explain errors, "
    "unexpected output, quality issues, latency, or cross-turn propagation without editing application code.",
)
edit(f"{A}/SKILL.md", "# Analyze MLflow traces\n", "# Analyze MLflow traces\n" + GATE_SHORT)
edit(
    f"{A}/SKILL.md",
    "pass diagnosis and trace ID to `mlflow-agent-improvement` when installed; investigation itself",
    "pass diagnosis and trace ID to the user or the build agent; investigation itself",
)
edit(
    f"{A}/references/session-analysis.md",
    " On Databricks with UC, even `max-results 1` requires a timestamp predicate.",
    "",
)
edit(
    f"{A}/references/session-analysis.md",
    "is **not suitable for UC discovery** because it has no time filter; use the bounded workflow above.",
    "has no time filter; prefer the bounded workflow above on large experiments.",
)
edit(
    f"{A}/references/session-analysis.md",
    "pass the diagnosis and trace IDs to `mlflow-agent-improvement` when installed.",
    "pass the diagnosis and trace IDs to the user or the build agent.",
)
edit(
    f"{A}/references/trace-structure.md",
    "including UC `trace:/<location>/<id>` or legacy `tr-` prefix.",
    "including the `tr-` prefix.",
)
edit(
    f"{A}/references/trace-structure.md",
    "Alternatively UC catalog/schema/table prefix; a schema can contain several prefixes. UC `experiment_id` may be absent; use configured experiment identity.",
    "Experiment that holds the trace.",
)
edit(
    f"{A}/references/cross-trace-analysis.md",
    "Aggregate trends with `mlflow-trace-metrics`; use this guide",
    "Aggregate trends yourself (e.g. `mlflow traces search` output in duckdb/pandas); use this guide",
)
edit(
    f"{A}/references/cross-trace-analysis.md",
    "Use `mlflow-trace-metrics` to check whether",
    "Aggregate across a sample of traces to check whether",
)
for f in ("discover_schema.sh", "inspect_turn.sh"):
    (DST / A / "scripts" / f).chmod(0o755)

# ================================================================= evaluation
E = "mlflow-evaluation"
frontmatter(
    f"{E}/SKILL.md",
    "Design MLflow scorers and run GenAI evaluation on an LLM app/agent, dataset, precomputed outputs, or traces; "
    "judges run on the self-hosted gateway. For classic ML runs use mlflow-tracking.",
)
edit(f"{E}/SKILL.md", "# Agent evaluation\n", "# Agent evaluation\n" + GATE)
edit(
    f"{E}/SKILL.md",
    "For missing configuration, use `mlflow-onboarding` when available.",
    "For missing configuration, follow the Onyxia prerequisites above (`MLFLOW_TRACKING_URI` is injected by the MLflow service).",
)
drop_line(f"{E}/SKILL.md", "- For UC, use the intended fully qualified table and backend-supported discovery.")
edit(
    f"{E}/SKILL.md",
    "- Requested behavior fixes: hand results to `mlflow-agent-improvement`.",
    "- Requested behavior fixes: hand results (with trace evidence) to the user or the build agent; this skill never edits application code.",
)
rx(f"{E}/SKILL.md", r"- Databricks production scoring:\n[^\n]*\n[^\n]*start monitoring\.\n", "")
# scorers: judge models limited to the platform
rx(f"{E}/references/scorers.md", r"\| `databricks` \|[^\n]*\n\| `databricks:/<endpoint>` \|[^\n]*\n", "")
edit(
    f"{E}/references/scorers.md",
    "| `openai:/<model>` | Configured OpenAI credentials / gateway |",
    "| `openai:/<model>` | **Onyxia default**: self-hosted gateway via `OPENAI_BASE_URL` / `OPENAI_API_KEY` (e.g. `openai:/gemma4-26b-moe`) |",
)
drop_line(f"{E}/references/scorers.md", "| `anthropic:/<model>` |")
drop_line(f"{E}/references/scorers.md", "| `gemini:/<model>` |")
edit(
    f"{E}/references/scorers.md",
    "(historically Databricks managed judging on Databricks and OpenAI elsewhere); inspect them rather than",
    "(historically OpenAI); on Onyxia always set the judge model explicitly to a platform model, and inspect defaults rather than",
)
rx(
    f"{E}/references/dataset-preparation.md",
    r"OSS dataset search and Unity Catalog discovery differ\.[^\n]*\n[^\n]*\n[^\n]*first dataset\.\n",
    "Use the dataset search API supported by the installed MLflow (`search_datasets()`); never select an arbitrary or first dataset.\n",
)
rx(
    f"{E}/references/dataset-preparation.md",
    r'<a id="databricks-unity-catalog-considerations"></a>\n\n## Databricks Unity Catalog compatibility.*?(?=\n## )',
    "",
    re.DOTALL,
)
rx(
    f"{E}/references/dataset-preparation.md",
    r"- Databricks: inspect the installed.*?`merge_records`\.\n",
    "",
    re.DOTALL,
)
edit(
    f"{E}/references/advanced-evaluation.md",
    "dataset schema, Unity Catalog setup, and coverage guidance",
    "dataset schema and coverage guidance",
)
rx(f"{E}/references/troubleshooting.md", r" Use `mlflow-onboarding` when connection setup is missing\.", "")
for key in (
    "Invalid Databricks profile/auth",
    "UC dataset unsupported fields",
    "UC table missing",
    "If UC dataset metadata access",
    "If UC creation requires Spark",
):
    drop_line(f"{E}/references/troubleshooting.md", key)
rx(
    f"{E}/references/prompt-optimization.md",
    r"On Databricks, confirm its Unity Catalog `catalog\.schema\.name`[^\n]*?; do not overwrite",
    "Do not overwrite",
)
edit(
    f"{E}/references/prompt-optimization.md",
    "The old Databricks evaluation skill used",
    "Earlier versions of this skill used",
)
rx(
    f"{E}/references/judge-alignment.md",
    r"On Databricks, confirm the intended Unity Catalog dataset[^.]*\.\s*Do not create a dataset in an arbitrary accessible schema\.\s*",
    "",
)

# online monitoring (a managed-platform feature) is not covered: its reference file is excluded above
rx(
    f"{E}/references/scorers.md",
    r"For production scoring read\n\[Databricks online monitoring\]\(databricks-online-monitoring\.md\): registration does not start monitoring, and\nserialization/sample settings need separate verification\.",
    "Continuous/online production scoring is not covered by this skill: registering a scorer does not start\n"
    "monitoring. Evaluate sampled production traces offline instead (see [advanced-evaluation.md](advanced-evaluation.md)).",
)
rx(
    f"{E}/references/scorers-constraints.md",
    r"cannot install missing dependencies; see\n  \[online monitoring\]\(databricks-online-monitoring\.md\)\.",
    "cannot install missing dependencies.",
)
rx(
    f"{E}/references/troubleshooting.md",
    r"\| Monitoring serialization fails \|[^\n]*\n\| Registered scorer never scores production \|[^\n]*\n",
    "",
)
edit(
    f"{A}/references/cross-trace-analysis.md",
    " Use `mlflow-agent-improvement` to turn a recurring failure into a regression test.",
    " Turn a recurring failure into a regression case in the evaluation dataset (`mlflow-evaluation`).",
)

# ================================================================= docs (rewritten for opencode tools)
D = "mlflow-docs"
wr(
    f"{D}/SKILL.md",
    f"""---
name: mlflow-docs
description: Look up the official MLflow documentation (features, APIs, tracing, evaluation, integrations) from mlflow.org via its llms.txt index. Use when the user asks how an MLflow API works or for MLflow doc examples. The llms.txt index covers GenAI topics; for classic tracking, see mlflow-tracking.
license: Apache-2.0
metadata:
  upstream: {UP}
  adapted: onyxia
---

# MLflow documentation search

Needs outbound HTTPS to `mlflow.org` (public documentation; no data is sent). If the fetch is refused or fails,
say so and answer from the installed package (`help()` / `inspect`) instead of guessing.

## Workflow

1. Fetch the index `https://mlflow.org/docs/latest/llms.txt` with the `webfetch` tool and find the page(s)
   relevant to the topic.
2. Fetch the `.md` source of that page (`https://mlflow.org/docs/latest/<path>.md`).
3. Present the result with **verbatim** code examples, then adapt them to the project (tracking URI from
   `MLFLOW_TRACKING_URI`, models from the self-hosted gateway).

## Anti-patterns

- Do not fetch `.html` pages: use the `.md` sources only.
- Do not use web search: start from `llms.txt` (search returns outdated or third-party content).
- Do not ask vaguely ("extract the documentation"): ask for the code blocks verbatim, without summarising.
- Do not use versioned paths (`/docs/3.8/`) unless the user explicitly requests a version: use `/docs/latest/`.
- Do not guess URLs: verify the path exists in `llms.txt` before fetching.
- Do not follow external links (GitHub, PyPI, third parties) and do not mix in other libraries' docs.
- `llms.txt` indexes the GenAI documentation only; for classic ML tracking pages the paths may differ.
- The docs describe the latest MLflow: check the server and client versions (see `mlflow-tracking`) before
  using an API.
""",
)

print("adapted:", ", ".join(SKILLS))
