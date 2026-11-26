"""Génère les figures et results.json des diapositives à partir des summary.json du benchmark.

Aucune valeur n'est saisie à la main : tout vient de data/final-27b.json et data/final-opus.json
(copies de onyxia-agent-bench/runs/final-{27b,opus}/summary.json).

Usage : uv run --with matplotlib python scripts/make_slide_figs.py
"""
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA, FIG = ROOT / "data", ROOT / "figures"
FIG.mkdir(exist_ok=True)

# Palette catégorielle validée (dataviz skill, slots 1 et 2, mode clair) + encres de texte.
BARE, CONF = "#0E9F8E", "#3559FC"  # sarcelle = nu, bleu = configuré
INK, MUTED, SURFACE, GRID = "#22252F", "#5b6070", "#ECEDF2", "#cfd2dc"
OPUS = "#8c93a3"

MODELS = {
    "final-27b": "Qwen 27B\n(auto-hébergé)",
    "final-opus": "Claude Opus 5.5\n(frontière)",
}
TASKS = {
    "t09_secret_trap": "Commit sans fuite d'identifiants",
    "t10_diag_403": "Diagnostic du service rouge",
    "t03_mlflow_train": "Suivi d'expérience MLflow",
    "t23_code_review": "Revue du code d'un collègue",
    "t18_notebook_refactor": "Notebook → module fiable",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 17, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def fr(x, nd=2, sign=False):
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    return s.replace("-", "−").replace(".", ",")


from matplotlib.ticker import FuncFormatter  # noqa: E402


def style(ax, numeric_axis="y"):
    """Virgule décimale sur l'axe numérique uniquement (l'axe catégoriel garde ses libellés)."""
    fmt = FuncFormatter(lambda v, _: fr(v, 2).rstrip("0").rstrip(",") if v else "0")
    (ax.yaxis if numeric_axis == "y" else ax.xaxis).set_major_formatter(fmt)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)


def combined(rec):
    return rec["axis_scores"].get("combined", rec["metrics"].get("combined"))


runs, out = {}, {}
for key in MODELS:
    d = json.load(open(DATA / f"{key}.json"))
    runs[key] = d
    recs = [r for r in d["records"] if r["status"] in ("ok", "timeout", "agent_error")]
    by = defaultdict(dict)  # (task, seed) -> {config: score}
    for r in recs:
        by[(r["task"], r["seed"])][r["config"]] = combined(r)
    per_task = defaultdict(list)
    for (t, _), v in by.items():
        if "C0" in v and "C4" in v:  # paires valides uniquement
            per_task[t].append(v["C4"] - v["C0"])
    tok = defaultdict(list)
    for r in recs:
        tok[r["config"]].append(r["tokens_total"])
    out[key] = {
        "model": d["meta"]["model"],
        "level": {c: d["mean_by_config"][c]["combined"] for c in ("C0", "C4")},
        "delta": d["delta_combined_paired"]["mean"],
        "ci": d["delta_combined_paired"]["ci95"],
        "n_pairs": d["delta_combined_paired"]["n"],
        "per_task": {t: sum(v) / len(v) for t, v in per_task.items()},
        "tokens": {c: sum(v) / len(v) for c, v in tok.items()},
        "wall_s": {c: d["reliability"][c]["mean_wall_clock_s"] for c in ("C0", "C4")},
    }
    out[key]["token_ratio"] = out[key]["tokens"]["C4"] / out[key]["tokens"]["C0"]

(ROOT / "data" / "results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

# --- Figure 1 : niveau de qualité, agent nu vs configuré (étiquettes directes, pas de légende) ---
fig, ax = plt.subplots(figsize=(10, 5.2))
w = 0.36
for i, key in enumerate(MODELS):
    for j, (cfg, col, lab) in enumerate((("C0", BARE, "nu"), ("C4", CONF, "configuré"))):
        v = out[key]["level"][cfg]
        x = i + (j - 0.5) * w
        ax.bar(x, v, w - 0.05, color=col)
        ax.text(x, v + 0.025, fr(v), ha="center", color=INK, fontsize=22, fontweight="bold")
        ax.text(x, 0.03, lab, ha="center", color="white", fontsize=16, fontweight="bold")
    ax.text(i, 1.13, f"{fr(out[key]['delta'], 2, True)}  [{fr(out[key]['ci'][0], 2, True)} ; {fr(out[key]['ci'][1], 2, True)}]",
            ha="center", color=INK, fontsize=17)
ax.set_xticks(range(len(MODELS)), list(MODELS.values()), fontsize=18)
ax.set_ylim(0, 1.24)
ax.set_yticks([0, 0.5, 1])
ax.yaxis.grid(True, color=GRID)
ax.set_axisbelow(True)
style(ax)
fig.tight_layout()
fig.savefig(FIG / "fig_niveau.png", dpi=200)
plt.close(fig)

# --- Figure 2 : gain par tâche, points triés (échelle commune) ---------------------------------
order = sorted(TASKS, key=lambda t: -out["final-27b"]["per_task"][t])
fig, ax = plt.subplots(figsize=(11, 4.8))
ys = list(range(len(order)))
for y in ys:
    a = out["final-27b"]["per_task"][order[y]]
    b = out["final-opus"]["per_task"][order[y]]
    ax.plot([a, b], [y, y], color=GRID, lw=4, zorder=1)
for key, col, lab in (("final-27b", CONF, "Qwen 27B"), ("final-opus", OPUS, "Opus 5.5")):
    vals = [out[key]["per_task"][t] for t in order]
    ax.scatter(vals, ys, s=170, color=col, zorder=3, edgecolor=SURFACE, linewidth=2)
    for y, v in zip(ys, vals):
        dy = -0.3 if key == "final-27b" else 0.3
        ax.text(v, y + dy, fr(v, 2, True), ha="center", va="center", color=INK, fontsize=14,
                bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5), zorder=4)
ax.text(out["final-27b"]["per_task"][order[0]], -0.85, "Qwen 27B", color=CONF, fontsize=16, fontweight="bold", ha="center")
ax.text(out["final-opus"]["per_task"][order[0]] + 0.05, -0.85, "Opus 5.5", color=OPUS, fontsize=16, fontweight="bold", ha="left")
ax.axvline(0, color=MUTED, lw=1)
ax.set_yticks(ys, [TASKS[t] for t in order], fontsize=16)
ax.set_ylim(len(order) - 0.4, -1.2)
ax.set_xlim(-0.2, 1.0)
ax.set_xlabel("Gain apparié (configuré − nu)")
ax.xaxis.grid(True, color=GRID)
ax.set_axisbelow(True)
style(ax, "x")
fig.tight_layout()
fig.savefig(FIG / "fig_par_tache.png", dpi=200)
plt.close(fig)
print(json.dumps({k: {x: out[k][x] for x in ("delta", "ci", "n_pairs", "token_ratio")} for k in out}, indent=1))

# --- Variables Quarto : {{< var q27.delta >}} etc. (virgule décimale française) ----------------
lines = []
for short, key in (("q27", "final-27b"), ("opus", "final-opus")):
    o = out[key]
    lines += [
        f"{short}:",
        f"  nu: '{fr(o['level']['C0'])}'",
        f"  conf: '{fr(o['level']['C4'])}'",
        f"  delta: '{fr(o['delta'], 2, True)}'",
        f"  ci: '[{fr(o['ci'][0], 2, True)} ; {fr(o['ci'][1], 2, True)}]'",
        f"  n: '{o['n_pairs']}'",
        f"  ratio: '{fr(o['token_ratio'], 1)}'",
        f"  tok_nu: '{o['tokens']['C0'] / 1000:.0f}'",
        f"  tok_conf: '{o['tokens']['C4'] / 1000:.0f}'",
        f"  wall_nu: '{fr(o['wall_s']['C0'] / 60, 1)}'",
        f"  wall_conf: '{fr(o['wall_s']['C4'] / 60, 1)}'",
        f"  rej_nu: '{fr(runs[key]['reliability']['C0']['mean_permission_rejections'], 1)}'",
        f"  rej_conf: '{fr(runs[key]['reliability']['C4']['mean_permission_rejections'], 1)}'",
    ]
    for t, v in o["per_task"].items():
        lines.append(f"  {t.split('_')[0]}: '{fr(v, 2, True)}'")
(ROOT / "_variables.yml").write_text("\n".join(lines) + "\n")
