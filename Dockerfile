FROM python:3.11-slim
WORKDIR /app

# pydirectinput is Windows-only, so it is left out of the container build.
COPY requirements.txt .
RUN grep -vi pydirectinput requirements.txt > req-docker.txt \
    && pip install --no-cache-dir -r req-docker.txt

COPY . .
CMD ["python", "train.py"]
