# Multi-stage build for the AutoSRE network daemon.
# Build context is the repo root (see docker-compose.yml) so it can read the
# root Go module. Only the Go sources are copied into the build stage.

# --- build stage ---
FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY cmd/ ./cmd/
COPY internal/ ./internal/
COPY pkg/ ./pkg/
RUN CGO_ENABLED=0 go build -trimpath -o /out/network-daemon ./cmd/network-daemon

# --- runtime stage ---
# :nonroot runs as uid 65532; the static binary needs no shell or packages.
FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=build /out/network-daemon /app/network-daemon
COPY configs/network-daemon.yaml /app/config.yaml
USER nonroot
EXPOSE 2112
ENTRYPOINT ["/app/network-daemon"]
