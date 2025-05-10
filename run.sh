#!/usr/bin/env bash
set -euo pipefail

# ── 1) Locate project root ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 2) Ensure virtualenv exists ───────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "🌱 Creating virtualenv..."
  python3 -m venv .venv
fi

# ── 3) Activate & install deps ────────────────────────────────────────────────────────
source .venv/bin/activate
echo "🐍 Using Python at: $(which python)"
# pip install --upgrade pip
# pip install -r requirements.txt

# Ensure Python can find your src/ directory
export PYTHONPATH="$SCRIPT_DIR/src:${PYTHONPATH:-}"

# ── 4) Ensure punkt (and punkt_tab) are downloaded locally ────────────────────────────
NLTK_DATA_PATH="$SCRIPT_DIR/.venv/nltk_data"
export NLTK_DATA="$NLTK_DATA_PATH"

# only if the punkt directory is missing, download both punkt & punkt_tab
if [ ! -d "$NLTK_DATA_PATH/tokenizers/punkt" ]; then
  echo "📥 Downloading NLTK tokenizers (punkt & punkt_tab)…"
  python - <<PYCODE
import nltk, os
# add our custom nltk_data path
nltk.data.path.append(os.environ["NLTK_DATA"])
# download both punkt and punkt_tab
for pkg in ("punkt","punkt_tab"):
    nltk.download(pkg, download_dir=os.environ["NLTK_DATA"], quiet=True)
PYCODE
fi

# ── 5) Run the bot ────────────────────────────────────────────────────────────────────
python -m llm_telegram_bot.telegram.poller "$@"