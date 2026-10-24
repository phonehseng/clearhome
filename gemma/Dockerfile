# Gemma 4 (26B, the same model the app calls through the Gemini API) served by Ollama on a Cloud Run L4 GPU.
# The weights are baked into the image so a cold start doesn't download 17 GB. See gemma/README.md.
FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:8080 \
    OLLAMA_MODELS=/models \
    OLLAMA_KEEP_ALIVE=-1 \
    OLLAMA_NUM_PARALLEL=4 \
    OLLAMA_DEBUG=false
ENV MODEL=gemma4:26b

RUN ollama serve & sleep 5 && ollama pull $MODEL && kill %1

ENTRYPOINT ["ollama", "serve"]
