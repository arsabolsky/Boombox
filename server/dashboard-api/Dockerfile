# Build the Go program, then copy just the program into a small image.
FROM golang:1.27 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /dashboard-api ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=build /dashboard-api /dashboard-api
EXPOSE 8000
ENTRYPOINT ["/dashboard-api"]
