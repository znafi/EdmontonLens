#!/usr/bin/env bash
# ============================================================================
# EdmontonLens -- Local Database Health Check (Bash / Linux / macOS)
# ----------------------------------------------------------------------------
# Checks PostgreSQL (or SQLite fallback), MySQL, and SQL Server.
# For every table in the schema: prints row count and most recent ingested_at.
# Flags empty tables ([WARN] EMPTY) and tables with data older than 48 hours
# ([WARN] STALE). Exit code 0 if all pass, 1 if any warn/fail.
#
# Requirements:
#   - PostgreSQL: psql  (brew install postgresql)
#   - MySQL:      mysql (brew install mysql-client)
#   - SQL Server: sqlcmd from mssql-tools
#       macOS:  brew tap microsoft/mssql-release && brew install mssql-tools18
#       Linux:  https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-setup-tools
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

TABLES=(
  transit_routes
  transit_stops
  transit_performance
  transit_stop_delays
  parks
  waste_schedules
  neighbourhoods
  neighbourhood_kpis
  delay_predictions
)

STALE_HOURS=48
EXIT_CODE=0

_load_env_var() {
  local var="$1"
  local val="${!var:-}"
  if [[ -z "${val}" && -f "${ENV_FILE}" ]]; then
    val="$(grep -E "^${var}=" "${ENV_FILE}" | head -n1 | cut -d'=' -f2-)"
  fi
  echo "${val}"
}

DATABASE_URL="$(_load_env_var DATABASE_URL)"
[[ -z "${DATABASE_URL}" ]] && DATABASE_URL="sqlite:///./data/edmonton_lens.db"

MYSQL_DATABASE_URL="$(_load_env_var MYSQL_DATABASE_URL)"
SQLSERVER_DATABASE_URL="$(_load_env_var SQLSERVER_DATABASE_URL)"

# ---------- helpers ----------------------------------------------------------

_age_status() {
  local last_ts="$1"
  if [[ -z "${last_ts}" || "${last_ts}" == "NULL" ]]; then echo ""; return; fi
  local last_epoch now_epoch age_hours
  last_epoch="$(date -d "${last_ts}" +%s 2>/dev/null \
    || date -j -f "%Y-%m-%d %H:%M:%S" "${last_ts%%.*}" +%s 2>/dev/null \
    || echo 0)"
  now_epoch="$(date +%s)"
  if [[ "${last_epoch}" -gt 0 ]]; then
    age_hours=$(( (now_epoch - last_epoch) / 3600 ))
    if [[ "${age_hours}" -gt "${STALE_HOURS}" ]]; then
      echo "STALE:${age_hours}"
    fi
  fi
}

_print_row() {
  local table="$1" count="$2" last_ts="$3"
  local status="[OK]"
  if [[ "${count}" == "0" || -z "${count}" ]]; then
    status="[WARN] EMPTY"; EXIT_CODE=1
  else
    local age_info
    age_info="$(_age_status "${last_ts}")"
    if [[ "${age_info}" == STALE:* ]]; then
      status="[WARN] STALE (${age_info#STALE:}h)"; EXIT_CODE=1
    fi
  fi
  printf "  %-22s rows=%-7s last_ingested=%-26s %s\n" \
    "${table}" "${count:-0}" "${last_ts:-none}" "${status}"
}

# ============================================================================
# PostgreSQL / SQLite
# ============================================================================
echo ""
echo "EdmontonLens DB Health Check"
echo "======================================================================"
echo "[PostgreSQL / SQLite]  ${DATABASE_URL%%://*}://***"
echo "----------------------------------------------------------------------"

pg_query() {
  local sql="$1"
  if [[ "${DATABASE_URL}" == sqlite* ]]; then
    local db_path="${DATABASE_URL#sqlite:///}"
    [[ "${db_path}" == ./* ]] && db_path="${ROOT_DIR}/${db_path#./}"
    sqlite3 "${db_path}" "${sql}" 2>/dev/null
  else
    psql "${DATABASE_URL}" -tAc "${sql}" 2>/dev/null
  fi
}

for table in "${TABLES[@]}"; do
  count="$(pg_query "SELECT COUNT(*) FROM ${table};" 2>/dev/null || echo 0)"
  last_ts="$(pg_query "SELECT MAX(ingested_at) FROM ${table};" 2>/dev/null || echo "")"
  _print_row "${table}" "${count}" "${last_ts}"
done

# ============================================================================
# MySQL
# ============================================================================
echo ""
echo "[MySQL]"
echo "----------------------------------------------------------------------"

if [[ -z "${MYSQL_DATABASE_URL}" ]]; then
  echo "  MYSQL_DATABASE_URL not set -- skipping MySQL checks."
else
  # Parse mysql+pymysql://user:pass@host:port/db
  _mysql_user="$(echo "${MYSQL_DATABASE_URL}" | sed -E 's|.*://([^:]+):.*|\1|')"
  _mysql_pass="$(echo "${MYSQL_DATABASE_URL}" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')"
  _mysql_host="$(echo "${MYSQL_DATABASE_URL}" | sed -E 's|.*@([^:/]+)[:/].*|\1|')"
  _mysql_port="$(echo "${MYSQL_DATABASE_URL}" | sed -E 's|.*:([0-9]+)/.*|\1|')"
  _mysql_db="$(echo "${MYSQL_DATABASE_URL}" | sed -E 's|.*/([^?]+).*|\1|')"

  mysql_query() {
    local sql="$1"
    mysql -h "${_mysql_host}" -P "${_mysql_port}" -u "${_mysql_user}" \
      -p"${_mysql_pass}" "${_mysql_db}" -sNe "${sql}" 2>/dev/null
  }

  if mysql_query "SELECT 1" >/dev/null 2>&1; then
    for table in "${TABLES[@]}"; do
      count="$(mysql_query "SELECT COUNT(*) FROM \`${table}\`;" 2>/dev/null || echo 0)"
      last_ts="$(mysql_query "SELECT MAX(ingested_at) FROM \`${table}\`;" 2>/dev/null || echo "")"
      _print_row "${table}" "${count}" "${last_ts}"
    done
  else
    echo "  Could not connect to MySQL at ${_mysql_host}:${_mysql_port} -- is docker compose up?"
    EXIT_CODE=1
  fi
fi

# ============================================================================
# SQL Server
# ============================================================================
echo ""
echo "[SQL Server]"
echo "----------------------------------------------------------------------"

if [[ -z "${SQLSERVER_DATABASE_URL}" ]]; then
  echo "  SQLSERVER_DATABASE_URL not set -- skipping SQL Server checks."
else
  _ss_host="$(echo "${SQLSERVER_DATABASE_URL}" | sed -E 's|.*@([^:,]+)[,:]([0-9]+)/.*|\1|')"
  _ss_port="$(echo "${SQLSERVER_DATABASE_URL}" | sed -E 's|.*@[^:,]+[,:]([0-9]+)/.*|\1|')"
  _ss_pass="EdmontonLens123!"

  ss_query() {
    local sql="$1"
    sqlcmd -S "${_ss_host},${_ss_port}" -U sa -P "${_ss_pass}" \
      -d edmonton_lens -Q "${sql}" -h -1 -W 2>/dev/null | head -n1
  }

  if sqlcmd -S "${_ss_host},${_ss_port}" -U sa -P "${_ss_pass}" \
       -Q "SELECT 1" -h -1 >/dev/null 2>&1; then
    for table in "${TABLES[@]}"; do
      count="$(ss_query "SET NOCOUNT ON; SELECT COUNT(*) FROM [${table}]" 2>/dev/null || echo 0)"
      last_ts="$(ss_query "SET NOCOUNT ON; SELECT CONVERT(VARCHAR,MAX(ingested_at),120) FROM [${table}]" 2>/dev/null || echo "")"
      _print_row "${table}" "${count//[[:space:]]/}" "${last_ts//[[:space:]]/}"
    done
  else
    echo "  Could not connect to SQL Server at ${_ss_host}:${_ss_port} -- is docker compose up?"
    EXIT_CODE=1
  fi
fi

echo ""
echo "======================================================================"
if [[ "${EXIT_CODE}" -eq 0 ]]; then
  echo "All checks passed."
else
  echo "One or more checks raised warnings."
fi
exit "${EXIT_CODE}"
