# Multi-stage build for the AutoSRE API service (Go).
# Build context is the repo root so it can read the root Go module.

# --- build stage ---
FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY cmd/ ./cmd/
COPY internal/ ./internal/
COPY pkg/ ./pkg/
RUN CGO_ENABLED=0 go build -trimpath -o /out/api ./cmd/api

# --- runtime stage ---
# :nonroot runs as uid 65532; the static binary needs no shell or packages.
FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=build /out/api /app/api
USER nonroot
EXPOSE 8000
ENTRYPOINT ["/app/api"]
