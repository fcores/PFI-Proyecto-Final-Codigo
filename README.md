# PFI — Proyecto Final

Configuración y despliegue de una red **Hyperledger Fabric 2.5 LTS** desde cero.
Proyecto final de Ingeniería Informática (UADE).

Esta primera etapa levanta una red de prueba mínima y reproducible:

- **2 organizaciones** (`Org1`, `Org2`), cada una con 1 peer.
- **1 orderer** (consenso Raft / etcdraft), usando la *Channel Participation API* (sin system channel).
- **Material criptográfico** generado con `cryptogen`.
- **Chaincode** de ejemplo (`asset-transfer-basic`) escrito en **Go**.
- **Canal** de aplicación: `mychannel`.

> La app cliente (Fabric Gateway SDK) se sumará en una etapa posterior.

---

## Estructura del proyecto

```
PFI-Proyecto-Final/
├── README.md
├── .gitignore
├── docs/                          # Documentación de prerequisitos y arquitectura
│   ├── 01-prerequisitos.md
│   ├── 02-arquitectura.md
│   ├── 03-uso.md
│   └── 04-aws-ec2-setup.md     # Levantar la red en una EC2
├── chaincode/
│   └── asset-transfer-basic/      # Smart contract en Go
│       ├── go.mod
│       └── chaincode/
│           └── smartcontract.go
│       └── main.go
└── fabric/
    ├── network.sh                 # ⭐ Punto de entrada (up | down | createChannel | deployCC ...)
    ├── bin/                        # Binarios de Fabric (descargados, gitignored)
    ├── config/                     # core.yaml / orderer.yaml base (descargado, gitignored)
    ├── network/
    │   ├── .env                    # Versiones de imágenes y variables comunes
    │   ├── crypto-config.yaml      # Definición de identidades para cryptogen
    │   ├── configtx.yaml           # Perfiles de canal / genesis (Raft)
    │   ├── compose/
    │   │   └── compose-net.yaml    # orderer, peers, CLI
    │   ├── organizations/          # (generado) certificados y MSP
    │   └── channel-artifacts/      # (generado) bloques de génesis del canal
    └── scripts/
        ├── bootstrap.sh            # Provisiona Ubuntu/EC2 (Docker + Go)
        ├── install-fabric.sh       # Descarga binarios + imágenes Docker
        ├── envVar.sh               # Helpers de variables de entorno por org
        ├── utils.sh                # Funciones de logging
        ├── generateArtifacts.sh    # cryptogen + bloque génesis
        ├── createChannel.sh        # crear canal y unir peers
        └── deployChaincode.sh      # package / install / approve / commit
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

| Componente            | Versión   |
|-----------------------|-----------|
| Hyperledger Fabric    | 2.5.x LTS |
| Fabric CA             | 1.5.x     |
| Chaincode (Go)        | Go 1.21+  |
| Consenso del orderer  | etcdraft  |
