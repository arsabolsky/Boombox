# Python environment for running the models (decision.py, remediation.py, evaluate.py).
FROM python:3.13-slim
WORKDIR /ai
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
