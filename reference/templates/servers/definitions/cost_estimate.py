# ruff: noqa: F821
"""Placeholder cost estimation server used by looping control flow."""

from server_execution.conditional_execution import _cost_estimate_cents


def main(
    input_size: float = 0,
    output_size: float = 0,
    execution_time: float = 0,
    context=None,
):
    cost = _cost_estimate_cents(
        int(float(input_size or 0)),
        int(float(output_size or 0)),
        float(execution_time or 0),
    )
    return {"output": str(cost), "content_type": "text/plain"}

