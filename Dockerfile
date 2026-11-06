# Hugging Face Space — Python hologram. No npm ci.
# Flatten-compatible: Hub payload is Dockerfile + server.py + szl_space_brain.py +
# space/index.html + README + LICENSE.
# Base: python:3.15-slim through mirror.gcr.io, pinned to a multi-arch OCI image-index
# digest (3.15.2-slim-trixie; includes linux/amd64; index re-read from mirror.gcr.io on
# 2026-11-06). Dependabot (docker, /) moves the tag and the digest together.
FROM mirror.gcr.io/library/python:3.15-slim@sha256:e97b88e416c3c01eb427b21fd8cd3ebf006e6ee38afcfcc3cae1c54ee2ab0a75
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860
RUN python -m pip install --no-cache-dir "https://github.com/szl-holdings/szl-substrate/archive/ad2e04374717ef79dbf7dbb91aea5a8480ed10c3.tar.gz"
COPY server.py szl_space_brain.py ./
COPY space/index.html ./index.html
EXPOSE 7860
CMD ["python", "-u", "server.py"]
