from pathlib import Path

SDR_STREAMS = [
    # "http://fsdr.duckdns.org:8073", # just for test
    "http://sv8rv.dyndns.org",  # Zakynthos, Greece (KiwiSDR)
    "http://cyp.twrmon.net",  # Cyprus
    "http://tangerkiwi.ddns.net",  # Tanger
    "http://37.10.74.235",  # Mallorca
    # "http://mayzus.ddns.net",  # Tenerife
]

WEBSOCKRT_STREAM_URL = "ws://mayzus.ddns.net:8073/ws/"

MODEL_PATH = "llama.cpp/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
LLAMA_CPP_BINARY = "llama.cpp/build/bin/llama-cli"

BASE_DIR = Path.cwd()
FULL_MODEL_PATH = BASE_DIR / MODEL_PATH
FULL_LLAMA_CPP_BINARY = BASE_DIR / LLAMA_CPP_BINARY

WHISPER_MODEL = "base"  # Options: "tiny", "base", "small", "medium", "large"
LOG_FILE = "vhf_watch_log.jsonl"
CHUNK_SECONDS = 10
