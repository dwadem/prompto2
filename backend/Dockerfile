FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-scraper.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-scraper.txt \
    && playwright install --with-deps chromium
COPY . .
RUN mkdir -p data
# $PORT is injected at runtime by Render, Railway, and most PaaS.
# Shell form expands the variable; exec replaces the shell so uvicorn is PID 1.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
