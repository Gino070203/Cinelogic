FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    swi-prolog \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/python

ENV TMDB_API_KEY=
ENV SESSION_SECRET=

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
