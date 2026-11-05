FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app
COPY alembic.ini .
COPY backend backend
COPY scripts/container_start.py scripts/container_start.py
USER app
EXPOSE 8000
CMD ["python", "scripts/container_start.py"]
