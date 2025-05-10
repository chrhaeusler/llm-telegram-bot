#!/usr/bin/env bash
set -euo pipefail

# ── 1) Locate project root ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 2) Ensure virtualenv exists ────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "🌱 Creating virtualenv..."
  python3 -m venv .venv
fi

# ── 3) Activate & install deps ─────────────────────────────────────────────
source .venv/bin/activate
echo "🐍 Using Python at: $(which python)"
# pip install --upgrade pip
# pip install -r requirements.txt

# Ensure Python can find your src/ directory
export PYTHONPATH="$SCRIPT_DIR/src:${PYTHONPATH:-}"

# ── 4) Ensure punkt and punkt_tab are downloaded locally ───────────────────────────────────
NLTK_DATA_PATH="$SCRIPT_DIR/.venv/nltk_data"
export NLTK_DATA="$NLTK_DATA_PATH"

# downloads punkt if missing
if [ ! -f "$NLTK_DATA_PATH/tokenizers/punkt/english.pickle" ]; then
  echo "📥 Downloading NLTK punkt tokenizer..."
  python - <<PYCODE
import nltk, os
nltk.data.path.append(os.environ["NLTK_DATA"])
nltk.download("punkt", download_dir=os.environ["NLTK_DATA"], quiet=True)
PYCODE
fi

# download punkt_tab if missing
if [ ! -f "$NLTK_DATA_PATH/tokenizers/punkt_tab/english.pickle" ]; then
  echo "📥 Downloading NLTK punkt tokenizer..."
  python - <<PYCODE
import nltk, os
nltk.data.path.append(os.environ["NLTK_DATA"])
nltk.download("punkt_tab", download_dir=os.environ["NLTK_DATA"], quiet=True)
PYCODE
fi

# ── 5) Run the bot ───────────────────────────────────────────────────────────
python -m llm_telegram_bot.telegram.poller "$@"