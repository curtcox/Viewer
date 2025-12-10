"""Parser for extracting references from server Python code definitions."""

import re
from typing import Dict, Iterable, List, Optional, Set


class ServerDefinitionParser:
    """Extracts references to variables, secrets, and routes from server Python code."""

    # Pattern matching
    _INDEX_ACCESS_PATTERN = re.compile(
        r"context\[['\"](variables|secrets)['\"]\]\[['\"]([^'\"]+)['\"]\]"
    )

    _GET_ACCESS_PATTERN = re.compile(
        r"context\[['\"](variables|secrets)['\"]\]\.get\(\s*['\"]([^'\"]+)['\"]"
    )

    _ALIAS_ASSIGNMENT_PATTERNS = (
        re.compile(r"(\w+)\s*=\s*context\[['\"](variables|secrets)['\"]\]"),
        re.compile(
            r"(\w+)\s*=\s*context\.get\(\s*['\"](variables|secrets)['\"](?:\s*,[^)]*)?\)"
        ),
    )

    _ALIAS_TO_ALIAS_ASSIGNMENT_PATTERN = re.compile(r"(\w+)\s*=\s*(\w+)")

    _ROUTE_PATTERN = re.compile(r"['\"](/[-_A-Za-z0-9./]*)['\"]")

    def find_variable_aliases(self, definition: str) -> Dict[str, Set[str]]:
        """Find variable aliases like: vars = context['variables']

        Returns a mapping of context sources ('variables', 'secrets') to their aliases.
        """
        aliases: Dict[str, Set[str]] = {'variables': set(), 'secrets': set()}

        for pattern in self._ALIAS_ASSIGNMENT_PATTERNS:
            for alias, source in pattern.findall(definition):
                if alias and source:
                    aliases.setdefault(source, set()).add(alias)

        # Handle alias-to-alias assignments (e.g., vars2 = vars)
        pattern = self._ALIAS_TO_ALIAS_ASSIGNMENT_PATTERN
        for new_alias, existing_alias in pattern.findall(definition):
            if not new_alias or not existing_alias:
                continue
            for source, source_aliases in aliases.items():
                if existing_alias in source_aliases:
                    source_aliases.add(new_alias)

        return aliases

    def find_direct_references(self, definition: str) -> Dict[str, Set[str]]:
        """Find direct access like: context['variables']['name']"""
        matches: Dict[str, Set[str]] = {'variables': set(), 'secrets': set()}

        for pattern in (self._INDEX_ACCESS_PATTERN, self._GET_ACCESS_PATTERN):
            for source, name in pattern.findall(definition):
                if source in matches and name:
                    matches[source].add(name)

        return matches

    def find_aliased_references(
        self,
        definition: str,
        aliases: Dict[str, Set[str]]
    ) -> Dict[str, Set[str]]:
        """Find usage through aliases like: vars['name']"""
        matches: Dict[str, Set[str]] = {'variables': set(), 'secrets': set()}

        for source, alias_names in aliases.items():
            for alias in alias_names:
                if not alias:
                    continue

                alias_pattern = re.compile(
                    rf"(?<!\w){re.escape(alias)}"
                    r"(?:\[['\"]([^'\"]+)['\"]\]"
                    r"|\.get\(\s*['\"]([^'\"]+)['\"](?:\s*,[^)]*)?\))"
                )

                for match in alias_pattern.finditer(definition):
                    name = match.group(1) or match.group(2)
                    if source in matches and name:
                        matches[source].add(name)

        return matches

    def find_parameter_references(
        self,
        parameter_names: Set[str],
        known_variables: Optional[Iterable[str]] = None,
        known_secrets: Optional[Iterable[str]] = None,
    ) -> Dict[str, Set[str]]:
        """Find references from function parameter names.

        Args:
            parameter_names: Set of parameter names from function signature
            known_variables: Known variable names to match against
            known_secrets: Known secret names to match against

        Returns:
            Dict mapping 'variables' and 'secrets' to sets of matched names
        """
        matches: Dict[str, Set[str]] = {'variables': set(), 'secrets': set()}

        # Filter out 'context' which is a special parameter
        parameter_names = {name for name in parameter_names if name != 'context'}

        normalized = {
            'variables': {
                str(name) for name in (known_variables or [])
                if isinstance(name, str) and name
            },
            'secrets': {
                str(name) for name in (known_secrets or [])
                if isinstance(name, str) and name
            },
        }

        # First, match parameters against known variables and secrets
        matched_params = set()
        for source in ('variables', 'secrets'):
            for name in parameter_names & normalized[source]:
                matches[source].add(name)
                matched_params.add(name)

        # Then categorize unmatched parameters by naming convention:
        # - ALL_UPPERCASE names (with optional underscores) are likely secrets
        # - Other names are likely variables
        unmatched_params = parameter_names - matched_params
        for name in unmatched_params:
            # Check if the name is all uppercase (allowing underscores and digits)
            if name and name.replace('_', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '').isupper():
                matches['secrets'].add(name)
            else:
                matches['variables'].add(name)

        return matches

    def extract_context_references(
        self,
        definition: Optional[str],
        known_variables: Optional[Iterable[str]] = None,
        known_secrets: Optional[Iterable[str]] = None,
        parameter_names: Optional[Set[str]] = None,
    ) -> Dict[str, List[str]]:
        """Return referenced variable and secret names from a server definition.

        Args:
            definition: The server definition code
            known_variables: Known variable names for parameter matching
            known_secrets: Known secret names for parameter matching
            parameter_names: Parameter names from function signature

        Returns:
            Dict with 'variables' and 'secrets' keys mapping to sorted lists of referenced names
        """
        if not definition:
            return {'variables': [], 'secrets': []}

        aliases = self.find_variable_aliases(definition)
        direct_refs = self.find_direct_references(definition)
        alias_refs = self.find_aliased_references(definition, aliases)

        combined: Dict[str, Set[str]] = {'variables': set(), 'secrets': set()}
        for source, values in combined.items():
            values.update(direct_refs.get(source, set()))
            values.update(alias_refs.get(source, set()))

        if parameter_names:
            param_refs = self.find_parameter_references(
                parameter_names,
                known_variables,
                known_secrets
            )
            for source, values in combined.items():
                values.update(param_refs.get(source, set()))

        return {source: sorted(values) for source, values in combined.items()}

    def extract_route_references(self, definition: Optional[str]) -> List[str]:
        """Return route-like paths referenced within the server definition."""
        if not definition:
            return []

        candidates: Set[str] = set()
        for match in self._ROUTE_PATTERN.finditer(definition):
            value = match.group(1)
            if not value or value in {"/", "//"}:
                continue
            if value.startswith('//'):
                continue
            if value.startswith('/http') or value.startswith('/https'):
                continue
            if not re.search(r"[A-Za-z]", value):
                continue
            candidates.add(value)

        return sorted(candidates)


__all__ = ["ServerDefinitionParser"]
