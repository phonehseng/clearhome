# Gemma 4 (26B, the same model the app calls through the Gemini API) served by Ollama on a Cloud Run L4 GPU.
# The weights are baked into the image so a cold start doesn't download 17 GB. See gemma/README.md.
FROM ollama/ollama:latest

# A 16k-token window for each of 2 answers at a time. Ollama's default (4k) silently cut our longer prompts down to
# their last 2k tokens, dropping the rules and the question; keep OLLAMA_CONTEXT_LENGTH equal to CONTEXT_TOKENS in
# backend/gemma_gpu.py, or Ollama reloads the model whenever the two disagree. 2 x 16k fits the L4 next to the weights.
ENV OLLAMA_HOST=0.0.0.0:8080 \
    OLLAMA_MODELS=/models \
    OLLAMA_KEEP_ALIVE=-1 \
    OLLAMA_NUM_PARALLEL=2 \
    OLLAMA_CONTEXT_LENGTH=16384 \
    OLLAMA_DEBUG=false
ENV MODEL=gemma4:26b

RUN ollama serve & sleep 5 && ollama pull $MODEL

ENTRYPOINT ["ollama", "serve"]
