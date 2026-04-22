#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Virtual environment not found at .venv/bin/activate" >&2
  exit 1
fi

source .venv/bin/activate

provider="${SPEECH_PROVIDER:-gcp}"
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

if [[ "$provider" == "ollama" && -z "${OLLAMA_BASE_URL:-}" ]]; then
  cat >&2 <<'EOF'
OLLAMA_BASE_URL is required for Ollama mode, for example:

export SPEECH_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://your-ollama-host:11434"
export OLLAMA_MODEL="gemma4:default"
./run.sh
EOF
  exit 1
fi

python -m speech_to_text_app
