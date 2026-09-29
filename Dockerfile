# Hugging Face Space — Python hologram. No npm ci.
# Flatten-compatible: Hub payload is Dockerfile + server.py + space/index.html + README + LICENSE.
# Base: python:3.14-slim through mirror.gcr.io, pinned to the multi-arch OCI image-index
# digest that mirror.gcr.io and registry-1.docker.io both returned for that tag on
# 2026-09-29 (3.14.7-slim-trixie; includes linux/amd64). Dependabot (docker, /) moves the
# tag and the digest together.
FROM mirror.gcr.io/library/python:3.14-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860
RUN python -m pip install --no-cache-dir "https://github.com/szl-holdings/szl-substrate/archive/ad2e04374717ef79dbf7dbb91aea5a8480ed10c3.tar.gz"
COPY server.py szl_space_brain.py ./
COPY space/index.html ./index.html
EXPOSE 7860
CMD ["python", "-u", "server.py"]
