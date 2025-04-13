import argparse

from vhf_watch.config import CHUNK_SECONDS


def parse_args():
    parser = argparse.ArgumentParser(
        description="VHF-Watch: Monitor VHF marine distress radio streams with Whisper + LLM"
    )
    parser.add_argument("--debug", action="store_true", help="Print raw transcripts to terminal")
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Run for N minutes and exit (0 = run forever)",
    )
    parser.add_argument(
        "--chunk",
        type=int,
        default=CHUNK_SECONDS,
        help="Chunk length in seconds for audio recording (default: %(default)s)",
    )
    return parser.parse_args()
