import datetime
import os
import queue
import random
import threading
import time
import wave
from typing import Tuple

from vhf_watch.analyzer.llm_analyzer import analyze_transcript
from vhf_watch.cli import parse_args
from vhf_watch.config import LOG_FILE, WEBSOCKRT_STREAM_URL
from vhf_watch.logger.log_writer import log_event
from vhf_watch.logger_config import setup_logger
from vhf_watch.recorder.websocket_streamer import WebSocketTranscriber

logger = setup_logger(name=__name__)
transcriber = WebSocketTranscriber()
audio_queue: queue.Queue[Tuple[datetime.datetime, str]] = queue.Queue()

REPETITION_THRESHOLD = 5  # how many repeated tokens to consider it junk
SAVE_DIR = "captured_chunks"
os.makedirs(SAVE_DIR, exist_ok=True)

def is_repetitive_junk(transcript: str) -> bool:
    tokens = transcript.strip().split()
    return (
        len(tokens) > 0 and len(set(tokens)) <= 5 and tokens.count(tokens[0]) > REPETITION_THRESHOLD
    )

def raw_to_wav(raw_path: str, wav_path: str, sample_rate: int = 16000):
    try:
        with open(raw_path, 'rb') as raw_file:
            raw_data = raw_file.read()

        with wave.open(wav_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(raw_data)
        return True
    except Exception as e:
        logger.error(f"Failed to convert raw to wav: {e}")
        return False

def websocket_stream_worker(stream_url: str, stop_event):
    transcriber.start_stream(stream_url)
    # Audio data is written continuously to transcriber.audio_file

def audio_processing_worker(args, stop_event):
    while not stop_event.is_set():
        try:
            if not os.path.exists(transcriber.audio_file):
                time.sleep(1)
                continue

            timestamp = datetime.datetime.utcnow()
            raw_path = transcriber.audio_file
            wav_path = os.path.join(SAVE_DIR, f"{timestamp.strftime('%Y%m%d_%H%M%S')}.wav")

            if not raw_to_wav(raw_path, wav_path):
                continue

            if transcriber.is_speech_present(wav_path):
                transcript = transcriber.transcribe_chunk(wav_path)
                if transcript.strip():
                    if is_repetitive_junk(transcript):
                        logger.info(f"Filtered out repetitive numeric junk: {transcript}")
                        continue

                    logger.info(f"Saved non-junk audio to {wav_path}")

                    if args.debug:
                        logger.debug(f"Transcript: {transcript}")

                    llm_response = analyze_transcript(transcript)
                    logger.info(f"Analysis: {llm_response}")
                    log_event(timestamp, transcript, llm_response, LOG_FILE)
                else:
                    logger.info("Whisper returned an empty transcription.")
            else:
                logger.info("No significant audio detected.")
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            time.sleep(1)

def main():
    args = parse_args()
    logger.info("Starting VHF-Watch with WebSocket stream...")
    stop_event = threading.Event()

    stream_url = WEBSOCKRT_STREAM_URL 

    stream_thread = threading.Thread(
        target=websocket_stream_worker, args=(stream_url, stop_event), daemon=True
    )
    processing_thread = threading.Thread(
        target=audio_processing_worker, args=(args, stop_event), daemon=True
    )

    start_time = time.time()
    stream_thread.start()
    processing_thread.start()

    try:
        while True:
            if args.duration > 0 and (time.time() - start_time) > args.duration * 60:
                logger.info("Reached duration limit. Exiting.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")

    stop_event.set()
    stream_thread.join()
    processing_thread.join()

if __name__ == "__main__":
    main()
