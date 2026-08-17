# 04 — Levantar la red en una instancia EC2 (AWS)

Alternativa a WSL2: correr toda la red en una instancia Linux nativa en AWS.
Evita los problemas de virtualización/BIOS en Windows.

---

## 1. Crear la instancia EC2

En la consola de AWS → **EC2 → Launch instance**:

| Campo | Valor |
|-------|-------|
| Name | `pfi-fabric` |
| AMI | **Ubuntu Server 24.04 LTS** (64-bit x86) — también sirve 22.04. **NO** elegir variantes "with SQL Server" ni "Ubuntu Pro" |
| Tipo de instancia | **t3.large** (2 vCPU, 8 GB RAM) |
| Key pair | Crear o usar uno existente (`.pem`) — lo necesitás para SSH |
| Storage | **30 GB** gp3 |

### Security Group (firewall)

Para esta etapa todo corre **dentro** de la instancia, así que solo necesitás SSH:

| Tipo | Puerto | Origen |
|------|--------|--------|
| SSH  | 22     | **My IP** (tu IP pública, no `0.0.0.0/0`) |

> Cuando hagamos la app cliente y quieras accederla desde afuera, ahí evaluamos
> abrir puertos. Por ahora, dejá solo SSH.

### 💰 Costo

- t3.large ≈ **USD 0.083/hora** (~USD 2 por día completo encendida).
- **Apagá la instancia** (Stop, no Terminate) cuando no la uses: detenida no cobra
  cómputo, solo el disco (~USD 2.4/mes por 30 GB).

---

## 2. Conectarte por SSH

Desde PowerShell o terminal, en la carpeta donde está tu `.pem`:

```bash
# (una vez) restringir permisos de la key en Linux/WSL:
chmod 400 mi-key.pem

ssh -i mi-key.pem ubuntu@<IP-PUBLICA-DE-LA-EC2>
```

En Windows con PowerShell, si da error de permisos del `.pem`, usá la EC2
Instance Connect desde la consola web, o ajustá permisos del archivo.

---

## 3. Traer el proyecto a la instancia

**Opción A — clonar desde Git (recomendado si está en GitHub):**
```bash
git clone <URL-de-tu-repo>.git
cd PFI-Proyecto-Final
```

**Opción B — copiar desde tu máquina con scp:**
```bash
# desde tu PC (no dentro de la EC2):
scp -i mi-key.pem -r ./PFI-Proyecto-Final ubuntu@<IP-PUBLICA>:~/
```

---

## 4. Provisionar el entorno (Docker + Go)

Dentro de la instancia:

```bash
cd ~/PFI-Proyecto-Final/fabric/scripts
chmod +x bootstrap.sh
./bootstrap.sh
```

Esto instala Docker Engine + compose, Go, git y jq.

> **Importante:** al terminar, **cerrá y reabrí la sesión SSH** (o corré
> `newgrp docker`) para poder usar `docker` sin `sudo` y cargar el PATH de Go.

Verificá:
```bash
docker --version
docker compose version
go version
docker run hello-world   # debería bajar y correr sin sudo
```

---

## 5. Levantar la red completa

```bash
cd ~/PFI-Proyecto-Final/fabric

./network.sh install        # binarios + imágenes Docker (1 sola vez)
./network.sh up             # cripto + contenedores
./network.sh createChannel  # canal mychannel + peers
./network.sh deployCC       # chaincode prescriptions (endorsement AND de las 3 orgs) + prueba
```

Si todo salió bien, el último comando imprime el resultado de `ListPrescriptions`
con los 4 assets iniciales.

---

## 6. Apagar

```bash
./network.sh down           # baja la red Fabric y limpia artefactos
```

Y desde la consola de AWS, **Stop** la instancia para no seguir pagando cómputo.

---

## Checklist rápido

- [ ] Instancia t3.large Ubuntu 22.04 creada
- [ ] Security Group solo con SSH desde mi IP
- [ ] Conectado por SSH
- [ ] Proyecto clonado/copiado
- [ ] `bootstrap.sh` ejecutado y sesión reabierta
- [ ] `docker run hello-world` funciona sin sudo
- [ ] `./network.sh install && up && createChannel && deployCC` OK
- [ ] Instancia detenida (Stop) al terminar
