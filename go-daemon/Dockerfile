# --- build stage ---
FROM golang:1.23-alpine AS build
WORKDIR /src

# Resolve modules first for better layer caching. go.sum is generated here if
# absent (the build environment has network access).
COPY go.mod ./
RUN go mod download

COPY . .
RUN go mod tidy && CGO_ENABLED=0 go build -trimpath -o /out/network-daemon ./cmd/daemon

# --- runtime stage ---
# :nonroot runs as uid 65532; the static binary needs no shell or packages.
FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=build /out/network-daemon /app/network-daemon
COPY config.yaml /app/config.yaml
USER nonroot
EXPOSE 2112
ENTRYPOINT ["/app/network-daemon"]
