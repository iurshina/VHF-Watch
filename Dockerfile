FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y ffmpeg git build-essential curl sox cmake python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy project metadata and install Python dependencies
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi

# Clone kiwiclient and install its dependencies
RUN git clone https://github.com/jks-prv/kiwiclient.git && \
    pip install -r kiwiclient/requirements.txt

# Copy the main application code
COPY vhf_watch/ ./vhf_watch/

# Clone and build llama.cpp
RUN git clone https://github.com/ggerganov/llama.cpp.git && \
    mkdir llama.cpp/build && \
    cd llama.cpp/build && \
    cmake .. && \
    cmake --build . --config Release

# Copy model into llama.cpp models folder
COPY .models/mistral-7b-instruct-v0.2.Q4_K_M.gguf ./llama.cpp/models/mistral.gguf

# Set environment variables
ENV MODEL_PATH=/app/llama.cpp/models/mistral.gguf
ENV LLAMA_CPP_BINARY=/app/llama.cpp/build/bin/main

CMD ["python", "-m", "vhf_watch", "--debug", "--duration", "10"]