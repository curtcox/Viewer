"""Tests for GIT_SHA embedding in deployed app."""
import os
from app import create_app


class TestGitShaEmbedding:
    """Test suite for GIT_SHA configuration and embedding."""

    def test_git_sha_from_environment(self):
        """Test that GIT_SHA is read from environment variable."""
        test_sha = "test1234567890abcdef"
        os.environ["GIT_SHA"] = test_sha

        try:
            app = create_app({"TESTING": True})
            assert app.config.get("GIT_SHA") == test_sha
        finally:
            # Clean up
            if "GIT_SHA" in os.environ:
                del os.environ["GIT_SHA"]

    def test_git_sha_embedded_in_html_meta_tag(self):
        """Test that GIT_SHA appears in HTML meta tag."""
        test_sha = "abc123def456"
        os.environ["GIT_SHA"] = test_sha

        try:
            app = create_app({"TESTING": True})
            with app.test_client() as client:
                response = client.get("/")
                html = response.data.decode("utf-8")

                # Should have meta tag with SHA
                assert f'<meta name="git-sha" content="{test_sha}">' in html
        finally:
            if "GIT_SHA" in os.environ:
                del os.environ["GIT_SHA"]

    def test_git_sha_embedded_in_html_comment(self):
        """Test that GIT_SHA appears in HTML comment."""
        test_sha = "deadbeef12345678"
        os.environ["GIT_SHA"] = test_sha

        try:
            app = create_app({"TESTING": True})
            with app.test_client() as client:
                response = client.get("/")
                html = response.data.decode("utf-8")

                # Should have HTML comment with SHA
                assert f"<!-- GIT_SHA: {test_sha} -->" in html
        finally:
            if "GIT_SHA" in os.environ:
                del os.environ["GIT_SHA"]

    def test_no_git_sha_when_not_set(self):
        """Test that no GIT_SHA appears when environment variable not set."""
        # Ensure GIT_SHA is not in environment
        if "GIT_SHA" in os.environ:
            del os.environ["GIT_SHA"]

        app = create_app({"TESTING": True})

        # Config should not have GIT_SHA
        assert app.config.get("GIT_SHA") is None

        # HTML should not have git-sha meta tag
        with app.test_client() as client:
            response = client.get("/")
            html = response.data.decode("utf-8")

            assert 'name="git-sha"' not in html
            assert "GIT_SHA:" not in html

    def test_git_sha_verifiable_with_grep(self):
        """Test that SHA can be found with grep (as per requirements)."""
        test_sha = "4a02f98bc60aafbe73173442c3f1aef3c5455938"
        os.environ["GIT_SHA"] = test_sha

        try:
            app = create_app({"TESTING": True})
            with app.test_client() as client:
                response = client.get("/")
                html = response.data.decode("utf-8")

                # Simulate what grep would do - simple substring search
                assert test_sha in html
        finally:
            if "GIT_SHA" in os.environ:
                del os.environ["GIT_SHA"]
