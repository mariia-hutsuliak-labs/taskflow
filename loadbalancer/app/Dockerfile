FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install --no-cache-dir boto3==1.42.97

COPY serverless/lambda/handler.py /app/lambda/handler.py
COPY loadbalancer/app/server.py /app/server.py
COPY loadbalancer/app/metrics.py /app/metrics.py

EXPOSE 8000
CMD ["python", "server.py"]
