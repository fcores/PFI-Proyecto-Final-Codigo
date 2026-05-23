# PFI — Proyecto Final

Configuración y despliegue de una red **Hyperledger Fabric 2.5 LTS** desde cero.
Proyecto final de Ingeniería Informática (UADE).

Esta primera etapa levanta una red de prueba mínima y reproducible:

- **2 organizaciones** (`Org1`, `Org2`), cada una con 1 peer.
- **1 orderer** (consenso Raft / etcdraft), usando la *Channel Participation API* (sin system channel).
- **Material criptográfico** generado con `cryptogen`.
- **Chaincode** de ejemplo (`asset-transfer-basic`) escrito en **Go**.
- **Canal** de aplicación: `mychannel`.

> La app cliente (React + FastAPI + Fabric Gateway SDK) se sumará en una etapa posterior.

---

## Estructura del proyecto

```
PFI-Proyecto-Final/
├── README.md
├── .gitignore
├── docs/
│   ├── 01-prerequisitos.md
│   ├── 02-arquitectura.md
│   ├── 03-uso.md
│   └── 04-aws-ec2-setup.md
├── chaincode/
│   └── asset-transfer-basic/
│       ├── go.mod
│       ├── go.sum
│       ├── main.go
│       └── chaincode/
│           └── smartcontract.go
└── fabric/
    ├── network.sh
    ├── network/
    │   ├── .env
    │   ├── crypto-config.yaml
    │   ├── configtx.yaml
    │   └── compose/
    │       └── compose-net.yaml
    └── scripts/
        ├── bootstrap.sh
        ├── install-fabric.sh
        ├── envVar.sh
        ├── utils.sh
        ├── generateArtifacts.sh
        ├── createChannel.sh
        └── deployChaincode.sh
```

---

## Quickstart

> **Requisito:** Docker + Docker Compose corriendo.
> - En **AWS EC2** (recomendado, sin fricción): ver [docs/04-aws-ec2-setup.md](docs/04-aws-ec2-setup.md).
> - En **Windows** local: **WSL2 + Docker Desktop**, ver [docs/01-prerequisitos.md](docs/01-prerequisitos.md).

```bash
cd fabric

# 1. Descargar binarios de Fabric e imágenes Docker (una sola vez)
./network.sh install

# 2. Levantar la red (genera cripto + arranca contenedores)
./network.sh up

# 3. Crear el canal 'mychannel' y unir los peers
./network.sh createChannel

# 4. Desplegar el chaincode de ejemplo
./network.sh deployCC

# Apagar y limpiar todo
./network.sh down
```

Más detalle en [docs/03-uso.md](docs/03-uso.md).

---

## Versiones

| Componente            | Versión    |
|-----------------------|------------|
| Hyperledger Fabric    | 2.5.15 LTS |
| Fabric CA             | 1.5.13     |
| Chaincode (Go)        | Go 1.22+   |
| Docker Engine         | 29.x       |
| Consenso del orderer  | etcdraft   |

---

## Notas de compatibilidad

- **Docker Engine v29+**: requiere Fabric >= 2.5.15 (fix para broken pipe en chaincode build, ver [issue #5350](https://github.com/hyperledger/fabric/issues/5350)).
- **TLS**: los certificados incluyen SANs para `localhost` y `127.0.0.1` para permitir acceso desde el host a los contenedores.
- **go.sum**: debe estar commiteado junto con `go.mod` para que el chaincode compile correctamente dentro de `fabric-ccenv`.
- **configtx.yaml**: las rutas a `organizations/` son relativas a `FABRIC_CFG_PATH` (`fabric/network/`), por lo que usan `./organizations/`.
