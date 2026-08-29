"""El servidor sirve el dashboard y la API en modo demo, sin red externa."""
import json
import urllib.request

from app.config import cargar
from app.server import crear_servidor


def _levantar():
    cfg = cargar("demo")
    cfg.puerto = 0  # que el SO elija un puerto libre
    srv = crear_servidor(cfg)
    import threading
    threading.Thread(target=srv.handle_request, daemon=True).start()
    return srv


def _pedir(srv, ruta):
    puerto = srv.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{puerto}{ruta}", timeout=5) as r:
        return r.status, r.read()


def test_snapshot_endpoint_devuelve_json_demo():
    srv = crear_servidor(cargar("demo"))
    import threading
    t = threading.Thread(target=srv.handle_request, daemon=True)
    t.start()
    puerto = srv.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/snapshot", timeout=5) as r:
        assert r.status == 200
        d = json.loads(r.read())
    assert d["demo"] is True and "kpis" in d
    srv.server_close()


def test_config_endpoint_no_filtra_secreto():
    srv = crear_servidor(cargar("demo"))
    import threading
    threading.Thread(target=srv.handle_request, daemon=True).start()
    puerto = srv.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/config", timeout=5) as r:
        d = json.loads(r.read())
    assert "client_secret" not in d
    assert d["solo_lectura"] is True
    srv.server_close()
