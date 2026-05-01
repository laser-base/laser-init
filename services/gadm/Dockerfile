FROM python:3.11-slim

WORKDIR /app

# pyogrio bundles its own GDAL — no system GDAL install needed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV CACHE_DIR=/cache

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
