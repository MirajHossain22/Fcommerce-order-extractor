FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend HOST=0.0.0.0 PORT=8000 DATABASE_PATH=/data/orders.sqlite3
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home appuser \
    && mkdir /data && chown appuser:appuser /data
COPY backend/app ./backend/app
COPY frontend ./frontend
USER appuser
EXPOSE 8000
CMD ["python", "-m", "app.serve"]
