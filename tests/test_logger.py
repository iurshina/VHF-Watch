import json
from datetime import datetime

from vhf_watch.logger.log_writer import log_event


def test_log_event(tmp_path):
    log_path = tmp_path / "log.jsonl"
    timestamp = datetime.utcnow()
    transcript = "Distress signal from Sea Spirit."
    llm_response = json.dumps({"call_for_help": True, "location": "Sea"})

    log_event(timestamp, transcript, llm_response, str(log_path))

    with open(log_path) as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["transcription"] == transcript
        assert json.loads(data["llm_output"])["location"] == "Sea"
