FROM python:3.12-slim

WORKDIR /app

COPY services/api/requirements.txt /app/services/api/requirements.txt
RUN pip install --no-cache-dir -r /app/services/api/requirements.txt

COPY domain /app/domain
COPY services /app/services

CMD ["uvicorn", "services.api.app.main:api", "--host", "0.0.0.0", "--port", "8000"]
