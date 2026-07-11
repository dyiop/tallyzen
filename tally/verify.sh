#!/usr/bin/env bash
# Verify the Tally connector answers every endpoint the agents rely on.
# Green across the board = the Accountant agent will get real answers.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="http://127.0.0.1:8800"

python3 "$HERE/tally_connector.py" >/tmp/tallyconn.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT
sleep 1.5

check() {
  local name="$1" path="$2" needle="$3"
  local out; out="$(curl -s "$BASE$path")"
  if echo "$out" | grep -q "$needle"; then
    echo "  ok   $name"
  else
    echo "  FAIL $name  ($path did not contain '$needle')"
  fi
}

echo "Verifying Tally connector at $BASE ..."
check "health"               "/health"                          '"ok": true'
check "sales_by_destination" "/sales_by_destination"            '"grand_total_6m"'
check "sales_by_product"     "/sales_by_product"                'Vannamei'
check "receivables overdue"  "/receivables?overdue_only=1"      'Gulf Coast Seafood'
check "cash_position"        "/cash_position"                   '"total"'
check "gst_position"         "/gst_position"                    '"net_payable"'
check "sales_trend"          "/sales_trend"                     '"monthly_total"'
check "vendor lookup"        "/vendor?name=coastal"             '"found": true'
echo "done."
