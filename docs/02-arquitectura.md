# 02 — Arquitectura de la red

## Topología

```
                       ┌─────────────────────────────┐
                       │   orderer.example.com        │
                       │   (OrdererMSP, etcdraft)     │
                       │   :7050 (consenso)           │
                       │   :7053 (admin / osnadmin)   │
                       │   :9443 (operaciones)        │
                       └──────────────┬──────────────┘
                                      │  canal: mychannel
                ┌─────────────────────┴─────────────────────┐
                │                                            │
   ┌────────────────────────┐                  ┌────────────────────────┐
   │  peer0.org1.example.com │                  │  peer0.org2.example.com │
   │  (Org1MSP)              │                  │  (Org2MSP)              │
   │  :7051  (gossip/grpc)   │                  │  :9051  (gossip/grpc)   │
   │  :7052  (chaincode)     │                  │  :9052  (chaincode)     │
   │  :9444  (operaciones)   │                  │  :9445  (operaciones)   │
   └────────────────────────┘                  └────────────────────────┘
```

| Componente | MSP ID     | Rol                                            |
|------------|------------|------------------------------------------------|
| Orderer    | OrdererMSP | Ordena transacciones en bloques (consenso Raft)|
| Org1       | Org1MSP    | Mantiene el ledger, endorsa transacciones      |
| Org2       | Org2MSP    | Mantiene el ledger, endorsa transacciones      |

- **Base de datos de estado:** LevelDB (embebida en cada peer).
- **TLS:** habilitado en todos los nodos.
- **Política de endorsement (lifecycle):** `MAJORITY` → requiere aprobación de ambas orgs.

## Channel Participation API (sin system channel)

Desde Fabric 2.3 se eliminó el *system channel*. En este proyecto:

1. `configtxgen` genera el **bloque de génesis del canal de aplicación**
   directamente (perfil `ChannelGenesis` en `configtx.yaml`).
2. El orderer arranca **sin canal** (`ORDERER_GENERAL_BOOTSTRAPMETHOD=none`).
3. Se une al canal vía `osnadmin channel join` contra el endpoint admin (`:7053`).
4. Cada peer se une con `peer channel join`.

## Ciclo de vida del chaincode (Fabric 2.x)

```
package → install (cada peer) → approveformyorg (cada org) →
checkcommitreadiness → commit → invoke/query
```

A diferencia de Fabric 1.x, el chaincode requiere **aprobación de las orgs**
según la política antes de poder commitearse al canal. Esto está automatizado
en [deployChaincode.sh](../fabric/scripts/deployChaincode.sh).

## Mapa de puertos (host)

| Servicio                 | Puerto |
|--------------------------|--------|
| Orderer (consenso)       | 7050   |
| Orderer (admin)          | 7053   |
| Orderer (operaciones)    | 9443   |
| peer0.org1               | 7051   |
| peer0.org1 (operaciones) | 9444   |
| peer0.org2               | 9051   |
| peer0.org2 (operaciones) | 9445   |
