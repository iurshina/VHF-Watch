# 📡 VHF-Watch: AI Listener for Marine Distress Calls

⚠️ **Note: This project is in early development.**  

**Contributions, suggestions, testing, and collaborations are very welcome!** 🛠️

----

**VHF-Watch** is a Python-based CLI tool that monitors a live VHF marine radio WebSocket stream. It transcribes radio audio locally using [Whisper](https://github.com/openai/whisper), analyzes it with a local [llama.cpp](https://github.com/ggerganov/llama.cpp) LLM, and logs events such as:

- 🚨 Calls for help
- 🛂 Mentions of “Libyan Coast Guard”, “Frontex”, or “rescue”
- 📍 Locations or times
- 🚢 Named vessels or coast guards

---

## 🧰 Requirements

- Python 3.10+
- ffmpeg
- [Poetry](https://python-poetry.org/) 
- [Whisper](https://github.com/openai/whisper) (model files will be downloaded by the library on first use)
- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- A quantized `.gguf` LLM model (e.g. `mistral-7b-instruct.Q4_K_M.gguf`)
- The Silero VAD model files (`hubconf.py`, `silero_vad.onnx`, `utils_vad.py`) will be automatically downloaded to a `./silero-vad/` directory on first run if not found.

---

## 🚀 Quickstart (Poetry)

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Run the app
poetry run python -m vhf_watch --debug --duration 15
```
The application connects to a pre-configured WebSocket URL for the audio stream (see `vhf_watch/config.py`).

---

## 🐳 Docker (optional)

```bash
docker build -t vhf-watch .
docker run --rm -it vhf-watch
```
The Docker image includes all necessary dependencies. The WebSocket URL is also configured within the application.

---

## ⚙️ CLI Options

| Flag         | Description                             |
|--------------|-----------------------------------------|
| `--debug`    | Print raw Whisper transcript             |
| `--duration` | Time limit in minutes (default = 0, for continuous run)     |
| `--chunk`    | Audio chunk length in seconds for processing (default = 10) |

---

## 📂 Output

Logs are saved to `vhf_watch_log.jsonl`:

```json
{
  "timestamp": "2025-04-13T10:42:31.123Z",
  "transcription": "Mayday, mayday, this is Sea Star near Zakynthos...",
  "llm_output": {
    "call_for_help": true,
    "actors": ["Sea Star"],
    "location": "Zakynthos",
    "keywords": ["mayday"]
  }
}
```

---

## 🧪 Tests

```bash
poetry run pytest tests/
```

---

## 🛠 Dev Tools

```bash
# Format code
poetry run black .

# Lint with Ruff
poetry run ruff check .

# Auto-fix with Ruff
poetry run ruff check . --fix

# Type-check
poetry run mypy vhf_watch/
```