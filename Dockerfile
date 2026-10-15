FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/storage

WORKDIR /app

# Сначала только зависимости — этот слой кешируется,
# и пересборка после правки кода занимает секунды, а не минуты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Потом код. База, JSON-данные, картинки и .env сюда НЕ попадают (.dockerignore)
COPY src ./src

# Все изменяемые данные — в volume, который переживает пересборку
VOLUME ["/app/storage"]

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
