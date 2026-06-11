#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COUNTRIES_FILE="${ROOT_DIR}/etl/config/geofabrik_countries.tsv"
RAW_DIR="${ROOT_DIR}/data/raw"
PROCESSED_DIR="${ROOT_DIR}/data/processed"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
PYTHON_SCRIPT="${ROOT_DIR}/etl/scripts/extract_food_pois.py"
SNAPSHOT_DATE="$(date +%Y-%m-%d)"
PARALLEL=1
FORCE=false
DRY_RUN=false
NO_PROGRESS=false
ESTIMATE_TOTAL=true
MAX_EXTRACT=""
COUNTRY_FILTER=""

usage() {
  cat <<'EOF'
Usage:
  ./etl.sh [options]

Options:
  --countries-file PATH     TSV file with columns: country<TAB>url.
  --country COUNTRY         Process only one country from the countries file.
  --raw-dir PATH            Directory for downloaded .osm.pbf files.
  --processed-dir PATH      Directory for generated Parquet files.
  --snapshot-date DATE      Snapshot date in YYYY-MM-DD format. Default: today.
  --parallel N              Number of country jobs to run in parallel. Default: 1.
  --force                   Download even if the raw .osm.pbf file already exists.
  --max-extract N           Stop each country extraction after N matched POIs.
  --no-progress             Disable Python tqdm progress bars.
  --no-estimate-total       Keep tqdm, but skip osmium fileinfo percentage estimate.
  --no-tqdm                 Alias for --no-estimate-total.
  --dry-run                 Print actions without downloading or extracting.
  -h, --help                Show this help.

Examples:
  ./etl.sh
  ./etl.sh --country germany --max-extract 100
  ./etl.sh --parallel 3
  ./etl.sh --force --country austria
EOF
}

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

quote_cmd() {
  printf '%q ' "$@"
  printf '\n'
}

run_cmd() {
  if [[ "${DRY_RUN}" == "true" ]]; then
    quote_cmd "$@"
    return 0
  fi
  "$@"
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf 'Required command not found: %s\n' "${command_name}" >&2
    exit 1
  fi
}

date_compact() {
  local value="$1"
  if [[ ! "${value}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    printf 'Invalid --snapshot-date. Expected YYYY-MM-DD, got: %s\n' "${value}" >&2
    exit 1
  fi
  printf '%s%s%s\n' "${value:2:2}" "${value:5:2}" "${value:8:2}"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --countries-file)
        COUNTRIES_FILE="$2"
        shift 2
        ;;
      --country)
        COUNTRY_FILTER="$2"
        shift 2
        ;;
      --raw-dir)
        RAW_DIR="$2"
        shift 2
        ;;
      --processed-dir)
        PROCESSED_DIR="$2"
        shift 2
        ;;
      --snapshot-date)
        SNAPSHOT_DATE="$2"
        shift 2
        ;;
      --parallel)
        PARALLEL="$2"
        shift 2
        ;;
      --force)
        FORCE=true
        shift
        ;;
      --max-extract|--max_extract)
        MAX_EXTRACT="$2"
        shift 2
        ;;
      --no-progress)
        NO_PROGRESS=true
        shift
        ;;
      --no-estimate-total|--no-tqdm)
        ESTIMATE_TOTAL=false
        shift
        ;;
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        printf 'Unknown option: %s\n' "$1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
}

validate_args() {
  date_compact "${SNAPSHOT_DATE}" >/dev/null

  if [[ ! "${PARALLEL}" =~ ^[0-9]+$ || "${PARALLEL}" -lt 1 ]]; then
    printf '--parallel must be a positive integer.\n' >&2
    exit 1
  fi

  if [[ -n "${MAX_EXTRACT}" && ! "${MAX_EXTRACT}" =~ ^[0-9]+$ ]]; then
    printf '--max-extract must be a positive integer.\n' >&2
    exit 1
  fi

  if [[ -n "${MAX_EXTRACT}" && "${MAX_EXTRACT}" -lt 1 ]]; then
    printf '--max-extract must be a positive integer.\n' >&2
    exit 1
  fi

  if [[ ! -f "${COUNTRIES_FILE}" ]]; then
    printf 'Countries file does not exist: %s\n' "${COUNTRIES_FILE}" >&2
    exit 1
  fi

  if [[ ! -x "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="python"
  fi

  if [[ "${DRY_RUN}" != "true" ]]; then
    require_command curl
    require_command "${PYTHON_BIN}"
  fi
}

download_pbf() {
  local country="$1"
  local url="$2"
  local raw_path="$3"

  mkdir -p "$(dirname "${raw_path}")"

  if [[ -f "${raw_path}" && "${FORCE}" != "true" ]]; then
    log "${country}: raw file already exists, skipping download: ${raw_path}"
    return 0
  fi

  local tmp_path="${raw_path}.tmp.$$"
  log "${country}: downloading ${url}"
  run_cmd curl --location --fail --show-error --progress-bar --output "${tmp_path}" "${url}"

  if [[ "${DRY_RUN}" != "true" ]]; then
    mv "${tmp_path}" "${raw_path}"
  fi
}

extract_country() {
  local country="$1"
  local raw_path="$2"
  local output_path="$3"

  mkdir -p "$(dirname "${output_path}")"

  local python_args=(
    "${PYTHON_BIN}"
    "${PYTHON_SCRIPT}"
    --input "${raw_path}"
    --output "${output_path}"
    --snapshot-date "${SNAPSHOT_DATE}"
    --categories restaurant
  )

  if [[ -n "${MAX_EXTRACT}" ]]; then
    python_args+=(--max-extract "${MAX_EXTRACT}")
  fi

  if [[ "${NO_PROGRESS}" == "true" ]]; then
    python_args+=(--no-progress)
  fi

  if [[ "${ESTIMATE_TOTAL}" != "true" ]]; then
    python_args+=(--no-estimate-total)
  fi

  log "${country}: extracting restaurants"
  run_cmd "${python_args[@]}"
}

process_country() {
  local country="$1"
  local url="$2"
  local compact_date
  compact_date="$(date_compact "${SNAPSHOT_DATE}")"

  local raw_path="${RAW_DIR}/${country}-${compact_date}.osm.pbf"
  local output_path="${PROCESSED_DIR}/food_pois_${country}_snapshot_${SNAPSHOT_DATE//-/}.parquet"

  log "${country}: start"
  download_pbf "${country}" "${url}" "${raw_path}"
  extract_country "${country}" "${raw_path}" "${output_path}"
  log "${country}: done"
}

load_countries() {
  local countries=()
  local line country url

  while IFS=$'\t' read -r country url; do
    [[ -z "${country}" ]] && continue
    [[ "${country}" =~ ^# ]] && continue
    if [[ -n "${COUNTRY_FILTER}" && "${country}" != "${COUNTRY_FILTER}" ]]; then
      continue
    fi
    countries+=("${country}"$'\t'"${url}")
  done < "${COUNTRIES_FILE}"

  if [[ "${#countries[@]}" -eq 0 ]]; then
    printf 'No countries selected from %s\n' "${COUNTRIES_FILE}" >&2
    exit 1
  fi

  printf '%s\n' "${countries[@]}"
}

run_sequential() {
  local spec country url
  while IFS=$'\t' read -r country url; do
    process_country "${country}" "${url}"
  done
}

run_parallel() {
  local failures=0
  local running=0
  local spec country url

  while IFS=$'\t' read -r country url; do
    process_country "${country}" "${url}" &
    running=$((running + 1))

    if [[ "${running}" -ge "${PARALLEL}" ]]; then
      if ! wait -n; then
        failures=$((failures + 1))
      fi
      running=$((running - 1))
    fi
  done

  while [[ "${running}" -gt 0 ]]; do
    if ! wait -n; then
      failures=$((failures + 1))
    fi
    running=$((running - 1))
  done

  if [[ "${failures}" -gt 0 ]]; then
    printf '%s country job(s) failed.\n' "${failures}" >&2
    exit 1
  fi
}

main() {
  parse_args "$@"
  validate_args

  mkdir -p "${RAW_DIR}" "${PROCESSED_DIR}"

  log "Countries file: ${COUNTRIES_FILE}"
  log "Snapshot date: ${SNAPSHOT_DATE}"
  log "Raw directory: ${RAW_DIR}"
  log "Processed directory: ${PROCESSED_DIR}"
  log "Parallel jobs: ${PARALLEL}"

  if [[ "${PARALLEL}" -eq 1 ]]; then
    load_countries | run_sequential
  else
    load_countries | run_parallel
  fi
}

main "$@"
