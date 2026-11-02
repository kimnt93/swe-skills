#!/usr/bin/env bash
# Infrastructure readiness + health probe for containers (needs only bash; no curl/wget/psql/redis-cli).
#
#   health.sh postgres,clickhouse,kafka          one-shot check, exit 0 only if every dependency is reachable
#   health.sh                                    check the dependencies named in $HEALTH_DEPS
#   health.sh --app                              also check this service's own HTTP endpoint (HTTP services)
#   health.sh --wait -- /app/service serve       startup gate: wait for the dependencies, then exec the command
#
# Dependencies: postgres | redis | clickhouse | kafka | s3 (aliases: rustfs, minio). Comma or space separated.
# Use it as the image ENTRYPOINT (`--wait --`) so a task never starts, crashes and restarts before its
# infrastructure is up, and as the Swarm/Compose healthcheck (`health.sh` or `health.sh --app`).
#
# Options:  --wait            retry until reachable or $HEALTH_WAIT_SECONDS (default 120) elapse, then exit 1
#           --app             include the service's own endpoint: http://127.0.0.1:${PORT:-3000}${HEALTH_APP_PATH:-/healthz}
#           --timeout SECONDS per-connection timeout (default $HEALTH_TIMEOUT_SECONDS or 3)
#           --interval SECONDS retry interval with --wait (default 2)
# Exit:     0 healthy · 1 a dependency is unreachable (or wait timed out) · 2 configuration error
#
# Level of check: reachability and protocol liveness only (TCP; Postgres SSLRequest; Redis PING with AUTH;
# ClickHouse /ping; S3 health path). It does not validate credentials (the application must fail closed on
# its own startup), but it REQUIRES every variable below, including passwords, to be present: a missing
# required variable is a configuration error (exit 2, no retry). Secret values are never printed.
#
# Variables (per dependency; `<NAME>_FILE` may supply any secret from a mounted file):
#   postgres    POSTGRES_HOST POSTGRES_PORT(5432) POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD[_FILE]
#   redis       REDIS_HOST REDIS_PORT(6379) REDIS_PASSWORD[_FILE]            (REDIS_USERNAME optional ACL user)
#   clickhouse  CLICKHOUSE_HOST CLICKHOUSE_HTTP_PORT(8123) CLICKHOUSE_USER CLICKHOUSE_PASSWORD[_FILE]
#   kafka       KAFKA_BOOTSTRAP_SERVERS (host:port,...; any one reachable) KAFKA_SECURITY_PROTOCOL(PLAINTEXT)
#               and, for SASL_*, KAFKA_SASL_USERNAME KAFKA_SASL_PASSWORD[_FILE]
#   s3          S3_ENDPOINT (http[s]://host:port) S3_BUCKET S3_ACCESS_KEY[_FILE] S3_SECRET_KEY[_FILE]
#               S3_HEALTH_PATH(/health)
set -u

timeout_s="${HEALTH_TIMEOUT_SECONDS:-3}"
interval_s=2
wait_mode=0
app_mode=0
deps_arg=""

while [ $# -gt 0 ]; do
  case "$1" in
    --wait) wait_mode=1 ;;
    --app) app_mode=1 ;;
    --timeout) timeout_s="${2:?--timeout needs seconds}"; shift ;;
    --interval) interval_s="${2:?--interval needs seconds}"; shift ;;
    --) shift; break ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    -*) echo "health: unknown option $1" >&2; exit 2 ;;
    *) deps_arg="${deps_arg:+$deps_arg,}$1" ;;
  esac
  shift
done

deps="${deps_arg:-${HEALTH_DEPS:-}}"
deps="$(printf '%s' "$deps" | tr ', ' '\n\n' | sed '/^$/d' | tr 'A-Z' 'a-z')"
[ "$app_mode" = 1 ] && deps="$(printf 'app\n%s' "$deps" | sed '/^$/d')"

say() { printf 'health: %s\n' "$*" >&2; }

# value of VAR, or the contents of the file named by VAR_FILE; empty if neither is set
secret() {
  local name="$1" file_var="${1}_FILE" v="${!1:-}"
  if [ -z "$v" ] && [ -n "${!file_var:-}" ]; then
    [ -r "${!file_var}" ] || { say "$file_var=${!file_var} is not readable"; return 2; }
    v="$(cat "${!file_var}")"
  fi
  printf '%s' "$v"
}

# fail the configuration (exit 2) unless every named variable is set (secrets: value or _FILE)
need() {
  local dep="$1"; shift; local var missing=""
  for var in "$@"; do
    case "$var" in
      *PASSWORD|*SECRET_KEY|*ACCESS_KEY|*TOKEN)
        local file_var="${var}_FILE"
        if [ -z "${!var:-}" ] && [ -n "${!file_var:-}" ] && [ ! -r "${!file_var}" ]; then
          missing="$missing $file_var (${!file_var} is not readable by uid $(id -u))"
        elif [ -z "$(secret "$var" 2>/dev/null)" ]; then
          missing="$missing $var or ${var}_FILE"
        fi ;;
      *) [ -n "${!var:-}" ] || missing="$missing $var" ;;
    esac
  done
  [ -z "$missing" ] || { say "$dep: configuration error, required:$missing"; return 2; }
}

# connect to host:port; fd 3 stays open for the caller. Runs inside a timeout-guarded subshell.
tcp() { exec 3<>"/dev/tcp/$1/$2"; }

with_timeout() { if command -v timeout >/dev/null 2>&1; then timeout "$timeout_s" "$@"; else "$@"; fi; }

# HTTP GET host port path -> echoes the status code (empty on failure)
http_status() {
  local host="$1" port="$2" path="$3"
  with_timeout bash -c '
    exec 3<>"/dev/tcp/$0/$1" || exit 1
    printf "GET %s HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n\r\n" "$2" "$0" >&3
    read -r line <&3 || exit 1
    set -- $line; printf "%s" "${2:-}"
  ' "$host" "$port" "$path" 2>/dev/null
}

split_hostport() { # "host:port" -> HP_HOST HP_PORT (default port $2)
  HP_HOST="${1%:*}"; HP_PORT="${1##*:}"; [ "$HP_HOST" = "$1" ] && { HP_HOST="$1"; HP_PORT="$2"; }
  HP_HOST="${HP_HOST#[}"; HP_HOST="${HP_HOST%]}"
}

url_hostport() { # http[s]://host[:port][/...] -> HP_HOST HP_PORT, HP_SCHEME
  local u="${1#*://}"; HP_SCHEME="${1%%://*}"; u="${u%%/*}"
  split_hostport "$u" "$([ "$HP_SCHEME" = https ] && echo 443 || echo 80)"
}

# ---- one function per dependency: configuration check (exit 2) then liveness (exit 1) ----

check_app() {
  local port="${PORT:-3000}" path="${HEALTH_APP_PATH:-/healthz}" code
  code="$(http_status 127.0.0.1 "$port" "$path")"
  case "$code" in 2??) return 0 ;; *) say "app: GET $path on :$port returned '${code:-no response}'"; return 1 ;; esac
}

check_postgres() {
  need postgres POSTGRES_HOST POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD || return 2
  local host="$POSTGRES_HOST" port="${POSTGRES_PORT:-5432}" reply
  # SSLRequest: a live Postgres answers one byte ('S' or 'N') without needing credentials.
  reply="$(with_timeout bash -c '
    exec 3<>"/dev/tcp/$0/$1" || exit 1
    printf "\000\000\000\010\004\322\026\057" >&3
    read -r -n1 c <&3 || exit 1; printf "%s" "$c"
  ' "$host" "$port" 2>/dev/null)"
  case "$reply" in S|N) return 0 ;; *) say "postgres: $host:$port did not answer the protocol probe"; return 1 ;; esac
}

check_redis() {
  need redis REDIS_HOST REDIS_PASSWORD || return 2
  local host="$REDIS_HOST" port="${REDIS_PORT:-6379}" user="${REDIS_USERNAME:-}" pass reply
  pass="$(secret REDIS_PASSWORD)"
  reply="$(with_timeout bash -c '
    exec 3<>"/dev/tcp/$0/$1" || exit 1
    pass="$2"; user="$3"
    if [ -n "$user" ]; then
      printf "*3\r\n\$4\r\nAUTH\r\n\$%s\r\n%s\r\n\$%s\r\n%s\r\n" "${#user}" "$user" "${#pass}" "$pass" >&3
    else
      printf "*2\r\n\$4\r\nAUTH\r\n\$%s\r\n%s\r\n" "${#pass}" "$pass" >&3
    fi
    read -r auth <&3 || exit 1
    case "$auth" in "-ERR"*|"-WRONGPASS"*|"-NOAUTH"*) printf "AUTHFAIL"; exit 0 ;; esac
    printf "*1\r\n\$4\r\nPING\r\n" >&3
    read -r pong <&3 || exit 1; printf "%s" "$pong"
  ' "$host" "$port" "$pass" "$user" 2>/dev/null)"
  case "$reply" in
    +PONG*) return 0 ;;
    AUTHFAIL) say "redis: $host:$port rejected the credentials"; return 1 ;;
    *) say "redis: $host:$port did not answer PING"; return 1 ;;
  esac
}

check_clickhouse() {
  need clickhouse CLICKHOUSE_HOST CLICKHOUSE_USER CLICKHOUSE_PASSWORD || return 2
  local code; code="$(http_status "$CLICKHOUSE_HOST" "${CLICKHOUSE_HTTP_PORT:-8123}" /ping)"
  [ "$code" = 200 ] || { say "clickhouse: $CLICKHOUSE_HOST:${CLICKHOUSE_HTTP_PORT:-8123}/ping returned '${code:-no response}'"; return 1; }
}

check_kafka() {
  need kafka KAFKA_BOOTSTRAP_SERVERS || return 2
  case "${KAFKA_SECURITY_PROTOCOL:-PLAINTEXT}" in
    SASL_*) need kafka KAFKA_SASL_USERNAME KAFKA_SASL_PASSWORD || return 2 ;;
  esac
  local entry
  for entry in $(printf '%s' "$KAFKA_BOOTSTRAP_SERVERS" | tr ',' ' '); do
    split_hostport "$entry" 9092
    if with_timeout bash -c 'exec 3<>"/dev/tcp/$0/$1"' "$HP_HOST" "$HP_PORT" 2>/dev/null; then return 0; fi
  done
  say "kafka: no bootstrap server reachable ($KAFKA_BOOTSTRAP_SERVERS)"; return 1
}

check_s3() {
  need s3 S3_ENDPOINT S3_BUCKET S3_ACCESS_KEY S3_SECRET_KEY || return 2
  url_hostport "$S3_ENDPOINT"
  local path="${S3_HEALTH_PATH:-/health}" code
  [ "$HP_SCHEME" = https ] && { with_timeout bash -c 'exec 3<>"/dev/tcp/$0/$1"' "$HP_HOST" "$HP_PORT" 2>/dev/null && return 0
                                 say "s3: $HP_HOST:$HP_PORT unreachable"; return 1; }
  code="$(http_status "$HP_HOST" "$HP_PORT" "$path")"
  case "$code" in 2??) return 0 ;; *) say "s3: GET $path on $HP_HOST:$HP_PORT returned '${code:-no response}'"; return 1 ;; esac
}

run_check() {
  case "$1" in
    app) check_app ;; postgres|postgresql|pg) check_postgres ;; redis) check_redis ;;
    clickhouse) check_clickhouse ;; kafka|redpanda) check_kafka ;;
    s3|rustfs|minio) check_s3 ;;
    *) say "unknown dependency '$1' (postgres, redis, clickhouse, kafka, s3)"; return 2 ;;
  esac
}

# ---- run ----
pending="$deps"
deadline=$(( $(date +%s) + ${HEALTH_WAIT_SECONDS:-120} ))
while :; do
  failed=""; config_error=0
  for dep in $pending; do
    run_check "$dep"; rc=$?
    case "$rc" in
      0) say "ok   $dep" ;;
      2) config_error=1; failed="$failed $dep" ;;
      *) failed="$failed $dep" ;;
    esac
  done
  [ "$config_error" = 1 ] && exit 2
  pending="$(printf '%s' "$failed" | tr ' ' '\n' | sed '/^$/d')"
  [ -z "$pending" ] && break
  if [ "$wait_mode" = 0 ]; then exit 1; fi
  if [ "$(date +%s)" -ge "$deadline" ]; then say "gave up waiting for:$(printf ' %s' $pending)"; exit 1; fi
  say "waiting for:$(printf ' %s' $pending)"
  sleep "$interval_s"
done

[ $# -gt 0 ] && exec "$@"
exit 0
