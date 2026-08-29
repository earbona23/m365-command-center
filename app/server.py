"""Servidor del centro de mando: sirve el dashboard y la API de datos.

Usa solo la biblioteca estándar (http.server) — sin framework web. Menos
dependencias = menos superficie de ataque, y arranca sin instalar casi nada en modo
demo. Se ata a 127.0.0.1 por defecto: un dashboard SOC accesible desde internet es
justamente la fuga que este proyecto ayuda a detectar.
"""
from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.config import Config, cargar

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"


def construir_snapshot(cfg: Config) -> dict:
    if cfg.es_demo:
        from app.demo import demo_data
        return demo_data.snapshot()
    from app import collectors
    from app.graph import GraphClient
    g = GraphClient(cfg.tenant_id, cfg.client_id, cfg.client_secret)
    return collectors.snapshot(g)


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *a, cfg: Config, **k) -> None:
        self._cfg = cfg
        super().__init__(*a, **k)

    def _json(self, obj: dict, code: int = 200) -> None:
        cuerpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        # Endurecimiento básico: sin iframes de terceros, sin sniffing de tipo.
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self) -> None:
        ruta = self.path.split("?")[0]
        if ruta in ("/", "/index.html"):
            html = DASHBOARD.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(html)
        elif ruta == "/api/config":
            self._json(self._cfg.para_ui())
        elif ruta == "/api/snapshot":
            try:
                self._json(construir_snapshot(self._cfg))
            except Exception as e:  # noqa: BLE001 — el servidor no debe caerse por un panel
                self._json({"error": str(e)}, 502)
        else:
            self._json({"error": "no encontrado"}, 404)

    def log_message(self, *a) -> None:  # silenciar el log ruidoso por defecto
        pass


def crear_servidor(cfg: Config) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((cfg.host, cfg.puerto), partial(Handler, cfg=cfg))


def main() -> None:
    p = argparse.ArgumentParser(description="Centro de mando de seguridad M365 (solo lectura)")
    p.add_argument("--live", action="store_true",
                   help="Leer el tenant REAL vía Graph (por defecto: datos demo)")
    p.add_argument("--host", default=None, help="Interfaz (por defecto 127.0.0.1)")
    p.add_argument("--puerto", type=int, default=None)
    args = p.parse_args()

    cfg = cargar(modo="live" if args.live else "demo")
    if args.host:
        cfg.host = args.host
    if args.puerto:
        cfg.puerto = args.puerto

    etiqueta = "TENANT REAL (solo lectura)" if not cfg.es_demo else "DATOS DEMO"
    print(f"Centro de mando  ·  {etiqueta}")
    print(f"Abrí:  http://{cfg.host}:{cfg.puerto}")
    if cfg.host not in ("127.0.0.1", "localhost"):
        print("  ⚠  Lo estás exponiendo fuera de localhost. Un dashboard SOC expuesto")
        print("     filtra datos del tenant. Poné una autenticación delante o no lo hagas.")
    srv = crear_servidor(cfg)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")


if __name__ == "__main__":
    main()
