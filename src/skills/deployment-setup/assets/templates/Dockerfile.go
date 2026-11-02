# Go service. Replace `example-api` and ./cmd/example-api. Pin versions via ARG (digest preferred).
# Static build (CGO_ENABLED=0) can use a distroless runtime; with cgo keep a libc runtime (below).
# Drop the COPY lines for directories the module does not have; go.sum must exist.
ARG GO_IMAGE=golang:1.26-bookworm
ARG RUNTIME_IMAGE=debian:bookworm-slim

FROM ${GO_IMAGE} AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY cmd/ cmd/
COPY internal/ internal/
COPY pkg/ pkg/
RUN CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/example-api ./cmd/example-api

FROM ${RUNTIME_IMAGE}
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build --chown=65532:65532 /out/example-api /app/example-api
COPY --chown=65532:65532 scripts/health.sh /app/scripts/health.sh
USER 65532:65532
# Every API listens on 3000 (api-contract skill); Traefik reaches it there.
EXPOSE 3000
# The entrypoint gate waits for the infrastructure named in $HEALTH_DEPS, then execs the application
# (no-op when HEALTH_DEPS is empty). It needs bash in the runtime image.
# Exec form; the gate execs the app, so it is PID 1 and receives SIGTERM.
ENTRYPOINT ["/app/scripts/health.sh", "--wait", "--", "/app/example-api"]
CMD ["serve"]
