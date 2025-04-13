import tempfile

from vhf_watch.analyzer.llm_analyzer import analyze_transcript
from vhf_watch.recorder import streamer


def test_analyze_with_llm_mock(monkeypatch):
    def fake_run(*args, **kwargs):
        class Result:
            stdout = '{"call_for_help": true, "location": "Zakynthos"}'

        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    output = analyze_transcript("Mayday, this is Sea Spirit near Zakynthos.")
    assert output["call_for_help"] is True
    assert "Zakynthos" in output["location"]


def test_transcribe_chunk_mock(monkeypatch):
    import wave

    import numpy as np

    # Mock whisper model
    class FakeModel:
        def transcribe(self, path):
            return {"text": "This is a test broadcast."}

    monkeypatch.setattr("vhf_watch.recorder.streamer.model", FakeModel())

    # Generate a valid silent WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        with wave.open(tmp, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            duration_seconds = 1
            samples = (np.zeros(int(16000 * duration_seconds))).astype(np.int16).tobytes()
            wf.writeframes(samples)
        tmp_path = tmp.name

    result = streamer.transcribe_chunk(tmp_path)
    assert "test broadcast" in result
