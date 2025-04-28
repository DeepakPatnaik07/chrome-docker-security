FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libatspi2.0-0 libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libasound2 wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY ./docker/analyze_url.py .

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] # Keep CMD commented out or remove if not needed for this image

# Remove the conflicting Alpine commands below
# USER root
# RUN apk add --no-cache python3 py3-pip && \
#     pip3 install playwright && \
#     playwright install chromium