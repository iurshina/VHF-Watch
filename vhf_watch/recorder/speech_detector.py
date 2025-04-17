import torch


class SpeechDetector:
    def __init__(self):
        # Load Silero VAD model from torch hub
        self.vad_model, self.utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=False
        )
        (self.get_speech_ts, self.save_audio, self.read_audio, _, _) = self.utils

    def is_speech_present(self, wav_path: str) -> bool:
        try:
            # Load audio with torchaudio
            audio = self.read_audio(wav_path, sampling_rate=16000)

            # Run VAD
            speech_timestamps = self.get_speech_ts(
                audio,
                self.vad_model,
                sampling_rate=16000,
                threshold=0.7,
                min_speech_duration_ms=300,
                min_silence_duration_ms=500,
            )
            # Check if any speech segments were found
            return len(speech_timestamps) > 0
        except Exception as e:
            print("VAD analysis failed:", e)
            return False
