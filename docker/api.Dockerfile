FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY apps ./apps
COPY engine ./engine
COPY data ./data
COPY controls ./controls
COPY scenarios ./scenarios
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000"]
