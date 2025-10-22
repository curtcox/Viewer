import os
import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "test-secret-key")

from flask import session

from app import app, db
from analytics import (
    create_page_view_record,
    get_paginated_page_views,
    get_user_history_statistics,
    make_session_permanent,
    should_track_page_view,
    track_page_view,
)
from models import PageView


class TestAnalytics(unittest.TestCase):
    """Exercise analytics helpers against an in-memory database."""

    def setUp(self):
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            WTF_CSRF_ENABLED=False,
        )
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        self.user_id = "analytics-user"

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_make_session_permanent_marks_session(self):
        with app.test_request_context("/"):
            session.permanent = False
            make_session_permanent()
            self.assertTrue(session.permanent)

    def test_should_track_page_view_requires_success_status(self):
        with app.test_request_context("/dashboard"):
            response = app.response_class(status=404)
            self.assertFalse(should_track_page_view(response))

    def test_should_track_page_view_skips_static_and_ajax_requests(self):
        with app.test_request_context("/static/logo.png"):
            response = app.response_class(status=200)
            self.assertFalse(should_track_page_view(response))

        with app.test_request_context(
            "/dashboard",
            headers={"X-Requested-With": "XMLHttpRequest"},
        ):
            response = app.response_class(status=200)
            self.assertFalse(should_track_page_view(response))

    def test_should_track_page_view_accepts_standard_requests(self):
        with app.test_request_context(
            "/history",
            headers={"User-Agent": "Browser", "X-Requested-With": ""},
        ):
            response = app.response_class(status=200)
            self.assertTrue(should_track_page_view(response))

    def test_track_page_view_persists_record(self):
        long_user_agent = "Agent" * 200  # exceeds 500 characters when repeated
        environ_overrides = {"REMOTE_ADDR": "203.0.113.10"}
        with app.test_request_context(
            "/servers",
            headers={"User-Agent": long_user_agent},
            environ_overrides=environ_overrides,
        ):
            response = app.response_class(status=200)
            with patch(
                "analytics.current_user",
                new=SimpleNamespace(id=self.user_id),
            ):
                result = track_page_view(response)

        self.assertIs(result, response)
        stored = PageView.query.filter_by(user_id=self.user_id).one()
        self.assertEqual(stored.path, "/servers")
        self.assertEqual(stored.method, "GET")
        self.assertEqual(stored.user_agent, long_user_agent[:500])
        self.assertEqual(stored.ip_address, "203.0.113.10")

    def test_track_page_view_rolls_back_on_error(self):
        with app.test_request_context("/servers"):
            response = app.response_class(status=200)
            with patch(
                "analytics.current_user",
                new=SimpleNamespace(id=self.user_id),
            ), patch("analytics.should_track_page_view", return_value=True), patch(
                "analytics.create_page_view_record",
                side_effect=RuntimeError("boom"),
            ), patch.object(db.session, "rollback") as rollback:
                result = track_page_view(response)

        self.assertIs(result, response)
        rollback.assert_called_once()
        self.assertEqual(PageView.query.count(), 0)

    def test_create_page_view_record_reflects_request_details(self):
        with app.test_request_context(
            "/notes",
            method="POST",
            headers={"User-Agent": "AgentX"},
            environ_overrides={"REMOTE_ADDR": "198.51.100.1"},
        ):
            with patch(
                "analytics.current_user",
                new=SimpleNamespace(id=self.user_id),
            ):
                record = create_page_view_record()

        self.assertEqual(record.user_id, self.user_id)
        self.assertEqual(record.path, "/notes")
        self.assertEqual(record.method, "POST")
        self.assertEqual(record.user_agent, "AgentX")
        self.assertEqual(record.ip_address, "198.51.100.1")

    def test_get_user_history_statistics(self):
        now = datetime.now(timezone.utc)
        views = [
            PageView(user_id=self.user_id, path="/a", viewed_at=now),
            PageView(user_id=self.user_id, path="/a", viewed_at=now + timedelta(minutes=1)),
            PageView(user_id=self.user_id, path="/b", viewed_at=now + timedelta(minutes=2)),
            PageView(user_id="other", path="/a", viewed_at=now + timedelta(minutes=3)),
        ]
        db.session.add_all(views)
        db.session.commit()

        stats = get_user_history_statistics(self.user_id)
        self.assertEqual(stats["total_views"], 3)
        self.assertEqual(stats["unique_paths"], 2)
        self.assertEqual(stats["popular_paths"][0].path, "/a")
        self.assertEqual(stats["popular_paths"][0].count, 2)

    def test_get_paginated_page_views_orders_recent_first(self):
        base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        for offset, path in enumerate(["/first", "/second", "/third"], start=1):
            db.session.add(
                PageView(
                    user_id=self.user_id,
                    path=path,
                    viewed_at=base_time + timedelta(hours=offset),
                )
            )
        db.session.commit()

        page = get_paginated_page_views(self.user_id, page=1, per_page=2)
        self.assertEqual(page.total, 3)
        self.assertEqual(len(page.items), 2)
        self.assertEqual([item.path for item in page.items], ["/third", "/second"])


if __name__ == "__main__":
    unittest.main()
