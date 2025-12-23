"""HRX (Human Readable Archive) parser.

Implementation of the HRX format specification from https://github.com/google/hrx
"""

import re
from typing import Dict, Optional


class HRXParseError(Exception):
    """Exception raised when HRX parsing fails."""


class HRXArchive:
    """Represents a parsed HRX archive."""

    def __init__(self, archive_string: str):
        """Parse an HRX archive string.

        Args:
            archive_string: The HRX format string to parse

        Raises:
            HRXParseError: If the archive is invalid or empty
        """
        self.files: Dict[str, str] = {}
        self.directories: set[str] = set()
        self._parse(archive_string)

    def _parse(self, archive_string: str) -> None:
        """Parse the HRX archive string.

        Args:
            archive_string: The HRX format string to parse

        Raises:
            HRXParseError: If the archive is invalid
        """
        if not archive_string or not archive_string.strip():
            raise HRXParseError("Archive string is empty")

        # Find the first boundary to determine the boundary pattern
        first_boundary_match = re.match(r"^<(=+)>", archive_string)
        if not first_boundary_match:
            raise HRXParseError("No valid boundary found in archive")

        equals_count = len(first_boundary_match.group(1))
        boundary = f"<{'=' * equals_count}>"

        # Split the archive by boundaries
        # Each entry starts with a boundary
        pattern = f"^{re.escape(boundary)}"
        lines = archive_string.split("\n")

        current_path: Optional[str] = None
        current_content: list[str] = []
        in_content = False

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check if this line is a boundary
            if line.startswith(boundary):
                # Save previous entry if any
                if current_path is not None:
                    content = "\n".join(current_content)
                    if current_path.endswith("/"):
                        # Directory entry
                        self.directories.add(current_path[:-1])
                    else:
                        # File entry
                        self.files[current_path] = content
                    current_content = []
                    current_path = None
                    in_content = False

                # Parse the new entry
                rest = line[len(boundary) :].strip()
                if rest:
                    # File or directory entry
                    current_path = rest
                    in_content = True
                # else: comment boundary (no path) - we skip these

            elif in_content and current_path is not None:
                # Accumulate content lines
                current_content.append(line)

            i += 1

        # Handle the last entry
        if current_path is not None:
            content = "\n".join(current_content)
            if current_path.endswith("/"):
                self.directories.add(current_path[:-1])
            else:
                self.files[current_path] = content

    def list_files(self) -> list[str]:
        """Return a sorted list of all file paths in the archive.

        Returns:
            Sorted list of file paths
        """
        return sorted(self.files.keys())

    def get_file(self, path: str) -> Optional[str]:
        """Get the content of a file by path.

        Args:
            path: The file path to retrieve

        Returns:
            File content as string, or None if not found
        """
        return self.files.get(path)

    def has_file(self, path: str) -> bool:
        """Check if a file exists in the archive.

        Args:
            path: The file path to check

        Returns:
            True if file exists, False otherwise
        """
        return path in self.files


def parse_hrx(archive_string: str) -> HRXArchive:
    """Parse an HRX archive string.

    Args:
        archive_string: The HRX format string to parse

    Returns:
        Parsed HRXArchive object

    Raises:
        HRXParseError: If the archive is invalid
    """
    return HRXArchive(archive_string)
