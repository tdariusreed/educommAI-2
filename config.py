"""Settings. Override with environment variables."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("EDUCOMM_DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "educomm.db"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"

# Language model. Only ONE call is made per question (the final write-up), so a small model is fine.
#   LLM_MODE=auto -> use the model; if it is unreachable, fall back to a no-model answer built from sources
#   LLM_MODE=off  -> never call a model (zero extra RAM)
LLM_MODE = os.environ.get("LLM_MODE", "auto")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "ollama"))
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:3b")  # ~2 GB; use qwen2.5:1.5b on very tight machines
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "180"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "600"))  # caps generation time

# Retrieval
RESULTS_PER_QUERY = 4
SNIPPET_CHARS = 220
SEARCH_CACHE_TTL = 3600   # seconds; identical searches are served from memory
SEARCH_CACHE_MAX = 64
MAX_PARALLEL_SEARCHES = 3

# Public deployment: by default each visit gets a private random id that lives only in that browser session.
# Set EDUCOMM_URL_ID=1 to keep the id in the page URL instead (bookmark = same profile next time; anyone with the link sees it).
URL_ID = os.environ.get("EDUCOMM_URL_ID", "0") == "1"
