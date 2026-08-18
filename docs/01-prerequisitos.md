# 01 — Prerequisitos

> **Alcance:** esto es lo que hace falta para levantar la **red Fabric en tu
> máquina**. No aplica al resto del proyecto: el backend, el frontend y los
> tests no necesitan Docker ni Fabric (los tests usan un doble del chaincode), y
> el despliegue y la operación en AWS van por el pipeline y por SSM.
> Ver la tabla *"Qué necesitás según lo que vengas a hacer"* en el
> [README](../README.md).

## Software necesario

| Herramienta      | Versión recomendada | Para qué                                  |
|------------------|---------------------|-------------------------------------------|
| Docker           | 24+                 | Correr orderer, peers y chaincode         |
| Docker Compose   | v2 (`docker compose`) | Orquestar los contenedores              |
| Git Bash o WSL2  | —                   | Ejecutar los scripts `.sh`                |
| curl             | —                   | Descargar binarios de Fabric              |
| Go               | 1.21+               | Compilar / `go mod vendor` del chaincode  |

Los binarios de Fabric (`peer`, `orderer`, `cryptogen`, `configtxgen`, `osnadmin`)
se descargan automáticamente con `./network.sh install` dentro de `fabric/bin/`.

## ⚠️ Windows: usar WSL2

Hyperledger Fabric está pensado para entornos Unix. En Windows **se recomienda fuertemente**:

1. Instalar **WSL2** con una distro Linux (Ubuntu 22.04).
   ```powershell
   wsl --install -d Ubuntu
   ```
2. Instalar **Docker Desktop** y habilitar la integración con WSL2
   (*Settings → Resources → WSL Integration*).
3. Clonar el repo **dentro del filesystem de WSL** (ej. `~/PFI-Proyecto-Final`),
   no en `/mnt/c/...`, para evitar problemas de permisos y performance.
4. Instalar Go dentro de WSL:
   ```bash
   sudo apt update && sudo apt install -y golang-go
   ```

> Git Bash también puede funcionar para comandos simples, pero el montaje del
> socket de Docker y los permisos de los certificados suelen dar problemas.
> Para una experiencia sin fricción, usá WSL2.

## Verificar que todo está listo

```bash
docker --version
docker compose version
go version
curl --version
```

Una vez verificado, seguí con [03-uso.md](03-uso.md).
