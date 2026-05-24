FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY ets ./ets

RUN python -m pip install --no-cache-dir -e ".[dev]"

ENV ETS_STORAGE_PROVIDER=in_memory
ENV ETS_AUTH_MODE=local_header
ENV ETS_SIGNING_MODE=local_unsigned

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "ets.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
