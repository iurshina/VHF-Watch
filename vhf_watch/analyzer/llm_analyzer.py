import subprocess
import json
import re

from vhf_watch.config import MODEL_PATH, LLAMA_CPP_BINARY
from vhf_watch.logger_config import setup_logger

logger = setup_logger(name=__name__)

FALLBACK_KEYWORDS = [
    "mayday", "help", "rescue", "libyan coast guard", "frontex"
]


def analyze_transcript(transcript: str) -> dict:
    prompt = f"""
        You are monitoring marine distress communications. Analyze the following radio transcript.

        TRANSCRIPT:
        "{transcript}"

        Extract:
        - Calls for help
        - Mentions of "Libyan coast guard", "Frontex", or "rescue"
        - Any time or location mentioned
        - Any named actors (ship names, coast guards, etc.)

        Return the result in compact JSON format.
    """

    try:
        llama_cmd = [LLAMA_CPP_BINARY, "-m", MODEL_PATH, "-p", prompt, "-n", "200"]
        result = subprocess.run(llama_cmd, capture_output=True, text=True, timeout=60)
        return json.loads(result.stdout.strip())
    except Exception as e:
        logger.warning(f"LLM failed, falling back to regex: {e}")
        return fallback_analysis(transcript)


def fallback_analysis(transcript: str) -> dict:
    detected = [
        kw for kw in FALLBACK_KEYWORDS
        if re.search(rf"\b{re.escape(kw)}\b", transcript, re.IGNORECASE)
    ]
    if detected:
        logger.warning(f"LLM fallback triggered — matched keywords: {detected}")
    return {
        "call_for_help": any(
            kw in transcript.lower() for kw in ["mayday", "help", "rescue"]
        ),
        "keywords": detected,
        "llm_fallback": bool(detected)
    }
