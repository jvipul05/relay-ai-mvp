FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python -c \"from dotenv import load_dotenv; load_dotenv('/secrets/env/.env'); import os, uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=int(os.getenv('PORT', '8080')))\""]
