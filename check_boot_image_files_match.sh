#!/usr/bin/env bash
set -euo pipefail

python_cmd="python"
if ! command -v "$python_cmd" >/dev/null 2>&1; then
  python_cmd="python3"
fi

"$python_cmd" generate_boot_image.py

had_differences=0

diff_one() {
  local default_path="$1"
  local boot_path="$2"

  if [[ ! -f "$default_path" ]]; then
    echo "ERROR: missing file: $default_path" >&2
    return 2
  fi

  if [[ ! -f "$boot_path" ]]; then
    echo "ERROR: missing file: $boot_path" >&2
    return 2
  fi

  rc=0
  diff -u "$default_path" "$boot_path" || rc=$?
  if [[ $rc -eq 1 ]]; then
    had_differences=1
    return 0
  fi
  if [[ $rc -eq 0 ]]; then
    return 0
  fi
  return $rc
}

diff_one reference/templates/default.boot.cid reference/templates/boot.cid
diff_one reference/templates/default.boot.json reference/templates/boot.json
diff_one reference/templates/default.boot.source.json reference/templates/boot.source.json

exit "$had_differences"
