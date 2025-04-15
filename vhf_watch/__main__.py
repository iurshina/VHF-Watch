import datetime
import random
import time

from vhf_watch.analyzer.llm_analyzer import analyze_transcript
from vhf_watch.cli import parse_args
from vhf_watch.config import LOG_FILE, SDR_STREAMS
from vhf_watch.logger.log_writer import log_event
from vhf_watch.logger_config import setup_logger
from vhf_watch.recorder.streamer import Transcriber

logger = setup_logger(name=__name__)
transcriber = Transcriber()


def main():
    args = parse_args()
    logger.info("Starting VHF-Watch...")
    start_time = time.time()

    while True:
        current_stream = random.choice(SDR_STREAMS)
        timestamp = datetime.datetime.utcnow()

        audio_path = transcriber.capture_audio_chunk(current_stream, args.chunk)
        if audio_path and transcriber.is_speech_present(audio_path):
            transcript = transcriber.transcribe_chunk(audio_path)
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

        if args.duration > 0 and (time.time() - start_time) > args.duration * 60:
            logger.info("Reached duration limit. Exiting.")
            break

        time.sleep(2)


if __name__ == "__main__":
    main()
