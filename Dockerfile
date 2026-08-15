FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY ets ./ets
COPY scripts/qualify_hosted_azure_live.py ./scripts/qualify_hosted_azure_live.py

RUN python -m pip install --no-cache-dir -e ".[hosted]"

ENV ETS_STORAGE_PROVIDER=in_memory
ENV ETS_AUTH_MODE=local_header
ENV ETS_SIGNING_MODE=local_unsigned

EXPOSE 8000

CMD ["python", "-m", "ets.api.container_entrypoint"]
