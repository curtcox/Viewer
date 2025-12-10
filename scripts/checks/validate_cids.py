#!/usr/bin/env python3
"""Validate CID filenames against their content."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def _load_generate_cid():
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from cid_core import generate_cid

    return generate_cid


generate_cid = _load_generate_cid()


@dataclass
class CidFailure:
    """Information about a CID validation failure."""

    filename: str
    computed_cid: str
    size_bytes: int
    failure_type: str = "mismatch"  # "mismatch" or "short_filename"


@dataclass
class ValidationSummary:
    """Aggregate validation results."""

    cid_count: int
    valid_count: int
    total_bytes: int
    failures: list[CidFailure]

    @property
    def total_size_readable(self) -> str:
        return _format_size(self.total_bytes)

    @property
    def short_filename_failures(self) -> list[CidFailure]:
        return [f for f in self.failures if f.failure_type == "short_filename"]

    @property
    def mismatch_failures(self) -> list[CidFailure]:
        return [f for f in self.failures if f.failure_type == "mismatch"]

    def to_json(self) -> str:
        payload = {
            "cid_count": self.cid_count,
            "valid_count": self.valid_count,
            "total_bytes": self.total_bytes,
            "total_size_readable": self.total_size_readable,
            "failures": [asdict(failure) for failure in self.failures],
            "short_filename_failures": len(self.short_filename_failures),
            "mismatch_failures": len(self.mismatch_failures),
        }
        return json.dumps(payload, indent=2)


def _format_size(byte_count: int) -> str:
    units = ["bytes", "KB", "MB", "GB", "TB"]
    size = float(byte_count)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "bytes":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{byte_count} bytes"


def _select_cid_directory(cid_dir: Path | None) -> Path:
    if cid_dir is not None:
        return cid_dir

    repo_root = Path(__file__).resolve().parents[2]
    default_path = Path("/cids")
    if default_path.is_dir():
        return default_path

    return repo_root / "cids"


def _iter_cid_files(cid_dir: Path) -> Iterable[Path]:
    if not cid_dir.exists():
        raise FileNotFoundError(f"CID directory does not exist: {cid_dir}")

    for path in sorted(cid_dir.iterdir()):
        if path.is_file():
            yield path


def validate_cids(cid_dir: Path) -> ValidationSummary:
    cid_files = list(_iter_cid_files(cid_dir))
    failures: list[CidFailure] = []
    total_bytes = 0

    for path in cid_files:
        content = path.read_bytes()
        total_bytes += len(content)
        
        # Check if filename is less than 94 characters (literal CID)
        if len(path.name) < 94:
            failures.append(
                CidFailure(
                    filename=path.name,
                    computed_cid="N/A",
                    size_bytes=len(content),
                    failure_type="short_filename",
                )
            )
            continue
        
        # Check if computed CID matches filename
        computed = generate_cid(content)
        if computed != path.name:
            failures.append(
                CidFailure(
                    filename=path.name,
                    computed_cid=computed,
                    size_bytes=len(content),
                    failure_type="mismatch",
                )
            )

    valid_count = len(cid_files) - len(failures)
    return ValidationSummary(
        cid_count=len(cid_files),
        valid_count=valid_count,
        total_bytes=total_bytes,
        failures=failures,
    )


def write_report(summary: ValidationSummary, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(summary.to_json(), encoding="utf-8")

    report_lines = [
        "CID Validation Report",
        "--------------------",
        f"Total CIDs: {summary.cid_count}",
        f"Valid CIDs: {summary.valid_count}",
        f"Failures: {len(summary.failures)}",
        f"Total size: {summary.total_bytes} bytes ({summary.total_size_readable})",
        "",
    ]

    if summary.failures:
        if summary.short_filename_failures:
            report_lines.append("Short Filename Failures (CIDs with filenames < 94 characters):")
            report_lines.append("These CIDs should use embedded values rather than being stored as files.")
            for failure in summary.short_filename_failures:
                report_lines.append(
                    f"- {failure.filename} (length: {len(failure.filename)}, {failure.size_bytes} bytes)"
                )
            report_lines.append("")
        
        if summary.mismatch_failures:
            report_lines.append("CID Mismatch Failures:")
            for failure in summary.mismatch_failures:
                report_lines.append(
                    f"- {failure.filename} (computed {failure.computed_cid}, {failure.size_bytes} bytes)"
                )
    else:
        report_lines.append("No validation failures detected.")

    (output_dir / "report.txt").write_text("\n".join(report_lines), encoding="utf-8")



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate CID filenames against their contents.")
    parser.add_argument(
        "--cid-dir",
        type=Path,
        default=None,
        help="Directory containing CID files (defaults to /cids or ./cids).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where the validation report will be written.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cid_dir = _select_cid_directory(args.cid_dir)
    summary = validate_cids(cid_dir)
    write_report(summary, args.output_dir)
    return 0 if not summary.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
