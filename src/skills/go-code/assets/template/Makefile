.PHONY: fmt lint vet test test-race build run swagger
# Formatting is gofmt -s + goimports (std / third-party / module groups), configured in .golangci.yml
fmt:
	golangci-lint fmt ./...
lint:
	golangci-lint run ./...
vet:
	go vet ./...
test:
	go test ./...
test-race:
	go test -race ./...
build:
	CGO_ENABLED=1 go build -trimpath -o bin/api ./cmd/api
run:
	go run ./cmd/api
# Writes internal/interfaces/httpapi/openapi/swagger.json, which /docs/openapi.json serves. Commit it.
swagger:
	"$$(go env GOPATH)/bin/swag" init -g cmd/api/main.go --parseInternal \
		-o internal/interfaces/httpapi/openapi --outputTypes json
