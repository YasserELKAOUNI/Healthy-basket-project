#!/usr/bin/env bash
set -euo pipefail

fail=0
echo "Running pattern guards..."

# Disallow requests.* calls in groceries path and UI
if rg -n "\\brequests\\.(get|post|put|delete|request)\\b" src/groceries web_ui.py smart_grocery_service_cli.py >/dev/null; then
  echo "ERROR: Detected raw requests.* usage outside src/core in groceries/UI paths" >&2
  rg -n "\\brequests\\.(get|post|put|delete|request)\\b" src/groceries web_ui.py smart_grocery_service_cli.py || true
  fail=1
fi

# Disallow os.getenv outside core config in groceries path and UI
if rg -n "os\\.getenv\\(" src/groceries web_ui.py smart_grocery_service_cli.py >/dev/null; then
  echo "ERROR: Detected os.getenv usage outside src/core/config.py in groceries/UI paths" >&2
  rg -n "os\\.getenv\\(" src/groceries web_ui.py smart_grocery_service_cli.py || true
  fail=1
fi

if [[ $fail -ne 0 ]]; then
  exit 2
fi

echo "Guards passed."

