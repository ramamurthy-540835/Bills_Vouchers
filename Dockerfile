FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN pip install --no-cache-dir --no-deps .
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
