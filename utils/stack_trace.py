"""Stack trace building utilities for comprehensive error reporting."""

import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional


class StackTraceBuilder:
    """Build comprehensive stack trace metadata with source links for project files."""

    def __init__(self, error: Exception, root_path: Path, tracked_paths: frozenset[str]):
        """
        Initialize the stack trace builder.

        Args:
            error: The exception to build a stack trace for
            root_path: The root path of the project
            tracked_paths: Set of git-tracked file paths
        """
        self.error = error
        self.root_path = root_path
        self.tracked_paths = tracked_paths
        self.comprehensive_paths = tracked_paths | self._get_all_project_files()

    def build(self) -> List[Dict[str, Any]]:
        """
        Build the complete stack trace with metadata.

        Returns:
            List of frame dictionaries containing file paths, line numbers,
            function names, code context, and source links
        """
        exception = self._extract_exception(self.error)
        exception_chain = self._get_exception_chain(exception)
        return self._process_exception_chain(exception_chain)

    def _extract_exception(self, error: Exception) -> Exception:
        """Return the underlying exception for Flask HTTP errors."""
        original = getattr(error, "original_exception", None)
        if isinstance(original, Exception):
            return original
        return error

    def _get_exception_chain(self, exc: Exception) -> List[Exception]:
        """
        Get the full chain of exceptions including __cause__ and __context__.

        Args:
            exc: The exception to get the chain for

        Returns:
            List of exceptions in the chain
        """
        exceptions = []
        current: Optional[Exception] = exc
        seen = set()

        while current and id(current) not in seen:
            seen.add(id(current))
            exceptions.append(current)

            # Follow __cause__ first (explicit chaining), then __context__ (implicit)
            next_exc: Optional[Exception] = getattr(current, '__cause__', None) or getattr(current, '__context__', None)
            current = next_exc

        return exceptions

    def _get_all_project_files(self) -> frozenset[str]:
        """
        Get all Python and common source files in the project directory.

        Returns:
            Set of relative paths to project files
        """
        project_files = set()
        try:
            # Get all .py files recursively
            for py_file in self.root_path.rglob("*.py"):
                try:
                    relative = py_file.relative_to(self.root_path).as_posix()
                    project_files.add(relative)
                except ValueError:
                    continue

            # Also add other common source files
            for pattern in ["*.html", "*.js", "*.css", "*.json", "*.md", "*.txt", "*.yml", "*.yaml"]:
                for file in self.root_path.rglob(pattern):
                    try:
                        relative = file.relative_to(self.root_path).as_posix()
                        project_files.add(relative)
                    except ValueError:
                        continue
        except (OSError, ValueError, AttributeError):
            # Handle filesystem errors gracefully
            pass

        return frozenset(project_files)

    def _determine_relative_path(self, absolute_path: Path) -> Optional[str]:
        """
        Determine the relative path from the project root or tracked paths.

        Args:
            absolute_path: The absolute path to convert

        Returns:
            The relative path or None if not found
        """
        # First try to get relative path from project root
        try:
            relative = absolute_path.relative_to(self.root_path).as_posix()
            return relative
        except ValueError:
            pass

        # Fallback: check if path ends with any tracked path
        normalized = absolute_path.as_posix()
        best_match: Optional[str] = None
        for tracked in self.comprehensive_paths:
            if normalized.endswith(tracked):
                if best_match is None or len(tracked) > len(best_match):
                    best_match = tracked
        return best_match

    def _should_create_source_link(self, relative_path: str) -> bool:
        """
        Determine if we should create a source link for this file.

        Args:
            relative_path: The relative path to check

        Returns:
            True if a source link should be created
        """
        if not relative_path:
            return False

        # Create links for ALL files within the project directory, not just git-tracked ones
        full_path = self.root_path / relative_path
        try:
            # Check if file exists and is within project bounds
            resolved_path = full_path.resolve()
            resolved_root = self.root_path.resolve()
            if full_path.exists() and resolved_root in resolved_path.parents:
                return True
        except (OSError, ValueError):
            pass

        return False

    def _strip_project_root_prefix(self, path_str: str) -> str:
        """
        Remove redundant occurrences of the project root from a display path.

        Args:
            path_str: The path string to clean

        Returns:
            The cleaned path string
        """
        if not path_str:
            return path_str

        project_fragment = self.root_path.as_posix().rstrip("/")
        if not project_fragment:
            return path_str

        normalized = path_str.replace("\\", "/")
        updated = normalized
        changed = False

        # Remove every occurrence of the absolute project root, even if repeated.
        while project_fragment and project_fragment in updated:
            changed = True
            start_index = updated.find(project_fragment)
            end_index = start_index + len(project_fragment)
            prefix = updated[:start_index]
            suffix = updated[end_index:]
            if suffix.startswith("/"):
                suffix = suffix[1:]
            updated = (prefix + suffix).lstrip("/")

        if not changed:
            return normalized

        if not updated:
            return normalized or path_str

        return updated

    def _get_code_context(self, frame: traceback.FrameSummary, absolute_path: Path) -> str:
        """
        Get code context around the error line.

        Args:
            frame: The traceback frame
            absolute_path: The absolute path to the source file

        Returns:
            Code context string with line numbers
        """
        code_context: Optional[str] = frame.line
        try:
            if frame.line and frame.lineno is not None and absolute_path.exists():
                # Try to get more lines of context around the error
                with open(absolute_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if 0 < frame.lineno <= len(lines):
                        # Get 5 lines before and after for better context
                        start_line = max(0, frame.lineno - 6)
                        end_line = min(len(lines), frame.lineno + 5)
                        context_lines = []
                        for i in range(start_line, end_line):
                            line_num = i + 1
                            line_content = lines[i].rstrip()
                            marker = ">>> " if line_num == frame.lineno else "    "
                            context_lines.append(f"{marker}{line_num:4d}: {line_content}")
                        code_context = "\n".join(context_lines)
        except (OSError, UnicodeDecodeError, IndexError):
            # Fall back to the original line if we can't read context
            pass

        return code_context or ""

    def _process_exception_chain(self, exception_chain: List[Exception]) -> List[Dict[str, Any]]:
        """
        Process all exceptions in the chain and build frame metadata.

        Args:
            exception_chain: List of exceptions to process

        Returns:
            List of frame dictionaries
        """
        frames: List[Dict[str, Any]] = []

        # Process each exception in the chain
        for exc_index, exc in enumerate(exception_chain):
            traceback_obj = getattr(exc, "__traceback__", None)
            if traceback_obj is None:
                continue

            # Add separator for chained exceptions (except for the first one)
            if exc_index > 0:
                frames.append({
                    "display_path": "--- Exception Chain ---",
                    "lineno": 0,
                    "function": f"Caused by: {type(exc).__name__}",
                    "code": str(exc) if str(exc) else None,
                    "source_link": None,
                    "is_separator": True,
                })

            # Extract frames from this exception's traceback
            for frame in traceback.extract_tb(traceback_obj):
                try:
                    absolute_path = Path(frame.filename).resolve()
                except OSError:
                    absolute_path = Path(frame.filename)

                source_link = None
                display_path = frame.filename

                relative_path = self._determine_relative_path(absolute_path)
                if relative_path:
                    display_path = relative_path
                    # Create source links for ALL project files, not just git-tracked ones
                    if self._should_create_source_link(relative_path):
                        source_link = f"/source/{relative_path}"

                display_path = self._strip_project_root_prefix(display_path)

                # Get more context around the error line if possible (5 lines instead of 2)
                code_context = self._get_code_context(frame, absolute_path)

                frames.append(
                    {
                        "display_path": display_path,
                        "lineno": frame.lineno,
                        "function": frame.name,
                        "code": code_context,
                        "source_link": source_link,
                        "is_separator": False,
                    }
                )

        return frames


def extract_exception(error: Exception) -> Exception:
    """
    Return the underlying exception for Flask HTTP errors.

    Args:
        error: The exception to extract the underlying exception from

    Returns:
        The underlying exception if it exists, otherwise the original error
    """
    original = getattr(error, "original_exception", None)
    if isinstance(original, Exception):
        return original
    return error


def build_stack_trace(error: Exception, root_path: Path, tracked_paths: frozenset[str]) -> List[Dict[str, Any]]:
    """
    Build comprehensive stack trace metadata with source links.

    Args:
        error: The exception to build a stack trace for
        root_path: The root path of the project
        tracked_paths: Set of git-tracked file paths

    Returns:
        List of frame dictionaries containing file paths, line numbers,
        function names, code context, and source links
    """
    builder = StackTraceBuilder(error, root_path, tracked_paths)
    return builder.build()
