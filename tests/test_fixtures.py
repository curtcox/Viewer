"""Shared test fixtures, factories, and utilities for route testing."""

import re
from datetime import datetime, timezone
from typing import Optional

from alias_definition import format_primary_alias_line
from cid_utils import generate_cid
from database import db
from models import Alias, CID, Secret, Server, Variable


def _alias_definition(
    name: str,
    target: str,
    *,
    match_type: str = "literal",
    pattern: str | None = None,
    ignore_case: bool = False,
) -> str:
    """
    Create an alias definition string.

    Args:
        name: The alias name
        target: The target path
        match_type: The match type ('literal', 'prefix', 'regex')
        pattern: Optional pattern override
        ignore_case: Whether to ignore case in matching

    Returns:
        Formatted alias definition string
    """
    pattern_value = pattern
    if match_type == "literal" and not pattern_value:
        pattern_value = None
    elif pattern_value is None:
        pattern_value = f"/{name}"
    return format_primary_alias_line(
        match_type,
        pattern_value,
        target,
        ignore_case=ignore_case,
        alias_name=name,
    )


class TestDataFactory:
    """Factory for creating test data with sensible defaults."""

    @staticmethod
    def create_alias(
        name: str,
        target: str,
        *,
        match_type: str = "literal",
        pattern: str | None = None,
        ignore_case: bool = False,
        commit: bool = True,
    ) -> Alias:
        """
        Create an alias for testing.

        Args:
            name: The alias name
            target: The target path
            match_type: The match type ('literal', 'prefix', 'regex')
            pattern: Optional pattern override
            ignore_case: Whether to ignore case in matching
            commit: Whether to commit to the database

        Returns:
            Created Alias instance
        """
        definition = _alias_definition(
            name,
            target,
            match_type=match_type,
            pattern=pattern,
            ignore_case=ignore_case,
        )
        alias = Alias(
            name=name,
            definition=definition,
        )
        db.session.add(alias)
        if commit:
            db.session.commit()
        return alias

    @staticmethod
    def create_cid(
        content: bytes | str,
        *,
        path: str | None = None,
        commit: bool = True,
    ) -> CID:
        """
        Create a CID for testing.

        Args:
            content: The content to store (bytes or string)
            path: Optional custom path (auto-generated if not provided)
            commit: Whether to commit to the database

        Returns:
            Created CID instance
        """
        if isinstance(content, str):
            content = content.encode("utf-8")

        if path is None:
            cid_value = generate_cid(content)
            path = f"/{cid_value}"

        cid = CID(
            path=path,
            file_data=content,
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add(cid)
        if commit:
            db.session.commit()
        return cid

    @staticmethod
    def create_server(
        name: str,
        definition: str,
        *,
        definition_cid: str | None = None,
        commit: bool = True,
    ) -> Server:
        """
        Create a server for testing.

        Args:
            name: The server name
            definition: The server definition code
            definition_cid: Optional CID for the definition
            commit: Whether to commit to the database

        Returns:
            Created Server instance
        """
        server = Server(
            name=name,
            definition=definition,
            definition_cid=definition_cid,
        )
        db.session.add(server)
        if commit:
            db.session.commit()
        return server

    @staticmethod
    def create_variable(
        name: str,
        value: str,
        *,
        commit: bool = True,
    ) -> Variable:
        """
        Create a variable for testing.

        Args:
            name: The variable name
            value: The variable value
            commit: Whether to commit to the database

        Returns:
            Created Variable instance
        """
        variable = Variable(
            name=name,
            definition=value,
        )
        db.session.add(variable)
        if commit:
            db.session.commit()
        return variable

    @staticmethod
    def create_secret(
        name: str,
        encrypted_value: bytes,
        *,
        commit: bool = True,
    ) -> Secret:
        """
        Create a secret for testing.

        Args:
            name: The secret name
            encrypted_value: The encrypted secret value
            commit: Whether to commit to the database

        Returns:
            Created Secret instance
        """
        secret = Secret(
            name=name,
            definition=encrypted_value.decode("utf-8")
            if isinstance(encrypted_value, bytes)
            else encrypted_value,
        )
        db.session.add(secret)
        if commit:
            db.session.commit()
        return secret


class CrossReferenceAssertions:
    """Assertion helpers for cross-reference functionality."""

    @staticmethod
    def assert_entity_in_page(test_case, page: str, entity_key: str, entity_type: str):
        """
        Assert that an entity appears in the page with the correct key.

        Args:
            test_case: The test case instance (for assertions)
            page: The HTML page content
            entity_key: The expected entity key
            entity_type: The entity type for error messages
        """
        pattern = rf'<div[^>]*data-entity-key="{re.escape(entity_key)}"[^>]*>'
        test_case.assertIsNotNone(
            re.search(pattern, page),
            f"{entity_type} with key '{entity_key}' not found in page",
        )

    @staticmethod
    def assert_reference_in_page(
        test_case, page: str, ref_key: str, source: str, target: str
    ):
        """
        Assert that a reference appears in the page.

        Args:
            test_case: The test case instance (for assertions)
            page: The HTML page content
            ref_key: The expected reference key
            source: The source entity name (for error messages)
            target: The target entity name (for error messages)
        """
        pattern = rf'<div[^>]*data-reference-key="{re.escape(ref_key)}"[^>]*>'
        test_case.assertIsNotNone(
            re.search(pattern, page),
            f"Reference from '{source}' to '{target}' (key: {ref_key}) not found in page",
        )


class SearchAssertions:
    """Assertion helpers for search functionality."""

    @staticmethod
    def assert_search_category_results(
        test_case,
        response,
        category: str,
        expected_count: int,
        expected_items: Optional[list] = None,
    ):
        """
        Verify search category results match expectations.

        Args:
            test_case: The test case instance (for assertions)
            response: The Flask response object
            category: The search category ('aliases', 'servers', etc.)
            expected_count: The expected number of results
            expected_items: Optional list of expected item names
        """
        test_case.assertEqual(response.status_code, 200)
        payload = response.get_json()
        test_case.assertIn("categories", payload)
        test_case.assertIn(category, payload["categories"])

        category_data = payload["categories"][category]
        test_case.assertEqual(
            category_data["count"],
            expected_count,
            f"Expected {expected_count} {category} results, got {category_data['count']}",
        )

        if expected_items is not None:
            actual_names = [item["name"] for item in category_data.get("items", [])]
            for expected_name in expected_items:
                test_case.assertIn(
                    expected_name,
                    actual_names,
                    f"Expected '{expected_name}' in {category} results",
                )

    @staticmethod
    def assert_search_empty(test_case, response):
        """
        Verify that search returns no results.

        Args:
            test_case: The test case instance (for assertions)
            response: The Flask response object
        """
        test_case.assertEqual(response.status_code, 200)
        payload = response.get_json()
        test_case.assertIn("categories", payload)

        for category, data in payload["categories"].items():
            test_case.assertEqual(
                data["count"],
                0,
                f"Expected no results in {category}, got {data['count']}",
            )


class RouteAssertions:
    """General assertion helpers for route testing."""

    @staticmethod
    def assert_redirects_to(test_case, response, expected_path: str):
        """
        Assert that a response redirects to the expected path.

        Args:
            test_case: The test case instance (for assertions)
            response: The Flask response object
            expected_path: The expected redirect path
        """
        test_case.assertEqual(response.status_code, 302)
        test_case.assertEqual(response.location, expected_path)

    @staticmethod
    def assert_contains_text(
        test_case, response, expected_text: str, status_code: int = 200
    ):
        """
        Assert that a response contains the expected text.

        Args:
            test_case: The test case instance (for assertions)
            response: The Flask response object
            expected_text: The text that should appear in the response
            status_code: The expected HTTP status code
        """
        test_case.assertEqual(response.status_code, status_code)
        page = response.get_data(as_text=True)
        test_case.assertIn(expected_text, page)

    @staticmethod
    def assert_json_response(
        test_case, response, expected_data: dict, status_code: int = 200
    ):
        """
        Assert that a JSON response matches expected data.

        Args:
            test_case: The test case instance (for assertions)
            response: The Flask response object
            expected_data: Dictionary of expected data to match
            status_code: The expected HTTP status code
        """
        test_case.assertEqual(response.status_code, status_code)
        actual_data = response.get_json()
        for key, value in expected_data.items():
            test_case.assertIn(key, actual_data)
            test_case.assertEqual(actual_data[key], value)


__all__ = [
    "TestDataFactory",
    "CrossReferenceAssertions",
    "SearchAssertions",
    "RouteAssertions",
    "_alias_definition",
]
