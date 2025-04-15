import datetime
import queue
import random
import threading
import time
from typing import Tuple

from vhf_watch.analyzer.llm_analyzer import analyze_transcript
from vhf_watch.cli import parse_args
from vhf_watch.config import LOG_FILE, SDR_STREAMS
from vhf_watch.logger.log_writer import log_event
from vhf_watch.logger_config import setup_logger
from vhf_watch.recorder.streamer import Transcriber

logger = setup_logger(name=__name__)
recorder = Transcriber()
audio_queue: queue.Queue[Tuple[datetime.datetime, str]] = queue.Queue()


def audio_capture_worker(duration, stop_event):
    while not stop_event.is_set():
        current_stream = random.choice(SDR_STREAMS)
        audio_path = recorder.capture_audio_chunk(current_stream, duration)
        if audio_path:
            audio_queue.put((datetime.datetime.utcnow(), audio_path))


def audio_processing_worker(args, stop_event):
    while not stop_event.is_set() or not audio_queue.empty():
        try:
            timestamp, audio_path = audio_queue.get(timeout=1)
        except queue.Empty:
            continue

        if recorder.is_speech_present(audio_path):
            transcript = recorder.transcribe_chunk(audio_path)
            if transcript.strip():
                if args.debug:
                    logger.debug(f"Transcript: {transcript}")
                llm_response = analyze_transcript(transcript)
                logger.info(f"Analysis: {llm_response}")
                log_event(timestamp, transcript, llm_response, LOG_FILE)
            else:
                logger.info("Whisper returned an empty transcription.")
        else:
            logger.info("No significant audio detected.")


def main():
    args = parse_args()
    logger.info("Starting VHF-Watch...")
    stop_event = threading.Event()

    # TODO: we'll do better, in the future, I promise :)
    capture_thread = threading.Thread(
        target=audio_capture_worker, args=(args.chunk, stop_event), daemon=True
    )
    processing_thread = threading.Thread(
        target=audio_processing_worker, args=(args, stop_event), daemon=True
    )

    start_time = time.time()
    capture_thread.start()
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
    capture_thread.join()
    processing_thread.join()


if __name__ == "__main__":
    main()
