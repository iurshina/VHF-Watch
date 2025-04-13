import json

from vhf_watch.analyzer.llm_analyzer import analyze_transcript

def test_analyze_with_llm_mock(monkeypatch):
    def fake_run(*args, **kwargs):
        class Result:
            stdout = '{"call_for_help": true, "location": "Zakynthos"}'

        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    output = analyze_transcript("Mayday, this is Sea Spirit near Zakynthos.")
    assert output["call_for_help"] is True
    assert "Zakynthos" in output["location"]