#!/usr/bin/env bash
# Quick helper to upload photos to njorda.net
# Usage:
#   ./upload.sh                         -> Starts local drag-and-drop web uploader (http://localhost:8765)
#   ./upload.sh path/to/pic.jpg --push  -> CLI upload and push

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -eq 0 ]; then
  python3 "${SCRIPT_DIR}/scripts/local_uploader.py"
else
  python3 "${SCRIPT_DIR}/scripts/add_photo.py" "$@"
fi
