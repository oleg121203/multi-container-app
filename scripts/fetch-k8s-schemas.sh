#!/usr/bin/env bash
set -euo pipefail

# Fetch Kubernetes JSON Schemas into infra/k8s/schemas for offline validation
# Usage:
#   ./scripts/fetch-k8s-schemas.sh [SCHEMA_TAG]
# Examples of SCHEMA_TAG: v1.30.0, v1.29.0 (matches https://github.com/yannh/kubernetes-json-schema/tags)

REQUESTED_VERSION="${1:-auto}"
SCHEMAS_DIR="infra/k8s/schemas"

echo "[kube-schemas] Preparing directory: ${SCHEMAS_DIR}"
mkdir -p "${SCHEMAS_DIR}"

echo "[kube-schemas] Clearing old schemas (if any)"
rm -rf "${SCHEMAS_DIR:?}/"*

download_and_extract_master() {
	TMPDIR=$(mktemp -d)
	ARCHIVE_URL="https://github.com/yannh/kubernetes-json-schema/archive/refs/heads/master.tar.gz"
	echo "[kube-schemas] Downloading ${ARCHIVE_URL}"
	curl -fsSL "${ARCHIVE_URL}" | tar -xz -C "${TMPDIR}"
	# Find extracted root folder
	ROOT_DIR=$(find "${TMPDIR}" -maxdepth 1 -type d -name 'kubernetes-json-schema-*' | head -n1)
	if [ -z "${ROOT_DIR:-}" ]; then
		echo "[kube-schemas] ERROR: Unable to locate extracted directory"
		exit 2
	fi
	echo "[kube-schemas] Extracted to ${ROOT_DIR}"

	# If explicit version requested, try to use that folder first
	if [ "${REQUESTED_VERSION}" != "auto" ]; then
		for variant in "${REQUESTED_VERSION}-standalone-strict" "${REQUESTED_VERSION}-standalone" "${REQUESTED_VERSION}"; do
			CAND="${ROOT_DIR}/${variant}"
			if [ -d "${CAND}" ]; then
				echo "[kube-schemas] Using schemas from ${variant}"
				rsync -a --delete "${CAND}/" "${SCHEMAS_DIR}/"
				return 0
			fi
		done
		echo "[kube-schemas] WARNING: Requested version ${REQUESTED_VERSION} not found, falling back to latest available."
	fi

	# Auto-pick the latest '*-standalone-strict' if available, then '*-standalone', then plain 'v*'
	pick_and_copy_latest "${ROOT_DIR}" "*-standalone-strict" && return 0
	pick_and_copy_latest "${ROOT_DIR}" "*-standalone" && return 0
	pick_and_copy_latest "${ROOT_DIR}" "v*" && return 0

	echo "[kube-schemas] ERROR: No schema directories found"
	exit 3
}

pick_and_copy_latest() {
	local base="$1"
	local pattern="$2"
	mapfile -t dirs < <(find "${base}" -maxdepth 1 -type d -name "${pattern}" -printf '%f\n' 2>/dev/null | sort -rV 2>/dev/null)
	if [ ${#dirs[@]} -eq 0 ]; then
		# macOS/BSD fallback without -printf and -V
		dirs=( $(find "${base}" -maxdepth 1 -type d -name "${pattern}" | sed 's#.*/##' | sort -r) )
	fi
	if [ ${#dirs[@]} -eq 0 ]; then
		return 1
	fi
	local latest="${dirs[0]}"
	echo "[kube-schemas] Selected ${latest}"
	rsync -a --delete "${base}/${latest}/" "${SCHEMAS_DIR}/"
}

download_and_extract_master

COUNT=$(find "${SCHEMAS_DIR}" -type f -name '*.json' | wc -l | tr -d ' ')
echo "[kube-schemas] Prepared ${COUNT} schema files into ${SCHEMAS_DIR}"
echo "[kube-schemas] Done."
