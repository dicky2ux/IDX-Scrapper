#!/usr/bin/env bash
# Basic CLI wrapper for export_idx_keywords_csv.py
# Usage examples:
#   ./run_idx.sh                 # headless automated run using saved storage state
#   ./run_idx.sh --persist-login  # will open a headed browser to login if no saved state
#   ./run_idx.sh --proxy http://user:pass@proxy:3128
#   ./run_idx.sh --date-from 20251010 --date-to 20251013 --output out.csv

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PY=python3
SCRIPT="$SCRIPT_DIR/export_idx_keywords_csv.py"

# defaults
PROXY=""
PERSIST_LOGIN=""
HEADLESS="--headless"
OUTPUT="tmp_idx_scrapper.csv"
DATE_FROM=""
DATE_TO=""
AUTH_TOKEN=""
# parse simple flags
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --proxy)
      PROXY="$2"
      shift; shift
      ;;
    --persist-login)
      PERSIST_LOGIN="--persist-login"
      shift
      ;;
    --no-headless)
      HEADLESS=""
      shift
      ;;
    --output|-o)
      OUTPUT="$2"; shift; shift ;;
    --date-from)
      DATE_FROM="$2"; shift; shift ;;
    --date-to)
      DATE_TO="$2"; shift; shift ;;
    --auth-token)
      AUTH_TOKEN="$2"; shift; shift ;;
    -h|--help)
      sed -n '1,120p' "$SCRIPT_DIR/run_idx.sh"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"; exit 1 ;;
  esac
done

CMD=("$PY" "$SCRIPT")
CMD+=("--output" "$OUTPUT")
CMD+=("--automated-playwright")
CMD+=("$HEADLESS")
if [[ -n "$PERSIST_LOGIN" ]]; then
  CMD+=("$PERSIST_LOGIN")
fi
if [[ -n "$PROXY" ]]; then
  CMD+=("--proxy" "$PROXY")
fi
if [[ -n "$DATE_FROM" ]]; then
  CMD+=("--date-from" "$DATE_FROM")
fi
if [[ -n "$DATE_TO" ]]; then
  CMD+=("--date-to" "$DATE_TO")
fi
if [[ -n "$AUTH_TOKEN" ]]; then
  CMD+=("--auth-token" "$AUTH_TOKEN")
fi

echo "Running: ${CMD[*]}"
exec "${CMD[@]}"
