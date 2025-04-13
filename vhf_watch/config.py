SDR_STREAMS = [
    # "http://fsdr.duckdns.org:8073/stream", # just for test
    "http://sv8rv.dyndns.org",  # Zakynthos, Greece (KiwiSDR)
    # "http://cyp.twrmon.net:8073/stream",  # Cyprus
    # "http://tangerkiwi.ddns.net/stream",  # Tanger
    # "http://37.10.74.235:8073//stream",  # Mallorca
]

MODEL_PATH = "/app/llama.cpp/models/mistral.gguf"
LLAMA_CPP_BINARY = "/app/llama.cpp/main"
WHISPER_MODEL = "base"  # Options: "tiny", "base", "small", "medium", "large"
LOG_FILE = "vhf_watch_log.jsonl"
CHUNK_SECONDS = 10
