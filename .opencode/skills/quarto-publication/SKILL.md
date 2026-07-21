---
name: quarto-publication
description: Write and publish Quarto documents (.qmd) on Onyxia — HTML/PDF reports, reveal.js presentations, dashboards, websites and books; executable R and Python code, parameterized documents, publishing to S3 (diffusion/ folder) or GitHub Pages. Load this skill whenever a report, notice, presentation, dashboard or documentation must be produced, or when the task mentions Quarto, .qmd, migrating an .Rmd, or an HTML/PDF render (rapport, publier, présentation, tableau de bord).
license: MIT
---

# Writing and publishing with Quarto on Onyxia

Quarto is the recommended reporting tool (AGENTS.md): the code (R and/or
Python) stays executable and versioned **with** the report. An existing
`.Rmd` usually migrates by renaming it to `.qmd` and adapting the header.

> **Golden rule**: the render must be **re-generable** (`quarto render`) —
> never hand-pasted results, never a secret or sensitive data in the
> rendered document.

## Core workflow

1. **Create** a `.qmd` (or a project with `_quarto.yml`); read data
   **from S3** (skill `onyxia-storage-s3`), never from a hard-coded local path.
2. **Render / preview**:
   ```bash
   quarto render report.qmd             # -> report.html (or pdf depending on format)
   quarto render report.qmd --to pdf
   quarto preview report.qmd            # live render while writing
   ```
3. **Publish**: copy to the S3 `diffusion/` folder or `quarto publish gh-pages`
   (recipes in [references/formats.md](references/formats.md)).

## Choosing a format

| Deliverable | Format |
|---|---|
| Analysis report, notice | single `.qmd`, `format: html` (or `pdf`) |
| Presentation | `format: revealjs` |
| Monitoring dashboard | `format: dashboard` |
| Multi-page documentation / site | project `type: website` |
| Structured long-form (chapters) | project `type: book` |
| Same report for several years/departments | parameterized document (`params`) |

## Guardrails

- `freeze: auto` in projects: avoids re-running expensive unchanged chunks.
- The `.qmd` is committed; the render (`.html`, `_site/`) goes to `output/`
  or to S3, not into Git (skill `git-workflow-ds`).
- Proofread the render before publishing: no secret, no individual-level data.

## Where to look next

| Need | Read |
|---|---|
| `.qmd` anatomy, website/book/dashboard/revealjs recipes, parameterized documents, publish targets (S3 `diffusion/`, GitHub Pages), diagnostics | [references/formats.md](references/formats.md) |
| Starter project config (website) | [assets/_quarto.yml](assets/_quarto.yml) |
| Starter parameterized report (Python engine) | [assets/report-template.qmd](assets/report-template.qmd) |

## References

- https://quarto.org/docs/guide/
- utilitR, "Produire des documents" section: https://book.utilitr.org
