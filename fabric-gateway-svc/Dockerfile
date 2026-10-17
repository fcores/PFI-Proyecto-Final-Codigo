# fabric-gateway-svc — puente HTTP -> Fabric Gateway SDK.
# Se construye desde fabric/network/compose/compose-net.yaml (servicio fabric-gateway).
# Go 1.25+ es requisito de fabric-gateway v1.11.0 (con 1.24 el build falla con
# "requires go >= 1.25.0"). Mantener alineado con go.mod y con el job
# gateway-build de ci.yml.
FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go.mod ./
# go mod tidy resuelve y fija dependencias (el repo no versiona go.sum de este modulo)
COPY . .
RUN go mod tidy && CGO_ENABLED=0 go build -o /out/fabric-gateway-svc .

FROM alpine:3.20
RUN adduser -D -u 10001 gateway
USER gateway
COPY --from=build /out/fabric-gateway-svc /usr/local/bin/fabric-gateway-svc
EXPOSE 8443
ENTRYPOINT ["fabric-gateway-svc"]
