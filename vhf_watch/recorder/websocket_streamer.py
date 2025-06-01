import wave
import json
import numpy as np
import webrtcvad
import whisper
import websocket

from vhf_watch.logger_config import setup_logger
from vhf_watch.recorder.speech_detector import SpeechDetector


class WebSocketTranscriber:
    def __init__(self, vad_aggressiveness=3, whisper_model="base"):
        self.logger = setup_logger(name=self.__class__.__name__)
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.model = whisper.load_model(whisper_model)
        self.speech_detector = SpeechDetector()
        self.failed_hosts = set()
        self.audio_file = "radio_audio_stream.raw"

    def is_audio_active(self, wav_path: str, threshold_db: float = -45.0) -> bool:
        try:
            with wave.open(wav_path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                if len(samples) == 0:
                    return False
                rms = np.sqrt(np.mean(samples ** 2))
                db = 20 * np.log10(rms / 32768.0 + 1e-6)
                self.logger.debug(f"RMS dB: {db:.2f}")
                return db > threshold_db
        except Exception:
            self.logger.error("Failed to analyze audio activity", exc_info=True)
            return False

    def is_speech_present(self, wav_path: str, use_silero: bool = True) -> bool:
        try:
            if use_silero:
                self.speech_detector.is_speech_present(wav_path=wav_path)

            with wave.open(wav_path, "rb") as wf:
                assert wf.getframerate() == 16000
                assert wf.getnchannels() == 1
                assert wf.getsampwidth() == 2

                frame_duration = 30
                frame_size = int(16000 * frame_duration / 1000) * 2
                speech_frames = 0

                while True:
                    frame = wf.readframes(frame_size // 2)
                    if len(frame) < frame_size:
                        break

                    frame_np = np.frombuffer(frame, dtype=np.int16)
                    energy = np.sqrt(np.mean(frame_np.astype(np.float32) ** 2))

                    if energy < 300:
                        continue

                    if self.vad.is_speech(frame, 16000):
                        speech_frames += 1
                        if speech_frames > 5:
                            return True
                return False
        except Exception:
            self.logger.error("VAD analysis failed", exc_info=True)
            return False

    def transcribe_chunk(self, wav_path: str) -> str:
        try:
            result = self.model.transcribe(wav_path)
            return result.get("text", "")
        except Exception:
            self.logger.error("Whisper transcription failed", exc_info=True)
            return ""

    def on_message(self, ws, message):
        if isinstance(message, bytes):
            self.logger.info(f"[+] Received {len(message)} bytes of audio data")
            with open(self.audio_file, "ab") as f:
                f.write(message)
        else:
            self.logger.debug(f"[i] Text message: {message}")

    def on_open(self, ws):
        self.logger.info("[*] WebSocket connected, tuning...")
        ws.send("SERVER DE CLIENT client=openwebrx.js type=receiver")

        ws.send(json.dumps({
            "type": "connectionproperties",
            "params": {"nr_enabled": True}
        }))

        ws.send(json.dumps({
            "type": "dspcontrol",
            "params": {"low_cut": -4000, "high_cut": 4000}
        }))

        ws.send(json.dumps({
            "type": "dspcontrol",
            "params": {"offset_freq": -2200000}
        }))

        ws.send(json.dumps({
            "type": "dspcontrol",
            "action": "start"
        }))

    def on_error(self, ws, error):
        self.logger.error(f"[!] WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.logger.info(f"[*] WebSocket closed: {close_status_code}, {close_msg}")

    def start_stream(self, ws_url: str):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.logger.info("[*] Connecting to radio stream...")
        ws.run_forever()
