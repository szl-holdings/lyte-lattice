# Hugging Face Space — Python hologram. No npm ci.
# Flatten-compatible: Hub payload is Dockerfile + server.py + index.html + README + LICENSE.
# Base: python:3.12-slim through mirror.gcr.io, pinned to the multi-arch OCI image-index
# digest that mirror.gcr.io and registry-1.docker.io both returned for that tag on
# 2026-09-29 (3.12.14-slim-trixie; includes linux/amd64). Dependabot (docker, /space) moves the
# tag and the digest together.
FROM mirror.gcr.io/library/python:3.14-slim@sha256:c3e521df8b2b498a7a682e7e18676771cb80c6b75b8699af886b2d554ce40151
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860
COPY server.py ./server.py
COPY index.html ./index.html
EXPOSE 7860
CMD ["python", "-u", "server.py"]
