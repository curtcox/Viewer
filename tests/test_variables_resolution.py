from routes.variables import _describe_resolution


def _details_lookup(details, label):
    for item in details:
        if item["label"] == label:
            return item["value"]
    raise AssertionError(f"Label {label!r} not found in details {details!r}")


def test_describe_route_resolution_includes_methods_and_rule():
    resolution = {
        "type": "route",
        "endpoint": "main.index",
        "rule": "/index",
        "blueprint": "main",
        "methods": ["GET", "POST"],
    }

    summary, details = _describe_resolution(resolution)

    assert summary == "Route main.index (/index)"
    assert _details_lookup(details, "Endpoint") == "main.index"
    assert _details_lookup(details, "Rule") == "/index"
    assert _details_lookup(details, "Blueprint") == "main"
    assert _details_lookup(details, "Methods") == "GET, POST"


def test_describe_alias_redirect_includes_status_metadata():
    resolution = {
        "type": "alias_redirect",
        "alias": "sample",
        "target_path": "/target",
        "redirect_location": "/other",
        "target_metadata": {
            "status_code": 302,
            "path": "/resolved",
        },
    }

    summary, details = _describe_resolution(resolution)

    assert summary == "Alias sample → /target"
    assert _details_lookup(details, "Alias") == "sample"
    assert _details_lookup(details, "Target") == "/target"
    assert _details_lookup(details, "Redirect Location") == "/other"
    assert _details_lookup(details, "Target Status") == "302 – Found"
    assert _details_lookup(details, "Resolved Path") == "/resolved"


def test_describe_unknown_resolution_type():
    summary, details = _describe_resolution({"type": "custom_handler"})

    assert summary == "Custom Handler"
    assert details == []
