FROM python:3.12-slim

WORKDIR /app

# Install dependencies (excluding playwright — not needed on server)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    python-dotenv \
    python-telegram-bot \
    schedule \
    flask \
    gunicorn

COPY . .

# Heroku sets PORT at runtime
CMD python main.py --web
