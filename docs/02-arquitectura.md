# 02 — Arquitectura de la red

## Topología

Tres organizaciones con semántica de negocio monitorean el ciclo de vida de
las prescripciones: el centro prescriptor, la empresa auditora MedChain y la
prepaga (financiador).

```
                       ┌─────────────────────────────┐
                       │   orderer.medchain.com       │
                       │   (OrdererMSP, etcdraft)     │
                       │   :7050 (consenso)           │
                       │   :7053 (admin / osnadmin)   │
                       │   :9443 (operaciones)        │
                       └──────────────┬──────────────┘
                                      │  canal: mychannel
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│ peer0.prescriptor.    │  │ peer0.auditoria.      │  │ peer0.prepaga.        │
│   medchain.com        │  │   medchain.com        │  │   medchain.com        │
│ (PrescriptorMSP)      │  │ (MedChainMSP)         │  │ (PrepagaMSP)          │
│ :7051 (gossip/grpc)   │  │ :9051 (gossip/grpc)   │  │ :11051 (gossip/grpc)  │
│ :7052 (chaincode)     │  │ :9052 (chaincode)     │  │ :11052 (chaincode)    │
│ :9444 (operaciones)   │  │ :9445 (operaciones)   │  │ :9446 (operaciones)   │
│ couchdb.prescriptor   │  │ couchdb.auditoria     │  │ couchdb.prepaga       │
│   :5984               │  │   :7984               │  │   :9984               │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘

        fabric-gateway (:8081) — puente HTTP del backend, una identidad por org
```

| Componente  | MSP ID         | Rol                                                       |
|-------------|----------------|-----------------------------------------------------------|
| Orderer     | OrdererMSP     | Ordena transacciones en bloques (consenso Raft)           |
| Prescriptor | PrescriptorMSP | Crea prescripciones; mantiene el ledger, endosa           |
| MedChain    | MedChainMSP    | Audita (aprobar/rechazar/revisión); mantiene el ledger, endosa |
| Prepaga     | PrepagaMSP     | Lectura/monitoreo; mantiene el ledger, endosa             |

- **Base de datos de estado:** CouchDB (una instancia por peer) — habilita las
  rich queries con paginación por bookmark del chaincode `prescriptions`.
- **TLS:** habilitado en todos los nodos.
- **Política de endorsement del chaincode (explícita):**
  `AND('PrescriptorMSP.peer','MedChainMSP.peer','PrepagaMSP.peer')` — ninguna
  transacción entra al ledger sin la firma de las tres organizaciones.
- **Política de lifecycle:** `MAJORITY` → requiere aprobación de 2 de 3 orgs
  (el script de deploy aprueba siempre con las tres).

## Channel Participation API (sin system channel)

Desde Fabric 2.3 se eliminó el *system channel*. En este proyecto:

1. `configtxgen` genera el **bloque de génesis del canal de aplicación**
   directamente (perfil `ChannelGenesis` en `configtx.yaml`).
2. El orderer arranca **sin canal** (`ORDERER_GENERAL_BOOTSTRAPMETHOD=none`).
3. Se une al canal vía `osnadmin channel join` contra el endpoint admin (`:7053`).
4. Cada peer se une con `peer channel join`.

## Ciclo de vida del chaincode (Fabric 2.x)

```
package → install (3 peers) → approveformyorg (3 orgs, con --signature-policy) →
checkcommitreadiness → commit → invoke/query
```

A diferencia de Fabric 1.x, el chaincode requiere **aprobación de las orgs**
según la política antes de poder commitearse al canal. Esto está automatizado
en [deployChaincode.sh](../fabric/scripts/deployChaincode.sh), que además
autodetecta la secuencia para los redeploys.

## Mapa de puertos (host)

| Servicio                        | Puerto |
|---------------------------------|--------|
| Orderer (consenso)              | 7050   |
| Orderer (admin)                 | 7053   |
| Orderer (operaciones)           | 9443   |
| peer0.prescriptor               | 7051   |
| peer0.prescriptor (operaciones) | 9444   |
| peer0.auditoria                 | 9051   |
| peer0.auditoria (operaciones)   | 9445   |
| peer0.prepaga                   | 11051  |
| peer0.prepaga (operaciones)     | 9446   |
| couchdb.prescriptor             | 5984   |
| couchdb.auditoria               | 7984   |
| couchdb.prepaga                 | 9984   |
| fabric-gateway (puente backend) | 8081   |
