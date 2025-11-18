from __future__ import annotations

import html
import re
from urllib.parse import urlsplit

import pytest

from cid_presenter import format_cid
from database import db
from models import Alias, CID, Server

pytestmark = pytest.mark.integration


def _normalize_location(location: str) -> str:
    parsed = urlsplit(location)
    return parsed.path or "/"


def _create_alias_chain(app, base_name: str, redirect_count: int, final_target: str) -> list[str]:
    names: list[str] = []
    with app.app_context():
        for index in range(redirect_count):
            alias_name = f"{base_name}-{index + 1}"
            next_path = final_target if index + 1 == redirect_count else f"/{base_name}-{index + 2}"
            db.session.add(
                Alias(
                    name=alias_name,
                    definition=f"{alias_name} -> {next_path}",
                )
            )
            names.append(alias_name)
        db.session.commit()
    return names


def _extract_request_paths(page: str) -> list[str]:
    return re.findall(r'data-request-path="([^"]+)"', page)


def test_route_details_for_builtin_index(client):
    """The route explorer should describe built-in Flask routes."""

    response = client.get("/")
    assert response.status_code == 200

    detail_response = client.get("/routes/")
    assert detail_response.status_code == 200

    page = detail_response.get_data(as_text=True)
    assert "Route Explorer" in page
    assert "Handled by Flask endpoint main.index" in page
    assert 'badge text-bg-primary me-2">200' in page


def test_route_details_for_alias_redirect(client):
    """Alias routes should surface their target path and redirect."""

    alias_response = client.get("/css/darkmode", follow_redirects=False)
    assert alias_response.status_code == 302
    target = alias_response.headers.get("Location")
    assert target

    detail_response = client.get("/routes/css/darkmode")
    assert detail_response.status_code == 200
    page = detail_response.get_data(as_text=True)

    assert "Alias" in page
    assert "CSS" in page
    assert target in page

    # The alias title should link directly to the definition.
    assert re.search(
        r'class="fw-semibold text-decoration-none" href="/aliases/CSS">CSS</a>',
        page,
    )

    # Redirect messaging should include a hyperlink to the destination.
    assert re.search(
        r"Redirects to\s*<a class=\"text-decoration-none\" href=\""
        + re.escape(target)
        + r"\">"
        + re.escape(target)
        + r"</a>",
        page,
    )


def test_route_details_for_server_execution(client, integration_app):
    """Server-backed routes should report the server definition."""

    with integration_app.app_context():
        db.session.add(
            Server(
                name="demo",
                definition=(
                    "def main():\n"
                    "    return {'output': 'demo output', 'content_type': 'text/plain'}\n"
                ),
            )
        )
        db.session.commit()

    server_response = client.get("/demo", follow_redirects=False)
    assert server_response.status_code == 302
    redirect_target = server_response.headers.get("Location")
    assert redirect_target and redirect_target.startswith("/")

    detail_response = client.get("/routes/demo")
    assert detail_response.status_code == 200
    page = detail_response.get_data(as_text=True)

    assert "Server" in page
    assert "demo" in page
    assert "Executes server code" in page
    assert "def main():" in page


def test_route_details_for_direct_cid(client, integration_app):
    """CID paths should display CID helper markup."""

    cid_value = format_cid("abcdef123456")

    with integration_app.app_context():
        db.session.add(
            CID(
                path=f"/{cid_value}",
                file_data=b"hello world",
            )
        )
        db.session.commit()

    cid_response = client.get(f"/{cid_value}")
    assert cid_response.status_code == 200

    detail_response = client.get(f"/routes/{cid_value}")
    assert detail_response.status_code == 200
    page = detail_response.get_data(as_text=True)

    assert "CID" in page
    assert "cid-display" in page
    assert cid_value in page
    assert "hello world" in page


@pytest.mark.parametrize("redirect_count", [2, 3])
def test_route_details_follow_alias_chain_to_server(
    client, integration_app, redirect_count
):
    server_name = f"chain-server-destination-{redirect_count}"
    base_name = f"chain-server-{redirect_count}"

    with integration_app.app_context():
        db.session.add(
            Server(
                name=server_name,
                definition=(
                    "def main():\n"
                    "    return {'output': 'demo output', 'content_type': 'text/plain'}\n"
                ),
            )
        )
        db.session.commit()

    alias_names = _create_alias_chain(
        integration_app, base_name, redirect_count, final_target=f"/{server_name}"
    )

    current_path = f"/{base_name}-1"
    visited_paths = [current_path]
    for _ in range(redirect_count):
        response = client.get(current_path, follow_redirects=False)
        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        current_path = _normalize_location(location)
        visited_paths.append(current_path)

    assert visited_paths[-1] == f"/{server_name}"

    server_response = client.get(current_path, follow_redirects=False)
    assert server_response.status_code == 302

    detail_response = client.get(f"/routes/{base_name}-1")
    assert detail_response.status_code == 200
    page = detail_response.get_data(as_text=True)

    path_order = _extract_request_paths(page)
    assert path_order == visited_paths

    for alias_name in alias_names:
        assert f'href="/aliases/{alias_name}"' in page

    assert f'href="/servers/{server_name}"' in page

    for path in visited_paths:
        assert f'href="{path}"' in page

    assert page.count("Redirects to") == redirect_count

    for index, alias_name in enumerate(alias_names):
        target_path = visited_paths[index + 1]
        escaped_line = html.escape(f"{alias_name} -> {target_path}")
        assert escaped_line in page
        alias_pattern = (
            r'class="fw-semibold text-decoration-none" href="/aliases/'
            + re.escape(alias_name)
            + r'">'
            + re.escape(alias_name)
            + r"</a>"
        )
        assert re.search(alias_pattern, page)
        assert re.search(
            r"Redirects to\s*<a class=\"text-decoration-none\" href=\""
            + re.escape(target_path)
            + r"\">"
            + re.escape(target_path)
            + r"</a>",
            page,
        )

    assert "def main():" in page
    server_pattern = (
        r'class="fw-semibold text-decoration-none" href="/servers/'
        + re.escape(server_name)
        + r'">'
        + re.escape(server_name)
        + r"</a>"
    )
    assert re.search(server_pattern, page)


@pytest.mark.parametrize("redirect_count", [4, 5])
def test_route_details_follow_alias_chain_to_cid(
    client, integration_app, redirect_count
):
    cid_value = format_cid(f"cidchain{redirect_count}abcdef")
    base_name = f"chain-cid-{redirect_count}"

    with integration_app.app_context():
        db.session.add(
            CID(
                path=f"/{cid_value}",
                file_data=b"cid target",
            )
        )
        db.session.commit()

    alias_names = _create_alias_chain(
        integration_app, base_name, redirect_count, final_target=f"/{cid_value}"
    )

    current_path = f"/{base_name}-1"
    visited_paths = [current_path]
    for _ in range(redirect_count):
        response = client.get(current_path, follow_redirects=False)
        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        current_path = _normalize_location(location)
        visited_paths.append(current_path)

    assert visited_paths[-1] == f"/{cid_value}"

    final_response = client.get(current_path, follow_redirects=False)
    assert final_response.status_code == 200

    detail_response = client.get(f"/routes/{base_name}-1")
    assert detail_response.status_code == 200
    page = detail_response.get_data(as_text=True)

    path_order = _extract_request_paths(page)
    assert path_order == visited_paths

    for alias_name in alias_names:
        assert f'href="/aliases/{alias_name}"' in page

    assert f'href="/{cid_value}"' in page
    assert "cid-display" in page

    for path in visited_paths:
        assert f'href="{path}"' in page

    assert page.count("Redirects to") == redirect_count

    for index, alias_name in enumerate(alias_names):
        target_path = visited_paths[index + 1]
        escaped_line = html.escape(f"{alias_name} -> {target_path}")
        assert escaped_line in page
        assert re.search(
            r"Redirects to\s*<a class=\"text-decoration-none\" href=\""
            + re.escape(target_path)
            + r"\">"
            + re.escape(target_path)
            + r"</a>",
            page,
        )

    assert "cid target" in page
