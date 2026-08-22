#!/usr/bin/env bash
# Idempotent Cloud Agent install for auto-coder.
# Creates an isolated virtualenv (avoids conflicts with Debian-managed system
# Python packages), installs runtime dependencies plus the package in editable
# mode, and exposes the console scripts on PATH via /usr/local/bin symlinks.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV="${AUTOCODER_VENV:-$HOME/autocoder-venv}"

# System libraries required by some Python deps (cairosvg -> libcairo,
# pdf2image -> poppler, pydub/audio -> ffmpeg). apt-get install is idempotent.
if command -v apt-get >/dev/null 2>&1; then
  SUDO=""
  if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi
  $SUDO apt-get update -qq || true
  $SUDO apt-get install -y -qq --no-install-recommends \
    python3-venv python3.12-venv \
    libcairo2 libcairo2-dev poppler-utils ffmpeg pkg-config || true
fi

# Create the virtualenv if it does not already exist.
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi

# Note: setuptools is intentionally NOT upgraded here; requirements.txt pins it
# to <81 because autocoder imports the removed pkg_resources API.
"$VENV/bin/python" -m pip install --upgrade pip wheel
"$VENV/bin/pip" install -r requirements.txt
"$VENV/bin/pip" install -e .

# Developer tooling used by the repo's test scripts (scripts/run_test.sh,
# pytest.ini) but not part of the runtime requirements.
"$VENV/bin/pip" install pytest

# Expose the CLI entry points on PATH without shell-profile mutation.
SCRIPTS=(
  auto-coder auto-coder.core chat-auto-coder auto-coder.chat
  auto-coder-serve auto-coder.serve auto-coder.rag
  auto-coder.run auto-coder.cli
)
if [ -w /usr/local/bin ] || command -v sudo >/dev/null 2>&1; then
  LN_SUDO=""
  if [ ! -w /usr/local/bin ]; then LN_SUDO="sudo"; fi
  for s in "${SCRIPTS[@]}"; do
    if [ -x "$VENV/bin/$s" ]; then
      $LN_SUDO ln -sf "$VENV/bin/$s" "/usr/local/bin/$s"
    fi
  done
fi

echo "auto-coder install complete: $("$VENV/bin/pip" show auto-coder 2>/dev/null | awk '/^Version:/{print $2}')"
