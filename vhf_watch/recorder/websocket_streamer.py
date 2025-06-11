import wave
import json
import numpy as np
import webrtcvad
import whisper
import websocket

from vhf_watch.logger_config import setup_logger
from vhf_watch.recorder.speech_detector import SpeechDetector


class WebSocketTranscriber:
    """
    Manages a WebSocket connection to a VHF radio stream (e.g., from an OpenWebRX instance),
    receives audio data, performs voice activity detection (VAD), and transcribes
    speech using Whisper.
    """
    def __init__(self, vad_aggressiveness: int = 3, whisper_model: str = "base"):
        """
        Initializes the WebSocketTranscriber.

        Args:
            vad_aggressiveness (int): Sets the aggressiveness of the WebRTC VAD.
                                      An integer between 0 (least aggressive) and 3 (most aggressive).
            whisper_model (str): The name of the Whisper model to use for transcription
                                 (e.g., "tiny", "base", "small").
        """
        self.logger = setup_logger(name=self.__class__.__name__)
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.model = whisper.load_model(whisper_model)
        self.speech_detector = SpeechDetector() # Uses Silero VAD + WebRTC VAD
        self.failed_hosts = set() # Not currently used, but could be for stream cycling
        self.audio_file = "radio_audio_stream.raw" # Path where raw audio data is accumulated

    def is_audio_active(self, wav_path: str, threshold_db: float = -45.0) -> bool:
        """
        Checks if the audio level in a WAV file exceeds a given RMS dB threshold.

        Note: This method is not actively used by the audio_processing_worker
        but can be a utility for general audio level checking.

        Args:
            wav_path (str): Path to the WAV audio file.
            threshold_db (float): RMS dB threshold for considering audio active.

        Returns:
            bool: True if audio level exceeds the threshold, False otherwise.
        """
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
        """
        Detects speech in a WAV file using primarily WebRTC VAD, with an option
        to also invoke the more comprehensive SpeechDetector (Silero+WebRTC).

        Args:
            wav_path (str): Path to the WAV audio file (16kHz, mono, 16-bit).
            use_silero (bool): If True, also utilizes the `SpeechDetector` class,
                               which combines Silero VAD and WebRTC VAD.
                               Note: The current implementation of this method calls
                               `self.speech_detector.is_speech_present` but its result
                               is not directly used to gate the subsequent WebRTC VAD logic.
                               This might be an area for future refinement.

        Returns:
            bool: True if speech is detected, False otherwise.
        """
        try:
            # TODO: Review the logic for `use_silero`. Currently, speech_detector.is_speech_present
            # is called, but its return value doesn't gate the VAD logic below.
            # It might be intended for logging or as a pre-check.
            if use_silero:
                # This call to speech_detector uses a combined Silero+WebRTC VAD.
                # Its result is not directly used below, but it runs the check.
                self.speech_detector.is_speech_present(wav_path=wav_path)

            # Primary VAD logic using WebRTC VAD on frames
            with wave.open(wav_path, "rb") as wf:
                if wf.getframerate() != 16000:
                    self.logger.warning(f"WAV file {wav_path} is not 16kHz, VAD may be inaccurate.")
                # Ensure basic WAV properties for VAD; consider raising error or returning False if not met.
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

    def on_message(self, ws: websocket.WebSocketApp, message: any):
        """
        Callback function triggered when a message is received over the WebSocket.

        If the message is bytes, it's assumed to be audio data and is appended
        to `self.audio_file`. Text messages are logged.

        Args:
            ws (websocket.WebSocketApp): The WebSocketApp instance.
            message (any): The received message (bytes or str).
        """
        if isinstance(message, bytes):
            # Audio data is typically received as binary frames
            self.logger.info(f"[+] Received {len(message)} bytes of audio data, appending to {self.audio_file}")
            with open(self.audio_file, "ab") as f:
                f.write(message)
        else:
            # Other messages (e.g., server status, JSON)
            self.logger.debug(f"[i] Text message from WebSocket: {message}")

    def on_open(self, ws: websocket.WebSocketApp):
        """
        Callback function triggered when the WebSocket connection is successfully opened.

        Sends initial configuration messages to the OpenWebRX server to set up
        the receiver and DSP parameters for VHF marine band reception.

        Args:
            ws (websocket.WebSocketApp): The WebSocketApp instance.
        """
        self.logger.info("[*] WebSocket connected, sending initial configuration messages...")
        # Example messages for an OpenWebRX server; may need adjustment for other stream types
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
        self.logger.info("[*] Initial configuration messages sent.")

    def on_error(self, ws: websocket.WebSocketApp, error: Exception):
        """
        Callback function triggered when a WebSocket error occurs.

        Args:
            ws (websocket.WebSocketApp): The WebSocketApp instance.
            error (Exception): The error object.
        """
        self.logger.error(f"[!] WebSocket error: {error}")

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str):
        """
        Callback function triggered when the WebSocket connection is closed.

        Args:
            ws (websocket.WebSocketApp): The WebSocketApp instance.
            close_status_code (int): The status code for closure.
            close_msg (str): The close message.
        """
        self.logger.info(f"[*] WebSocket closed. Status: {close_status_code}, Message: '{close_msg}'")

    def start_stream(self, ws_url: str):
        """
        Starts the WebSocket connection and runs it indefinitely.

        Initializes and runs the WebSocketApp, connecting to the specified URL
        and using the defined callbacks (`on_open`, `on_message`, etc.).

        Args:
            ws_url (str): The URL of the WebSocket audio stream.
        """
        websocket.enableTrace(False) # Set to True for detailed WebSocket tracing
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.logger.info("[*] Connecting to radio stream...")
        ws.run_forever()
