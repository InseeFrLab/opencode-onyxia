---
name: mlflow-trace-instrumentation
description: Add or repair MLflow tracing in Python LLM/RAG/agent apps (typically calling the self-hosted gateway): framework autologging, custom spans, persisted-trace verification, tracing needed for evaluation. For classic ML experiment tracking use mlflow-tracking.
license: Apache-2.0
metadata:
  upstream: mlflow/skills@6303169
  adapted: onyxia
---

# Instrument MLflow tracing

Reuse working tracing for investigation or evaluation.

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
- Calls made through the gateway with the OpenAI client are traced by `mlflow.openai.autolog()` (client built with `base_url=os.environ["OPENAI_BASE_URL"]`).

## Prerequisites

- Check entry point, language/framework, SDK version, tracking URI, experiment, and deployment identity.
- Preserve destinations and providers. Explicit application destinations override inherited environment values; assistant telemetry may use another experiment.
- Read [Python](references/python.md) for the runtime.

## Step 1: Check the destination

Keep the configured backend (the shared Onyxia MLflow at `MLFLOW_TRACKING_URI`) and proceed to Step 2.

## Step 2: Enable framework tracing

- Enable the matching integration before execution. LangGraph uses `mlflow.langchain.autolog()`, not `mlflow.langgraph.autolog()`.
- Do not wrap automatically traced nodes, tools, or models again. Reserve manual spans for uncaptured work or an outer application boundary.

## Step 3: Capture application work

- Trace meaningful root, LLM, retrieval, tool, routing, and external I/O (files/queues).
  Skip utility, configuration, and logging noise.
- Capture actual relevant inputs/outputs explicitly for manual spans; redact before export.

## Step 4: Run one request

- Run one representative request; record start/end epoch milliseconds.
- Save its trace ID immediately in-process: `mlflow.get_last_active_trace_id()`.
- Write/flush the trace ID to a file or captured stdout before readback; retain it if the process is cancelled.
  Do not rerun to recover an ID.

<a id="verification"></a>

## Verification

- Fetch a **persisted application trace**, not a local span or old trace.
- Set a **60-second wall-clock process deadline** for readback, including flush, SDK retries, requests, and backoff.
  Terminate at expiry unless the user explicitly requests deeper troubleshooting.
- Tool yields/thread-wait timeouts do not cancel calls. Without cancellation, report backend verification as unperformed.

- Flush once (`mlflow.flush_trace_async_logging()`); fetch the saved ID.
- Without an ID, search once in the configured experiment with run-time bounds, `max_results=1`, and spans included.
- Bound searches with `trace.timestamp_ms`; result limits do not bound scans. Python `search_traces()` has no `start_time` keyword.

For Python readback, adapt this recipe to the saved run values and enforce the deadline externally:

```python
mlflow.flush_trace_async_logging()
if trace_id:
    trace = mlflow.get_trace(trace_id)
else:
    traces = mlflow.search_traces(
        locations=[experiment_id],
        filter_string=(f"trace.timestamp_ms >= {run_start_ms} "
                       f"AND trace.timestamp_ms <= {run_end_ms}"),
        max_results=1, return_type="list", include_spans=True,
    )
    trace = traces[0] if traces else None
assert trace is not None, "No persisted trace read back"
assert run_start_ms <= trace.info.request_time <= run_end_ms
assert trace.data.spans, "No spans captured"
```

- Inspect expected root/graph, model, retrieval, and tool spans and actual I/O. Confirm the application's request, not scorer or assistant telemetry.
- Check the experiment from returned metadata.
- Reuse returned spans; stop after success.

- Retry at most once after a concrete quick fix **within the original budget**.
- Stop on missing provider keys, auth/permission errors, or `RESOURCE_EXHAUSTED`/429.
- No parallel searches, repeated agent runs, raw REST, or alternate credentials.
- Report operation/error, captured ID, successes, and unverified results. Request the missing prerequisite, not secrets.
- Keep instrumentation changes if backend verification is blocked; pause evaluation until tracing is verified.

Return the verified trace ID/link and observed spans. Do not label an unverified link as proof.

## References

- Deployment, async export, sampling: [production](references/production.md).
- Async/thread context, redaction, caught errors or links: [advanced patterns](references/advanced-patterns.md).
- Cross-service parent propagation: [distributed tracing](references/distributed-tracing.md).
- User ratings tied to traces: [feedback collection](references/feedback-collection.md).
- Unreadable non-chat root previews: [root span previews](references/root-span-previews.md).
- Explaining captured behavior: `mlflow-trace-analysis` (optional follow-on task).

- Other integrations: [automatic tracing docs](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic.md). Check installed signatures/types.
- Missing/moved topic: [llms.txt](https://mlflow.org/docs/latest/llms.txt). Docs unavailable: use local recipes and installed API introspection; stop if correctness remains uncertain.
