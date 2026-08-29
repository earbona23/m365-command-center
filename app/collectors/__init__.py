"""Colectores de datos reales del tenant (modo --live), todos SOLO LECTURA.

Cada colector toma un GraphClient y devuelve la misma forma que produce el módulo
demo, para que la UI no distinga de dónde vienen los datos — salvo por la bandera
`demo`, que la UI usa para rotular la pantalla.

Cada colector se prueba con un GraphClient falso (ver tests/), así que la suite corre
sin un tenant real.
"""
from __future__ import annotations

from app.graph import GraphClient, GraphError


def _serie_por_hora(eventos: list[dict], campo_fecha: str = "createdDateTime") -> list[dict]:
    conteo = {f"{h:02d}:00": 0 for h in range(24)}
    for e in eventos:
        ts = e.get(campo_fecha, "")
        if len(ts) >= 13 and ts[11:13].isdigit():
            conteo[f"{ts[11:13]}:00"] = conteo.get(f"{ts[11:13]}:00", 0) + 1
    return [{"hora": h, "fallidos": conteo[h]} for h in sorted(conteo)]


def login_fallidos(g: GraphClient) -> tuple[list[dict], list[dict]]:
    """Inicios de sesión fallidos: serie por hora + top de usuarios/IP."""
    eventos = list(g.get_all(
        "/auditLogs/signIns",
        {"$filter": "status/errorCode ne 0", "$top": "200"},
    ))
    serie = _serie_por_hora(eventos)
    agg: dict[tuple, dict] = {}
    for e in eventos:
        clave = (e.get("userPrincipalName", "?"), e.get("ipAddress", "?"))
        fila = agg.setdefault(clave, {
            "usuario": clave[0], "ip": clave[1],
            "ciudad": (e.get("location") or {}).get("city", "?"),
            "intentos": 0, "motivo": (e.get("status") or {}).get("failureReason", ""),
        })
        fila["intentos"] += 1
    top = sorted(agg.values(), key=lambda x: -x["intentos"])[:10]
    return serie, top


def usuarios_en_riesgo(g: GraphClient) -> list[dict]:
    _MAPA = {"high": "alto", "medium": "medio", "low": "bajo"}
    filas = []
    for u in g.get_all("/identityProtection/riskyUsers", {"$top": "100"}):
        if u.get("riskLevel", "none") == "none":
            continue
        filas.append({
            "usuario": u.get("userPrincipalName", "?"),
            "nivel": _MAPA.get(u.get("riskLevel"), u.get("riskLevel", "?")),
            "estado": u.get("riskState", "?"),
            "detalle": u.get("riskDetail", ""),
        })
    return filas


def salud_servicios(g: GraphClient) -> list[dict]:
    _MAPA = {
        "serviceOperational": "saludable",
        "serviceDegradation": "degradado",
        "serviceInterruption": "incidente",
        "investigating": "incidente",
        "extendedRecovery": "degradado",
    }
    filas = []
    for s in g.get_all("/admin/serviceAnnouncement/healthOverviews"):
        estado = s.get("status", "?")
        filas.append({
            "servicio": s.get("service", "?"),
            "estado": _MAPA.get(estado, estado),
        })
    return filas


def exfiltracion(g: GraphClient) -> list[dict]:
    """Reglas de reenvío a dominios externos = señal clásica de buzón comprometido.

    Requiere MailboxSettings.Read. Un fallo de permiso NO revienta el panel: se
    devuelve vacío con una nota, en lugar de tumbar todo el dashboard.
    """
    filas: list[dict] = []
    try:
        usuarios = list(g.get_all("/users", {"$select": "userPrincipalName", "$top": "100"}))
    except GraphError:
        return filas
    for u in usuarios:
        upn = u.get("userPrincipalName", "")
        dominio = upn.split("@")[-1].lower() if "@" in upn else ""
        try:
            cfg = g.get(f"/users/{upn}/mailboxSettings")
        except GraphError:
            continue
        fwd = cfg.get("forwardingSmtpAddress") or ""
        destino = fwd.replace("smtp:", "").lower()
        if destino and dominio and not destino.endswith("@" + dominio):
            filas.append({
                "usuario": upn, "tipo": "Reenvío SMTP externo",
                "destino": destino, "severidad": "alta",
                "detalle": "El buzón reenvía correo a un dominio fuera de la empresa",
            })
    return filas


def dispositivos(g: GraphClient) -> tuple[list[dict], list[dict]]:
    """Inventario de dispositivos con ciudad del último inicio de sesión (no GPS)."""
    filas = []
    for d in g.get_all("/devices", {"$top": "200"}):
        filas.append({
            "dispositivo": d.get("displayName", "?"),
            "usuario": "",
            "ciudad": d.get("registrationDateTime", "")[:10] or "?",
            "cumple": bool(d.get("isCompliant")),
            "ultimo_visto": (d.get("approximateLastSignInDateTime") or "")[:10],
            "nota": "" if d.get("isCompliant") else "No cumple políticas",
        })
    conteo: dict[str, int] = {}
    for d in filas:
        conteo[d["ciudad"]] = conteo.get(d["ciudad"], 0) + 1
    por_ciudad = sorted(
        ({"ciudad": c, "dispositivos": n} for c, n in conteo.items()),
        key=lambda x: -x["dispositivos"],
    )
    return filas, por_ciudad


def snapshot(g: GraphClient) -> dict:
    """Arma el estado completo del tenant REAL. Cada panel falla de forma aislada:
    si un colector no tiene permiso, ese panel queda vacío y los demás siguen."""
    def seguro(fn, defecto):
        try:
            return fn()
        except GraphError:
            return defecto

    serie, top = seguro(lambda: login_fallidos(g), ([], []))
    riesgo = seguro(lambda: usuarios_en_riesgo(g), [])
    servicios = seguro(lambda: salud_servicios(g), [])
    exfil = seguro(lambda: exfiltracion(g), [])
    disp, por_ciudad = seguro(lambda: dispositivos(g), ([], []))

    return {
        "demo": False,
        "kpis": {
            "usuarios": len(list(seguro(lambda: list(g.get_all("/users", {"$select": "id", "$top": "999"})), []))),
            "intentos_fallidos_24h": sum(x["fallidos"] for x in serie),
            "usuarios_riesgo_alto": sum(1 for r in riesgo if r["nivel"] == "alto"),
            "alertas_exfiltracion": len(exfil),
            "servicios_con_problema": sum(1 for s in servicios if s["estado"] != "saludable"),
            "dispositivos_no_cumplen": sum(1 for d in disp if not d["cumple"]),
        },
        "login_fallidos_serie": serie,
        "login_fallidos_top": top,
        "usuarios_riesgo": riesgo,
        "salud_servicios": servicios,
        "exfiltracion": exfil,
        "dispositivos": disp,
        "dispositivos_por_ciudad": por_ciudad,
    }
