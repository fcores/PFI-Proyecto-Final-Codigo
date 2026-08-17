# fabric-gateway-svc — puente HTTP -> Fabric Gateway SDK.
# Se construye desde fabric/network/compose/compose-net.yaml (servicio fabric-gateway).
FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod ./
# go mod tidy resuelve y fija dependencias (el repo no versiona go.sum de este modulo)
COPY . .
RUN go mod tidy && CGO_ENABLED=0 go build -o /out/fabric-gateway-svc .

FROM alpine:3.20
RUN adduser -D -u 10001 gateway
USER gateway
COPY --from=build /out/fabric-gateway-svc /usr/local/bin/fabric-gateway-svc
EXPOSE 8081
ENTRYPOINT ["fabric-gateway-svc"]
