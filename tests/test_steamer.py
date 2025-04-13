from vhf_watch.recorder import streamer


def test_transcribe_stream_mock(monkeypatch):
    # Mock Whisper model
    class FakeModel:
        def transcribe(self, _):
            return {"text": "This is a test broadcast."}

    monkeypatch.setattr("vhf_watch.recorder.streamer.model", FakeModel())

    # Create a fake process with .stdout.read()
    class DummyProcess:
        def __init__(self):
            self.stdout = self

        def read(self, n):
            return b"FAKEAUDIO" * (n // 9)

        def kill(self):
            pass

    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: DummyProcess())

    result = streamer.transcribe_stream("http://fake-stream", 5)
    assert "test broadcast" in result
