#!/usr/bin/env bash
# Deploy or update VectCutAPI with Docker Compose v2.
# Usage:
#   ./scripts/deploy.sh         # production stack, pull and restart
#   ./scripts/deploy.sh --build # rebuild and start
#   ./scripts/deploy.sh --prod  # production stack
#   ./scripts/deploy.sh --dev   # development api only
#   ./scripts/deploy.sh --down  # stop and remove services

set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: ./scripts/deploy.sh [--build] [--prod|--dev] [--down]

Options:
  --build   Rebuild images before starting services.
  --prod    Use the production stack: docker-compose.yml plus production profile.
  --dev     Use the default Compose files and start only the api service.
  --down    Stop and remove services instead of starting them.
            Cannot be combined with --build.
  -h, --help
            Show this help text.
USAGE
}

die_usage() {
    echo "Error: $1" >&2
    usage >&2
    exit 1
}

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(CDPATH= cd -- "${script_dir}/.." && pwd -P)"

mode="prod"
mode_set=""
action="up"
build_args=()
build_requested=false

set_mode() {
    local requested_mode="$1"

    if [[ -n "$mode_set" ]]; then
        if [[ "$mode_set" == "$requested_mode" ]]; then
            die_usage "mode already specified: --${requested_mode}"
        fi
        die_usage "--prod and --dev cannot be used together."
    fi

    mode="$requested_mode"
    mode_set="$requested_mode"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build)
            if [[ "$action" == "down" ]]; then
                die_usage "--build cannot be combined with --down because down does not build."
            fi
            build_args=(--build)
            build_requested=true
            shift
            ;;
        --prod)
            set_mode "prod"
            shift
            ;;
        --dev)
            set_mode "dev"
            shift
            ;;
        --down)
            if [[ "$build_requested" == "true" ]]; then
                die_usage "--build cannot be combined with --down because down does not build."
            fi
            action="down"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

cd "$repo_root"

compose=(docker compose)
services=()
log_services=(api)

if [[ "$mode" == "prod" ]]; then
    compose=(docker compose -f docker-compose.yml --profile production)
    log_services=(api nginx)
else
    services=(api)
fi

compose_run() {
    COMPOSE_PROFILES= "${compose[@]}" "$@"
}

preflight_prod_auth() {
    local htpasswd_path="${repo_root}/docker/ssl/.htpasswd"

    if [[ -s "$htpasswd_path" ]]; then
        return 0
    fi

    cat >&2 <<'EOF'
Error: production Basic Auth is enabled; docker/ssl/.htpasswd must be a file that exists and is not empty.
Create it before starting production nginx:

  mkdir -p docker/ssl
  htpasswd -c docker/ssl/.htpasswd admin

Install htpasswd with apache2-utils (Debian/Ubuntu) or httpd-tools (RHEL/CentOS).
EOF
    exit 1
}

if [[ "$action" == "down" ]]; then
    echo "Stopping services ..."
    compose_run down
    exit 0
fi

if [[ "$mode" == "prod" ]]; then
    preflight_prod_auth
fi

container_status() {
    local container_name="$1"
    docker inspect --format '{{.State.Status}}' "$container_name" 2>/dev/null || true
}

api_health_status() {
    docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' vectcut-api 2>/dev/null || true
}

prod_fallback_health_ok() {
    [[ "$(api_health_status)" == "healthy" ]] && [[ "$(container_status vectcut-nginx)" == "running" ]]
}

wait_for_health() {
    local i

    if [[ "$mode" == "prod" ]]; then
        echo "Waiting for production health check via nginx ..."
        for i in {1..12}; do
            if curl -kfsS https://localhost/health >/dev/null 2>&1; then
                echo "Health check passed via nginx."
                return 0
            fi
            sleep 5
        done

        if prod_fallback_health_ok; then
            echo "HTTPS health check failed, container-level fallback passed."
            return 0
        fi

        return 1
    fi

    echo "Waiting for development health check ..."
    for i in {1..12}; do
        if curl -fsS http://localhost:9001/health >/dev/null 2>&1; then
            echo "Health check passed."
            return 0
        fi
        sleep 5
    done

    return 1
}

echo "Pulling latest code ..."
git pull --ff-only

echo "Building and starting services ..."
compose_run up -d "${build_args[@]}" "${services[@]}"

if wait_for_health; then
    compose_run ps
    exit 0
fi

echo "Health check timed out. Recent logs:" >&2
compose_run logs --tail=50 "${log_services[@]}" >&2
exit 1
