#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

show_usage() {
  cat <<'EOF'
Usage: ./run.sh [--provider <local|gcp|openai>] [--help]

Starts the speech-to-text app with the local provider by default.

Provider overrides:
  ./run.sh --provider local
  GOOGLE_CLOUD_PROJECT=project-id ./run.sh --provider gcp
  OPENAI_API_KEY=api-key ./run.sh --provider openai

Options:
  --provider <provider>  Select local, gcp, or openai (default: local).
  -h, --help             Show this usage information and exit.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  show_usage
  exit 0
fi

provider="local"
if [[ "${1:-}" == "--provider" ]]; then
  if [[ $# -lt 2 ]]; then
    echo "--provider requires local, gcp, or openai." >&2
    exit 2
  fi
  provider="$2"
  shift 2
elif [[ "${1:-}" == --provider=* ]]; then
  provider="${1#*=}"
  shift
fi

if [[ "$provider" != "local" && "$provider" != "gcp" && "$provider" != "openai" ]]; then
  echo "Unknown provider: $provider. Expected local, gcp, or openai." >&2
  exit 2
fi

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Virtual environment not found at .venv/bin/activate" >&2
  exit 1
fi

source .venv/bin/activate

export SPEECH_PROVIDER="$provider"

if [[ "$provider" == "gcp" && -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
  cat >&2 <<'EOF'
Project ID is required. Set GOOGLE_CLOUD_PROJECT first, for example:

export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
./run.sh

Or set SPEECH_PROVIDER=openai and OPENAI_API_KEY for OpenAI mode.
EOF
  exit 1
fi

python -m speech_to_text_app "$@"
