FROM python:3.11-slim
WORKDIR /app
COPY app_v2/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
ARG CACHE_BUST=1
COPY app_v2 /app/app_v2
WORKDIR /app/app_v2
CMD ["python", "entrypoint.py"]
