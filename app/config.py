"""Configuración del centro de mando.

DOS MODOS, UNA REGLA QUE NO SE ROMPE
- `--demo`  : datos SINTÉTICOS. No toca ningún tenant. No necesita credenciales.
              Es el modo por defecto para que cualquiera lo vea funcionando ya.
- `--live`  : lee el tenant REAL vía Microsoft Graph, SOLO LECTURA.

La regla que manda sobre todo: esta herramienta NUNCA escribe en el tenant.
No hay una sola llamada POST/PATCH/PUT/DELETE a Graph en el código, y hay un
test que lo verifica (`tests/test_readonly_guarantee.py`). Si algún día alguien
agrega una, el test se vuelve rojo antes de que llegue a un tenant.

Los secretos NO viven en el repo. En modo `--live` la config se lee de un archivo
local (gitignored) o de variables de entorno. El archivo de ejemplo no tiene valores.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # PyYAML solo hace falta en modo --live
    yaml = None  # type: ignore

RAIZ = Path(__file__).resolve().parent.parent
CONFIG_LOCAL = RAIZ / "config.yaml"  # gitignored; el usuario lo crea desde el ejemplo


@dataclass
class Config:
    modo: str = "demo"            # "demo" | "live"
    tenant_id: str = ""
    client_id: str = ""
    # El secreto NUNCA se guarda en el objeto que se serializa a la UI.
    client_secret: str = field(default="", repr=False)
    host: str = "127.0.0.1"       # local por defecto: un dashboard SOC expuesto ES la fuga
    puerto: int = 8888
    # Cada permiso de Graph que la herramienta usa, para documentarlo en la UI.
    graph_scopes: tuple[str, ...] = (
        "AuditLog.Read.All",              # inicios de sesión fallidos
        "IdentityRiskyUser.Read.All",     # usuarios en riesgo
        "IdentityRiskEvent.Read.All",     # eventos de riesgo
        "User.Read.All",                  # inventario de usuarios
        "Device.Read.All",                # inventario de dispositivos + última ciudad
        "ServiceHealth.Read.All",         # estado de servicios de Microsoft 365
        "MailboxSettings.Read",           # reglas de reenvío externas (exfiltración)
    )

    @property
    def es_demo(self) -> bool:
        return self.modo != "live"

    def para_ui(self) -> dict:
        """Lo que la UI puede ver. NUNCA incluye el secreto."""
        return {
            "modo": self.modo,
            "tenant_id": self.tenant_id[:8] + "…" if self.tenant_id else "(demo)",
            "graph_scopes": list(self.graph_scopes),
            "solo_lectura": True,
        }


def cargar(modo: str = "demo") -> Config:
    """Carga la config. En demo no lee nada sensible. En live exige credenciales."""
    cfg = Config(modo=modo)
    if cfg.es_demo:
        return cfg

    if yaml is None:
        raise SystemExit("Modo --live necesita PyYAML: pip install -r requirements.txt")

    datos: dict = {}
    if CONFIG_LOCAL.exists():
        datos = yaml.safe_load(CONFIG_LOCAL.read_text(encoding="utf-8")) or {}

    # Las variables de entorno ganan sobre el archivo (útil en CI/contenedores).
    cfg.tenant_id = os.getenv("M365CC_TENANT_ID", datos.get("tenant_id", ""))
    cfg.client_id = os.getenv("M365CC_CLIENT_ID", datos.get("client_id", ""))
    cfg.client_secret = os.getenv("M365CC_CLIENT_SECRET", datos.get("client_secret", ""))
    cfg.host = datos.get("host", cfg.host)
    cfg.puerto = int(datos.get("puerto", cfg.puerto))

    faltan = [n for n, v in (
        ("tenant_id", cfg.tenant_id),
        ("client_id", cfg.client_id),
        ("client_secret", cfg.client_secret),
    ) if not v]
    if faltan:
        raise SystemExit(
            "Modo --live pero falta configurar: " + ", ".join(faltan) + ".\n"
            "Copiá config.example.yaml a config.yaml y completalo, "
            "o exportá M365CC_TENANT_ID / M365CC_CLIENT_ID / M365CC_CLIENT_SECRET."
        )
    return cfg
