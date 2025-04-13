import json
from datetime import datetime


def log_event(
    timestamp: datetime, transcript: str, llm_response: str, log_file: str
) -> None:
    log_entry = {
        "timestamp": timestamp.isoformat(),
        "transcription": transcript,
        "llm_output": llm_response,
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"[ERROR] Failed to write log entry: {e}")
