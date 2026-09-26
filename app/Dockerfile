# API + CAD (build123d / OCCT) for Railway. Web is deployed separately on Vercel (web/ is not in this image).
# Multi-stage: uv, its download cache and build state stay in the builder; the final image only carries the venv + app code.

FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 UV_NO_CACHE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
# OCP (OpenCascade) wheels link against GL / X11 client libs even when headless
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libxrender1 libxext6 libsm6 libgomp1 \
    && apt-get clean \
    && find /var/lib/apt/lists -type f -delete

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=builder /app/.venv /app/.venv

# prebuilt CAD/renders/fixtures live inside api/ (api/cad/prebuilt, api/fixtures, api/costs/data)
COPY api/ api/
COPY contracts/ contracts/
COPY factory_mcp/ factory_mcp/

# Defaults for a Railway volume mounted at /data (override in the Railway variables if needed)
ENV DB_PATH=/data/app.db FILES_DIR=/data/files FACTORY_MCP_DB=/data/network.db SEED_DEMO_ON_EMPTY=1
RUN mkdir -p /data

EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 75 --proxy-headers --forwarded-allow-ips='*'"]
