#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

venv_dir="${VIRTUAL_ENV_DIR:-.venv}"
activate_script="$venv_dir/bin/activate"

if [[ ! -f "$activate_script" ]]; then
  echo "Virtual environment not found at $activate_script" >&2
  exit 1
fi

source "$activate_script"

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

python -m speech_to_text_app
