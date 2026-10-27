# PEGELONLINE poller. Build context: ./ingestion/feeds (see compose.yaml).
# Needs the Docker socket to `docker cp` / `docker exec` into the Zetaris driver container.
# The docker client is the static binary from the official CLI image; no daemon, no apt.
FROM docker:27-cli AS dockercli

FROM python:3.12-slim
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
WORKDIR /app/ingestion/feeds
COPY pegel_poll.py .
ENV PYTHONUNBUFFERED=1 \
    POLL_INTERVAL_S=600 \
    ZETARIS_CONTAINER=zetaris-driver-1
CMD ["python", "pegel_poll.py", "--service"]
