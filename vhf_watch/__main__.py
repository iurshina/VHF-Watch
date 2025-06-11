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

def raw_to_wav(raw_path: str, wav_path: str, sample_rate: int = 16000) -> bool:
    """
    Converts a raw audio file to a WAV file.

    The raw audio data is expected to be mono, 16-bit PCM.

    Args:
        raw_path (str): Path to the input raw audio file.
        wav_path (str): Path to save the output WAV file.
        sample_rate (int, optional): Sample rate of the raw audio. Defaults to 16000.

    Returns:
        bool: True if conversion was successful, False otherwise.
    """
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
    # Audio data is written continuously to transcriber.audio_file by WebSocketTranscriber

def audio_processing_worker(args, stop_event: threading.Event):
    """
    Worker thread function that processes audio chunks from the transcriber.

    This function runs in a loop, taking audio data accumulated by the
    WebSocketTranscriber, converting it to WAV, detecting speech,
    transcribing, analyzing, and logging events. It includes error handling
    with a retry mechanism.

    Args:
        args: Command-line arguments (typically from argparse).
              Expected to have `args.debug` for debug logging.
        stop_event (threading.Event): Event to signal when the worker should stop.
    """
    retry_counter = 0
    max_retries = 5 # Maximum number of consecutive errors before exiting

    while not stop_event.is_set():
        try:
            # Check if the raw audio file from the transcriber exists
            if not os.path.exists(transcriber.audio_file):
                # Wait a bit if the file isn't there yet (e.g., stream just started)
                time.sleep(1)
                continue

            timestamp = datetime.datetime.utcnow()
            # Use the transcriber's current audio file as the source raw path
            raw_path = transcriber.audio_file
            # Define a unique WAV file path based on the timestamp
            wav_path = os.path.join(SAVE_DIR, f"{timestamp.strftime('%Y%m%d_%H%M%S')}.wav")

            # Convert the raw audio data to a proper WAV file
            if not raw_to_wav(raw_path, wav_path):
                logger.warning(f"Failed to convert {raw_path} to WAV. Skipping this chunk.")
                # Sleep briefly to avoid tight loop on persistent conversion failure
                time.sleep(1)
                continue

            # Perform speech detection on the WAV file
            if transcriber.is_speech_present(wav_path):
                logger.info(f"Speech detected in {wav_path}.")
                # Transcribe the audio chunk to text
                transcript = transcriber.transcribe_chunk(wav_path)

                if transcript.strip(): # Check if transcription is not empty
                    # Filter out repetitive junk often produced by Whisper on noise
                    if is_repetitive_junk(transcript):
                        logger.info(f"Filtered out repetitive numeric junk: {transcript}")
                        continue

                    logger.info(f"Saved non-junk audio to {wav_path}")

                    if args.debug:
                        logger.debug(f"Transcript: {transcript}")

                    # Analyze the transcript using the LLM
                    llm_response = analyze_transcript(transcript)
                    logger.info(f"Analysis: {llm_response}")
                    # Log the event (timestamp, transcript, analysis)
                    log_event(timestamp, transcript, llm_response, LOG_FILE)
                else:
                    logger.info(f"Whisper returned an empty transcription for {wav_path}.")
            else:
                logger.info(f"No significant audio detected in {wav_path}.")

            # If all processing is successful, reset the retry counter
            retry_counter = 0
        except Exception as e:
            retry_counter += 1
            logger.error(f"Audio processing error: {e} (Attempt {retry_counter}/{max_retries})")
            if retry_counter > max_retries:
                logger.error("Too many consecutive errors, exiting audio processing worker.")
                break # Exit the loop
            # Cool-down period before retrying
            time.sleep(5)

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
