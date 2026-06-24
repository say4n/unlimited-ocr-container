#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "bash" || "${1:-}" == "sh" || "${1:-}" == "python" || "${1:-}" == "python3" ]]; then
  exec "$@"
fi

exec python /opt/Unlimited-OCR/infer.py "$@"
