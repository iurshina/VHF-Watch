import os

from pydub import AudioSegment

from vhf_watch.logger_config import setup_logger
from vhf_watch.recorder.streamer import Transcriber

logger = setup_logger(name="test_mayday")
recorder = Transcriber()


def convert_mp3_to_wav(mp3_path: str, wav_path: str = None) -> str:
    audio = AudioSegment.from_mp3(mp3_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    if wav_path is None:
        wav_path = mp3_path.replace(".mp3", "_16k.wav")
    audio.export(wav_path, format="wav")
    return wav_path


def test_mayday_audio():
    # timestamp = datetime.datetime.utcnow()
    mp3_path = "tests/data/38382-20230617-2339.mp3"
    wav_path = convert_mp3_to_wav(mp3_path)

    logger.info(f"Converted to: {wav_path}")

    if not os.path.exists(wav_path):
        logger.error("Failed to convert MP3 to WAV.")
        return

    if recorder.is_speech_present(wav_path):
        logger.info("Speech detected in audio.")

        # transcript = transcribe_chunk(wav_path)
        # print("\n--- Transcript ---")
        # print(transcript)

        # if transcript.strip():
        #     analysis = analyze_transcript(transcript)
        #     print("\n--- Analysis ---")
        #     print(analysis)
        #     log_event(timestamp, transcript, analysis, LOG_FILE)
        # else:
        #     logger.warning("Transcription was empty.")
    else:
        logger.warning("No speech detected.")


if __name__ == "__main__":
    test_mayday_audio()
