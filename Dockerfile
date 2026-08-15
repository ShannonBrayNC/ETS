FROM python:3.12-slim-bookworm

WORKDIR /app

# Apply current Debian security updates during the image build. The APT lists are
# removed in the same layer so the runtime image does not retain package metadata.
RUN apt-get update \
    && apt-get upgrade --yes --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY ets ./ets
COPY scripts/qualify_hosted_azure_live.py ./scripts/qualify_hosted_azure_live.py

RUN python -m pip install --no-cache-dir -e ".[hosted]"

ENV ETS_STORAGE_PROVIDER=in_memory
ENV ETS_AUTH_MODE=local_header
ENV ETS_SIGNING_MODE=local_unsigned

EXPOSE 8000

CMD ["python", "-m", "ets.api.container_entrypoint"]
