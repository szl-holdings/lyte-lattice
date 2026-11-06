# Hugging Face Space — Python hologram. No npm ci.
# Flatten-compatible: Hub payload is Dockerfile + server.py + index.html + README + LICENSE.
# Base: python:3.15-slim through mirror.gcr.io, pinned to a multi-arch OCI image-index
# digest (3.15.2-slim-trixie; includes linux/amd64; index re-read from mirror.gcr.io on
# 2026-11-06). Dependabot (docker, /space) moves the tag and the digest together.
FROM mirror.gcr.io/library/python:3.15-slim@sha256:8c13a3f37a6a5b71498228e902c4b9f51c1f7900d49fabf71f9a650c6120e0d0
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860
COPY server.py ./server.py
COPY index.html ./index.html
EXPOSE 7860
CMD ["python", "-u", "server.py"]
