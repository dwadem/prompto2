FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-scraper.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-scraper.txt \
    && playwright install --with-deps chromium
COPY . .
RUN mkdir -p data
# Railway (and most PaaS) inject $PORT at runtime; bind to it, defaulting to
# 8000 for local `docker run`. JSON/exec form (signal-safe) wrapping `sh -c`
# so $PORT is expanded; `exec` makes uvicorn PID 1 to receive OS signals.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
