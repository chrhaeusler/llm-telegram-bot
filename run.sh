#!/bin/bash

# Set project root relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Export PYTHONPATH so Python can find the src/ directory
export PYTHONPATH="$SCRIPT_DIR/src"

# Ensure we're using the virtual environment
source .venv/bin/activate
which python

# Run the poller
python -m llm_telegram_bot.telegram.poller "$@"
