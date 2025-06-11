from pathlib import Path

WEBSOCKRT_STREAM_URL = "ws://mayzus.ddns.net:8073/ws/"

MODEL_PATH = "llama.cpp/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
LLAMA_CPP_BINARY = "llama.cpp/build/bin/llama-cli"

BASE_DIR = Path.cwd()
FULL_MODEL_PATH = BASE_DIR / MODEL_PATH
FULL_LLAMA_CPP_BINARY = BASE_DIR / LLAMA_CPP_BINARY

WHISPER_MODEL = "base"  # Options: "tiny", "base", "small", "medium", "large"
LOG_FILE = "vhf_watch_log.jsonl"
CHUNK_SECONDS = 10
