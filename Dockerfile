FROM python:3.11-slim

WORKDIR /app

EXPOSE 51827

COPY requirements.txt .
RUN sudo apt update \ 
#&& sudo apt upgrade -y \
&& sudo apt-get install libavahi-compat-libdnssd-dev -y \ 
#&& pip install --no-cache-dir -r requirements.txt && rm -rf /var/cache/pip/* \
#&& mkdir -p .smarthome

COPY . .

CMD ["python", "main.py"]
