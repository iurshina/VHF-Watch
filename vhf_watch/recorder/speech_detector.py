import numpy as np
import torch
import torchaudio
import webrtcvad
import os
import urllib.request
from vhf_watch.logger_config import setup_logger

logger = setup_logger(__name__)

# Define the local directory for the Silero VAD model
SILERO_VAD_DIR = "./silero-vad"
# Define the files required for the Silero VAD model
SILERO_MODEL_FILES = ["hubconf.py", "silero_vad.onnx", "utils_vad.py"]
# Define the base URL for downloading the Silero VAD model files
SILERO_REPO_URL = "https://raw.githubusercontent.com/snakers4/silero-vad/master/"


class SpeechDetector:
    """
    Detects speech in audio files using a combination of Silero VAD and WebRTC VAD.

    The Silero VAD model files are automatically downloaded if not found locally.
    """
    def __init__(self):
        """
        Initializes the SpeechDetector.

        This involves ensuring the Silero VAD model is present (downloading if necessary)
        and then loading both the Silero VAD model and initializing the WebRTC VAD.
        """
        self._ensure_silero_model_present()

        # Load Silero VAD model from local directory
        # trust_repo=True is required when loading from a local directory that isn't a git repo
        self.vad_model, self.utils = torch.hub.load(
            repo_or_dir=SILERO_VAD_DIR,
            model='silero_vad',
            source='local',
            trust_repo=True
        )
        (self.get_speech_ts, self.save_audio, self.read_audio, _, _) = self.utils

        # Initialize WebRTC VAD with the most aggressive mode (3)
        self.webrtc_vad = webrtcvad.Vad(3)

    def is_speech_present(self, wav_path: str) -> bool:
        """
        Checks for the presence of speech in a given WAV audio file.

        Combines results from both Silero VAD and WebRTC VAD for improved accuracy.
        Speech is considered present if both VADs detect significant speech activity.

        Args:
            wav_path (str): Path to the WAV audio file (must be 16kHz mono).

        Returns:
            bool: True if speech is detected, False otherwise.
        """
        try:
            # --- Silero VAD ---
            # Read audio file using Silero's utility function
            audio = self.read_audio(wav_path, sampling_rate=16000)

            speech_ts = self.get_speech_ts(
                audio,
                self.vad_model,
                sampling_rate=16000,
                threshold=0.85,
                min_speech_duration_ms=800,
                min_silence_duration_ms=1000,
            )

            def rms(t):
                return torch.sqrt(torch.mean(t.float() ** 2)).item()

            speech_ts = [ts for ts in speech_ts if rms(audio[ts["start"] : ts["end"]]) > 0.02]

            total_ms = sum(ts["end"] - ts["start"] for ts in speech_ts)
            silero_result = total_ms > 1000

            # --- WebRTC VAD ---
            wav, sr = torchaudio.load(wav_path)
            wav = torchaudio.functional.resample(wav, sr, 16000)
            samples = wav.squeeze().numpy()
            pcm_data = (samples * 32768).astype(np.int16).tobytes()

            frame_duration = 30  # ms
            frame_bytes = int(16000 * frame_duration / 1000) * 2  # 2 bytes per sample (16-bit)
            has_speech_webrtc = False

            for i in range(0, len(pcm_data), frame_bytes):
                frame = pcm_data[i : i + frame_bytes]
                if len(frame) < frame_bytes:
                    break
                if self.webrtc_vad.is_speech(frame, 16000):
                    has_speech_webrtc = True
                    break

            # Combine both results
            # Combine results: speech is present if both VADs agree.
            return silero_result and has_speech_webrtc
        except Exception as e:
            logger.error(f"VAD analysis failed for {wav_path}: {e}")
            return False # Default to no speech if analysis fails

    def _ensure_silero_model_present(self):
        """
        Ensures that the Silero VAD model files are present in the local directory.

        If the directory or any of the required model files (`hubconf.py`,
        `silero_vad.onnx`, `utils_vad.py`) are missing, it attempts to download
        them from the official Silero VAD GitHub repository.

        Raises:
            RuntimeError: If a critical model file cannot be downloaded.
        """
        os.makedirs(SILERO_VAD_DIR, exist_ok=True) # Ensure the target directory exists

        # Check if all necessary files are already present
        all_files_present = True
        for model_file in SILERO_MODEL_FILES:
            local_file_path = os.path.join(SILERO_VAD_DIR, model_file)
            if not os.path.exists(local_file_path):
                all_files_present = False
                logger.info(f"Silero VAD model file '{model_file}' not found locally at {local_file_path}.")
                break # No need to check further if one is missing

        if not all_files_present:
            logger.info(f"Attempting to download Silero VAD model files to '{SILERO_VAD_DIR}'...")
            for model_file in SILERO_MODEL_FILES:
                local_file_path = os.path.join(SILERO_VAD_DIR, model_file)
                # Check again for each file, in case some were present but not all
                if not os.path.exists(local_file_path):
                    file_url = SILERO_REPO_URL + model_file
                    try:
                        logger.info(f"Downloading '{model_file}' from {file_url}...")
                        urllib.request.urlretrieve(file_url, local_file_path)
                        logger.info(f"Successfully downloaded '{model_file}' to {local_file_path}.")
                    except Exception as e:
                        logger.error(f"Failed to download '{model_file}' from {file_url}. Error: {e}")
                        # If a crucial file like hubconf.py or the ONNX model fails,
                        # the local load will likely fail. It's better to raise an error.
                        raise RuntimeError(
                            f"Failed to download critical Silero VAD model file: '{model_file}'. "
                            "Cannot proceed without VAD model."
                        ) from e
        else:
            logger.info(f"All Silero VAD model files found locally in '{SILERO_VAD_DIR}'.")
