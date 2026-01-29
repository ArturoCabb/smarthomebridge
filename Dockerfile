FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt update && \
 apt-get install -y --no-install-recommends libavahi-compat-libdnssd-dev && \ 
 pip install --no-cache-dir -r requirements.txt && rm -rf /var/cache/pip/* && \ 
 mkdir -p .smarthome && \
 rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py"]
