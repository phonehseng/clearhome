# Container for Google Cloud Run. Deploy with: see DEPLOY.md
FROM python:3.12-slim

# OpenCV (used by the local OCR) needs these system libraries.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY frontend frontend
COPY data data

# The hosted copy is read-only (Cloud Run's disk resets) and pre-answers the example questions.
ENV CLEARHOUSE_READ_ONLY=1 WARM_EXAMPLES=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 app:app
