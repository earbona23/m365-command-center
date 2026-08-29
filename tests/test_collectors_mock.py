"""Los colectores reales, probados con un Graph FALSO — sin tenant, sin red."""
from app import collectors


class GraphFalso:
    """Devuelve respuestas programadas por ruta. Solo get/get_all, como el real."""
    def __init__(self, rutas):
        self.rutas = rutas

    def _match(self, ruta):
        # La MÁS específica gana: "/users" no debe robarle a
        # "/users/x@x/mailboxSettings" (el bug de subcadena de siempre).
        mejor = None
        for patron, resp in self.rutas.items():
            if patron in ruta and (mejor is None or len(patron) > len(mejor[0])):
                mejor = (patron, resp)
        return mejor[1] if mejor else None

    def get(self, ruta, params=None):
        return self._match(ruta) or {}

    def get_all(self, ruta, params=None):
        resp = self._match(ruta)
        if resp:
            yield from resp.get("value", [])


def test_login_fallidos_agrega_por_usuario_ip():
    g = GraphFalso({"/auditLogs/signIns": {"value": [
        {"userPrincipalName": "a@x.com", "ipAddress": "1.1.1.1",
         "createdDateTime": "2026-08-29T21:00:00Z",
         "location": {"city": "Santiago"}, "status": {"failureReason": "mal pass"}},
        {"userPrincipalName": "a@x.com", "ipAddress": "1.1.1.1",
         "createdDateTime": "2026-08-29T21:10:00Z",
         "location": {"city": "Santiago"}, "status": {"failureReason": "mal pass"}},
    ]}})
    serie, top = collectors.login_fallidos(g)
    assert len(serie) == 24
    assert top[0]["intentos"] == 2
    assert top[0]["usuario"] == "a@x.com"


def test_riesgo_excluye_nivel_none():
    g = GraphFalso({"/identityProtection/riskyUsers": {"value": [
        {"userPrincipalName": "r@x.com", "riskLevel": "high", "riskState": "atRisk"},
        {"userPrincipalName": "n@x.com", "riskLevel": "none", "riskState": "none"},
    ]}})
    filas = collectors.usuarios_en_riesgo(g)
    assert len(filas) == 1 and filas[0]["nivel"] == "alto"


def test_exfiltracion_solo_marca_reenvio_a_dominio_externo():
    g = GraphFalso({
        "/users": {"value": [
            {"userPrincipalName": "interno@empresa.com"},
            {"userPrincipalName": "fugado@empresa.com"},
        ]},
        "/users/interno@empresa.com/mailboxSettings": {"forwardingSmtpAddress": "smtp:jefe@empresa.com"},
        "/users/fugado@empresa.com/mailboxSettings": {"forwardingSmtpAddress": "smtp:ladron@gmail.com"},
    })
    filas = collectors.exfiltracion(g)
    assert len(filas) == 1, "reenvío interno NO es exfiltración; solo el externo"
    assert filas[0]["usuario"] == "fugado@empresa.com"


def test_snapshot_no_revienta_si_un_panel_falla():
    from app.graph import GraphError

    class GraphRoto:
        def get(self, ruta, params=None): raise GraphError("403")
        def get_all(self, ruta, params=None):
            raise GraphError("403")
            yield  # pragma: no cover

    s = collectors.snapshot(GraphRoto())
    assert s["demo"] is False
    assert s["usuarios_riesgo"] == []  # panel vacío, no excepción
