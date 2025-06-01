import numpy as np
import torch
import torchaudio
import webrtcvad


class SpeechDetector:
    def __init__(self):
        self.vad_model, self.utils = torch.hub.load(
            './silero-vad',
            'silero_vad',
            source='local'
        )
        (self.get_speech_ts, self.save_audio, self.read_audio, _, _) = self.utils

        # Initialize WebRTC VAD
        self.webrtc_vad = webrtcvad.Vad(3)  # 3 = most aggressive

    def is_speech_present(self, wav_path: str) -> bool:
        try:
            # --- Silero VAD ---
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
            return silero_result and has_speech_webrtc
        except Exception as e:
            print("VAD analysis failed:", e)
            return False