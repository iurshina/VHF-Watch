from vhf_watch.analyzer.llm_analyzer import analyze_transcript, fallback_analysis
import pytest # Already implicitly used by monkeypatch, but good to be explicit


def test_analyze_with_llm_mock(monkeypatch):
    def fake_run(*args, **kwargs):
        class Result:
            stdout = '{"call_for_help": true, "location": "Zakynthos"}'

        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    output = analyze_transcript("Mayday, this is Sea Spirit near Zakynthos.")
    assert output["call_for_help"] is True
    assert "Zakynthos" in output["location"]


def test_fallback_analysis_with_keywords():
    transcript = "MAYDAY MAYDAY ship sinking need HELP immediately"
    result = fallback_analysis(transcript)

    assert result["llm_fallback"] is True
    assert "mayday" in result["keywords"]
    assert "help" in result["keywords"]
    assert result["type"] == "DISTRESS"
    assert "ship sinking" in result["reason"] # Check if it captures some context

def test_fallback_analysis_no_keywords():
    transcript = "Weather is clear, all normal, sailing smoothly"
    result = fallback_analysis(transcript)

    assert result["llm_fallback"] is True
    assert not result["keywords"] # Should be empty or not contain specific distress words
    assert result["type"] == "NORMAL"
    assert "clear" in result["reason"] # Check if it captures some context
