import glob
import os
import re
import shutil
import socket
import tempfile
import wave
from subprocess import CalledProcessError, run

import numpy as np
import webrtcvad
import whisper

from vhf_watch.logger_config import setup_logger


class Transcriber:
    def __init__(self, vad_aggressiveness=3, whisper_model="base"):
        self.logger = setup_logger(name=self.__class__.__name__)
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.model = whisper.load_model(whisper_model)
        self.failed_hosts = set()

    def sanitize_kiwi_host(self, kiwi_host: str) -> str:
        host = re.sub(r"^https?://", "", kiwi_host)
        return host.split("/")[0]

    def is_kiwi_host_reachable(self, host: str, port: int = 8073, timeout: float = 2.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def capture_audio_chunk(self, kiwi_host: str, chunk_duration: int) -> str:
        kiwi_host = self.sanitize_kiwi_host(kiwi_host)

        if kiwi_host in self.failed_hosts or not self.is_kiwi_host_reachable(kiwi_host):
            self.failed_hosts.add(kiwi_host)
            self.logger.error(f"Kiwi host is not reachable: {kiwi_host}")
            return ""

        self.logger.info(f"Connecting to KiwiSDR: {kiwi_host}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            kiwirecorder_cmd = [
                "python3",
                "kiwiclient/kiwirecorder.py",
                "-s",
                kiwi_host.split(":")[0],
                "-p",
                kiwi_host.split(":")[1] if ":" in kiwi_host else "8073",
                "-f",
                "156.800",  #
                "-m",
                "nbfm",
                "-L",
                "0",
                "-r",
                "16000",  # resample
                "--dir",
                tmp_dir,
                "--station",
                "vhf_watch",
                "--tlimit",
                str(chunk_duration),
            ]

            try:
                run(kiwirecorder_cmd, stdout=None, stderr=None, check=True)
                matches = glob.glob(os.path.join(tmp_dir, "*.wav"))
                if matches:
                    src_path = matches[0]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as dst:
                        shutil.copyfile(src_path, dst.name)
                        return dst.name
                else:
                    self.logger.error("No WAV file generated by kiwirecorder.py")
                    self.failed_hosts.add(kiwi_host)
                    return ""
            except CalledProcessError:
                self.logger.error(f"kiwirecorder.py error while capturing from {kiwi_host}")
                self.failed_hosts.add(kiwi_host)
                return ""
            except Exception:
                self.logger.error("Failed to capture audio chunk", exc_info=True)
                self.failed_hosts.add(kiwi_host)
                return ""

    def is_audio_active(self, wav_path: str, threshold_db: float = -45.0) -> bool:
        try:
            with wave.open(wav_path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                if len(samples) == 0:
                    return False
                rms = np.sqrt(np.mean(samples**2))
                db = 20 * np.log10(rms / 32768.0 + 1e-6)
                self.logger.debug(f"RMS dB: {db:.2f}")
                return db > threshold_db
        except Exception:
            self.logger.error("Failed to analyze audio activity", exc_info=True)
            return False

    def is_speech_present(self, wav_path: str) -> bool:
        try:
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

                    if energy < 200:
                        continue

                    if self.vad.is_speech(frame, 16000):
                        speech_frames += 1
                        if speech_frames > 3:
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
