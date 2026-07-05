#!/usr/bin/env bash
# Back up the persistent Docker volumes used by VectCutAPI.
# Usage: ./scripts/backup.sh [backup_dir]
# Default backup directory: ./backup

set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: ./scripts/backup.sh [backup_dir]

Back up these Docker volumes:
  vectcutapi_template_data
  vectcutapi_template_config_data
  vectcutapi_generated_data

If backup_dir is omitted, ./backup is used.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

if [[ $# -gt 1 ]]; then
    echo "Error: too many arguments." >&2
    usage >&2
    exit 1
fi

backup_dir="${1:-./backup}"
timestamp="$(date +%Y%m%d-%H%M%S)"

volume_specs=(
    "template_data:vectcutapi_template_data"
    "template_config_data:vectcutapi_template_config_data"
    "generated_data:vectcutapi_generated_data"
)

is_windows_shell() {
    case "$(uname -s 2>/dev/null || true)" in
        MINGW*|MSYS*|CYGWIN*) return 0 ;;
        *) return 1 ;;
    esac
}

docker_cli() {
    if is_windows_shell; then
        MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker "$@"
    else
        docker "$@"
    fi
}

missing_volumes=()
for spec in "${volume_specs[@]}"; do
    volume_name="${spec#*:}"
    if ! docker_cli volume inspect "$volume_name" >/dev/null 2>&1; then
        missing_volumes+=("$volume_name")
    fi
done

if [[ ${#missing_volumes[@]} -gt 0 ]]; then
    echo "Error: required Docker volume(s) are missing or inaccessible:" >&2
    for volume_name in "${missing_volumes[@]}"; do
        echo "  - ${volume_name}" >&2
    done
    echo "No backup archives were created." >&2
    exit 1
fi

mkdir -p -- "$backup_dir"
backup_dir_abs="$(CDPATH= cd -- "$backup_dir" && pwd -P)"

echo "Starting backup to ${backup_dir_abs} ..."

for spec in "${volume_specs[@]}"; do
    archive_name="${spec%%:*}"
    volume_name="${spec#*:}"
    archive_file="${archive_name}-${timestamp}.tar.gz"
    archive_path="${backup_dir_abs}/${archive_file}"
    tmp_archive="${archive_path}.tmp"

    echo "Backing up ${volume_name} to ${archive_path}"
    if ! docker_cli run --rm \
        -v "${volume_name}:/data:ro" \
        alpine tar czf - -C /data . > "$tmp_archive"; then
        rm -f -- "$tmp_archive"
        echo "Error: failed to back up ${volume_name}." >&2
        exit 1
    fi

    mv -- "$tmp_archive" "$archive_path"

    size="$(du -h -- "$archive_path" | cut -f1)"
    echo "  Wrote ${archive_path} (${size})"
done

echo
echo "Backup complete:"
ls -lh -- "${backup_dir_abs}"/*-"${timestamp}".tar.gz
