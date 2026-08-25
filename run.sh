#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

show_usage() {
  cat <<'EOF'
Usage: ./run.sh [--provider <local|gcp|openai>] [audio-file] [options]

Starts the speech-to-text app with the local provider by default. When an
audio file is provided, converts it to a UTF-8 text file using Faster Whisper.

Provider overrides:
  ./run.sh --provider local
  ./run.sh test.m4a
  ./run.sh meeting.m4a --speaker-labels
  GOOGLE_CLOUD_PROJECT=project-id ./run.sh --provider gcp
  OPENAI_API_KEY=api-key ./run.sh --provider openai

Options:
  --provider <provider>  Select local, gcp, or openai (default: local).
  -o, --output <path>    Write file transcription to this path.
  --speaker-labels       Add optional local speaker labels and timestamps.
  --num-speakers <n>     Provide a known count; otherwise estimate it automatically.
  --force                Replace an existing output file.
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

if [[ "$(uname -s)" == "Darwin" ]]; then
  export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-1}"
fi

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
