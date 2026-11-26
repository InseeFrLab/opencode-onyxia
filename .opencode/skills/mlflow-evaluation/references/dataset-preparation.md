# Evaluation datasets

Read this when selecting, creating, adapting, or synthesizing evaluation records. Start with the [dataset SDK
guide](https://mlflow.org/docs/latest/genai/datasets/sdk-guide.md); verify installed signatures and backend
support. If unavailable, use the contract below and installed API introspection; stop if you cannot establish
the correct operation.

## Discover before creating

Use the installed dataset search/list API and inspect actual samples and schema. Discovery failure is not an
empty dataset list. Reuse the user's selected dataset unchanged when evaluating existing outputs.

Use the dataset search API supported by the installed MLflow (`search_datasets()`); never select an arbitrary or first dataset.

## Bind inputs to the real predictor

MLflow calls `predict_fn(**record["inputs"])`. Inspect the application entry point before preparing records.
Dataset keys must match the wrapper's keyword arguments; bind provider/configuration dependencies inside the
wrapper. Nested objects remain values, not extra keyword arguments.

```python
records = [{
    "inputs": {"query": "Where is order 42?", "context": {"order_id": 42}},
    "expectations": {"expected_response": "Order 42 has shipped."},
}]

def predict(query, context):
    return agent(query=query, context=context, provider=config.provider)
```

Ground truth belongs under `expectations` (`expected_response`, `expected_facts`, or the agreed scorer's
fields), not a top-level `expected_response`. Tags/source IDs preserve provenance. Check each scorer's actual
required data.

For precomputed evaluation, preserve `inputs` and `outputs` and omit `predict_fn`. For reruns, use the current
predictor and do not accidentally score stale stored outputs. Inspect trace-search DataFrame columns before
converting `request`/`response` to `inputs`/`outputs`; do not stringify a trace into an input or rename fields
by assumption.

## Create and verify only when needed

Use `mlflow.genai.datasets.create_dataset`, `merge_records`, and backend-supported retrieval;
`mlflow.data.from_pandas` / `mlflow.log_input` are not replacements for a managed GenAI dataset. Ordinary
record lists/DataFrames remain valid inputs to `mlflow.genai.evaluate`.

For an OSS store supporting these signatures:

```python
from mlflow.genai.datasets import create_dataset

dataset = create_dataset(name="agent-regression-v1")
dataset.merge_records(records)
```

Read the records back with the installed dataset's supported DataFrame accessor (`to_df()` or `df`, depending
on backend/version). Verify count, nested inputs, expectations, intended experiment/location, and source
identity before running evaluation.


## Coverage and optional synthesis

Use actual known failures, successes, boundary cases, and representative user journeys. A three-record pilot
validates the pipeline, not population quality; scale only to the requested coverage and cost budget. Keep
source IDs and version changes so comparisons use the same records.

Tiny order-support pilot (`predict(query, context)`); missing orders must not get invented statuses:

```python
records = [
    {"inputs": {"query": "Where is order 42?", "context": {"order_id": 42}},
     "expectations": {"expected_response": "Order 42 has shipped."}},  # success fixture
    {"inputs": {"query": "Where is order 999?", "context": {"order_id": 999}},
     "expectations": {"expected_response": "Order 999 was not found."}},  # missing-order fixture
    {"inputs": {"query": "Where is my order?", "context": {"order_id": None}},
     "expectations": {"expected_response": "Please provide your order ID."}},  # boundary
]
```

Use a fixture/store where 42 is shipped and 999 is absent. The second row exercises a failure path;
correctly reporting the missing order should pass the scorer.

When synthesis is requested and a corpus exists:

- OSS: an available RAGAS `TestsetGenerator` can generate from the corpus; map `user_input` to the real input
  key and `reference` to `expectations.expected_response`. Do not install a synthesis stack for a task
  satisfied by existing records.
- No corpus: prefer representative production queries/history over invented coverage. Remove sensitive data
  before reuse and identify missing ground truth honestly.

Choose size for coverage and confidence, not a universal 50/100-row threshold. Keep a separate holdout for
optimization and preserve dataset/judge versions for comparisons; see
[advanced-evaluation.md](advanced-evaluation.md).

### RAGAS corpus synthesis

[RAGAS v0.3.9 contract](https://github.com/vibrantlabsai/ragas/blob/v0.3.9/src/ragas/testset/synthesizers/generate.py#L101): use configured `generator` (approved LLM/embeddings), LangChain `Document` list `docs`, and selected `dataset`.
Check installed compatibility, review references against the corpus, and adapt `query` before merging.

```python
generated = generator.generate_with_langchain_docs(docs, testset_size=3).to_pandas()
records = [
    {"inputs": {"query": row.user_input},
     "expectations": {"expected_response": row.reference}}
    for row in generated.itertuples(index=False)
]
# After reviewing records and retaining source IDs:
dataset.merge_records(records)
```
