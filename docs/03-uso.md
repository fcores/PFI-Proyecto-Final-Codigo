# 03 — Uso

> Todos los comandos se ejecutan desde la carpeta `fabric/`.
> En Windows, hacelo desde **WSL2** (ver [01-prerequisitos.md](01-prerequisitos.md)).

```bash
cd fabric
```

## 1. Instalar binarios e imágenes (una sola vez)

```bash
./network.sh install
```

Descarga `peer`, `orderer`, `cryptogen`, `configtxgen`, `osnadmin` en `fabric/bin/`,
los archivos de config base en `fabric/config/` y baja las imágenes Docker de Fabric.

## 2. Levantar la red

```bash
./network.sh up
```

- Genera el material criptográfico (`organizations/`) con `cryptogen`.
- Genera el bloque de génesis del canal (`channel-artifacts/mychannel.block`).
- Arranca los contenedores: orderer, peer0.org1, peer0.org2 y cli.

Verificá con `docker ps`.

## 3. Crear el canal

```bash
./network.sh createChannel
# o con otro nombre:
./network.sh createChannel micanal
```

Une el orderer (vía `osnadmin`) y ambos peers al canal.

## 4. Desplegar el chaincode

```bash
./network.sh deployCC
```

Empaqueta, instala en los 3 peers, aprueba por las 3 organizaciones y commitea
el chaincode `prescriptions` con la política de endorsement
`AND('PrescriptorMSP.peer','MedChainMSP.peer','PrepagaMSP.peer')`, luego corre
`InitLedger` y una query `ListPrescriptions` de verificación.

## 5. Interactuar manualmente

Configurá las variables de entorno para operar como Org1:

```bash
export PATH=$PWD/bin:$PATH
export FABRIC_CFG_PATH=$PWD/config
export ORG_DIR=$PWD/network/organizations
source scripts/envVar.sh
setGlobals 1

ORDERER_CA=$ORG_DIR/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
PEER0_ORG1_CA=$ORG_DIR/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
PEER0_ORG2_CA=$ORG_DIR/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt
```

### Query — leer un asset

```bash
peer chaincode query -C mychannel -n basic -c '{"Args":["ReadAsset","asset1"]}'
```

### Invoke — crear un asset

```bash
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "$ORDERER_CA" \
  -C mychannel -n basic \
  --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_ORG1_CA" \
  --peerAddresses localhost:9051 --tlsRootCertFiles "$PEER0_ORG2_CA" \
  -c '{"function":"CreateAsset","Args":["asset10","magenta","12","Lucia","700"]}'
```

### Invoke — transferir un asset

```bash
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "$ORDERER_CA" \
  -C mychannel -n basic \
  --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_ORG1_CA" \
  --peerAddresses localhost:9051 --tlsRootCertFiles "$PEER0_ORG2_CA" \
  -c '{"function":"TransferAsset","Args":["asset10","Mariano"]}'
```

## 6. Apagar y limpiar

```bash
./network.sh down
```

Apaga los contenedores, borra volúmenes y elimina `organizations/`,
`channel-artifacts/` y paquetes `.tar.gz`.

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `docker: command not found` | Docker no instalado / no en PATH | Instalar Docker Desktop, abrir WSL2 |
| `cannot connect to the Docker daemon` | Docker no está corriendo | Iniciar Docker Desktop |
| El peer no se une al canal | red recién levantada, aún inicializando | el script reintenta; si persiste, `./network.sh down && up` |
| `chaincode install` falla compilando Go | faltan dependencias | correr `go mod vendor` en `chaincode/prescription-contract` |
| Permisos de certificados en Windows | repo en `/mnt/c/...` | clonar dentro del FS de WSL (`~/...`) |
