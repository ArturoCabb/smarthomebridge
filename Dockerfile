FROM python:3.11-slim

WORKDIR /app

EXPOSE 51827

COPY requirements.txt .
RUN sudo apt update && \
 sudo apt-get install -y --no-install-recommends build-essential libavahi-compat-libdnssd-dev && \ 
 pip install --no-cache-dir -r requirements.txt && rm -rf /var/cache/pip/* && \ 
 mkdir -p .smarthome && \
 rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py"]
