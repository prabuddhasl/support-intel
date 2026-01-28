#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KB_FILE="$ROOT_DIR/kb/sample_kb.md"

if [ ! -f "$KB_FILE" ]; then
  echo "KB sample not found: $KB_FILE"
  exit 1
fi

curl -sS -X POST "http://localhost:8000/kb/upload?source=sample_kb&source_url=https://example.com/kb" \
  -F "file=@${KB_FILE}"
