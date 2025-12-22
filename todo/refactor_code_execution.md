# Refactor Code Execution: Remaining Items

## Outstanding Work

- Remove legacy chaining branches in `server_execution/code_execution.py`, including `_evaluate_nested_path_to_value_legacy` and any callers that keep the legacy recursion path alive.
- Remove legacy chained-input resolution paths that can no longer be reached now that `_resolve_chained_input_from_path` and `_resolve_chained_input_for_server` always delegate to the pipeline compatibility layer.
- Simplify rollback hooks by deleting the legacy evaluator entry points after cleanup.
- Expand pipeline debug handling beyond the 404 path if product decides to surface debug data on primary routes.

## Current Baseline Tests

```bash
python -m pytest tests/test_pipeline_feature_flag.py tests/test_pipeline_execution.py
```
