"""Datos DEMO sintéticos, deterministas.

POR QUÉ EXISTE
Un dashboard que no se puede ver no consigue una sola estrella. Este módulo genera
un tenant ficticio completo para que cualquiera clone el repo y lo vea funcionando
sin credenciales y sin tocar ningún sistema real.

HONESTIDAD
Estos datos son INVENTADOS y la UI los rotula "DATOS DEMO" en grande. Nada de esto
sale de un tenant real. Es determinista (sin azar) para que los tests puedan afirmar
sobre valores exactos y para que dos personas vean lo mismo.
"""
from __future__ import annotations

# Semilla fija: nombres y ciudades ficticios de un tenant de ejemplo.
_USUARIOS = [
    ("ana.gomez", "Ana Gómez", "Santo Domingo"),
    ("luis.perez", "Luis Pérez", "Santiago"),
    ("carla.mota", "Carla Mota", "Santo Domingo"),
    ("jose.ramos", "José Ramos", "La Romana"),
    ("elena.diaz", "Elena Díaz", "Punta Cana"),
    ("marco.reyes", "Marco Reyes", "Santiago"),
    ("sofia.luna", "Sofía Luna", "Santo Domingo"),
    ("diego.mena", "Diego Mena", "San Pedro"),
]


def _serie_login_fallidos() -> list[dict]:
    """24 horas de intentos fallidos, con un pico nocturno (patrón de fuerza bruta)."""
    base = [1, 0, 2, 1, 0, 0, 1, 3, 4, 2, 3, 2, 1, 2, 1, 0, 1, 2, 3, 5, 9, 14, 7, 2]
    return [{"hora": f"{h:02d}:00", "fallidos": n} for h, n in enumerate(base)]


def _intentos_fallidos() -> list[dict]:
    return [
        {"usuario": "ana.gomez@contoso-demo.com", "ip": "45.**.**.12",
         "ciudad": "Bucarest, RO", "intentos": 14, "motivo": "Contraseña incorrecta"},
        {"usuario": "admin@contoso-demo.com", "ip": "185.**.**.7",
         "ciudad": "Lagos, NG", "intentos": 9, "motivo": "Usuario bloqueado"},
        {"usuario": "luis.perez@contoso-demo.com", "ip": "190.**.**.44",
         "ciudad": "Santiago, DO", "intentos": 3, "motivo": "MFA no completado"},
        {"usuario": "jose.ramos@contoso-demo.com", "ip": "201.**.**.9",
         "ciudad": "Santo Domingo, DO", "intentos": 2, "motivo": "Contraseña incorrecta"},
    ]


def _usuarios_en_riesgo() -> list[dict]:
    return [
        {"usuario": "ana.gomez@contoso-demo.com", "nivel": "alto",
         "estado": "activo", "detalle": "Viaje imposible: RD → Rumanía en 20 min"},
        {"usuario": "admin@contoso-demo.com", "nivel": "alto",
         "estado": "en_riesgo", "detalle": "Múltiples fallos desde IP anónima (Tor)"},
        {"usuario": "carla.mota@contoso-demo.com", "nivel": "medio",
         "estado": "activo", "detalle": "Inicio desde dirección IP no habitual"},
        {"usuario": "marco.reyes@contoso-demo.com", "nivel": "bajo",
         "estado": "remediado", "detalle": "Filtración de credenciales (ya cambiada)"},
    ]


def _salud_servicios() -> list[dict]:
    return [
        {"servicio": "Exchange Online", "estado": "saludable"},
        {"servicio": "Microsoft Teams", "estado": "saludable"},
        {"servicio": "SharePoint Online", "estado": "degradado",
         "detalle": "Latencia elevada en la región Este de EE.UU."},
        {"servicio": "Microsoft Entra ID", "estado": "saludable"},
        {"servicio": "Microsoft Intune", "estado": "saludable"},
        {"servicio": "Defender for Office 365", "estado": "incidente",
         "detalle": "Retraso en el escaneo de adjuntos"},
    ]


def _exfiltracion() -> list[dict]:
    """Reglas de reenvío a dominios externos = señal clásica de buzón comprometido."""
    return [
        {"usuario": "carla.mota@contoso-demo.com", "tipo": "Regla de reenvío externo",
         "destino": "recolector@gmail.com", "severidad": "alta",
         "detalle": "Reenvía TODO el correo entrante a un dominio personal"},
        {"usuario": "diego.mena@contoso-demo.com", "tipo": "Envío externo masivo",
         "destino": "37 destinatarios @proton.me", "severidad": "media",
         "detalle": "Adjuntó una hoja de cálculo de 12 MB fuera de la empresa"},
    ]


def _dispositivos() -> list[dict]:
    """Ubicación a nivel CIUDAD (desde el último inicio de sesión), no GPS."""
    return [
        {"dispositivo": "LAPTOP-ANA", "usuario": "ana.gomez", "ciudad": "Bucarest, RO",
         "cumple": False, "ultimo_visto": "hace 20 min", "nota": "Ciudad inesperada"},
        {"dispositivo": "LAPTOP-LUIS", "usuario": "luis.perez", "ciudad": "Santiago, DO",
         "cumple": True, "ultimo_visto": "hace 5 min", "nota": ""},
        {"dispositivo": "PC-CARLA", "usuario": "carla.mota", "ciudad": "Santo Domingo, DO",
         "cumple": True, "ultimo_visto": "hace 2 h", "nota": ""},
        {"dispositivo": "LAPTOP-JOSE", "usuario": "jose.ramos", "ciudad": "La Romana, DO",
         "cumple": False, "ultimo_visto": "hace 1 día", "nota": "Sin cifrado de disco"},
        {"dispositivo": "PC-ELENA", "usuario": "elena.diaz", "ciudad": "Punta Cana, DO",
         "cumple": True, "ultimo_visto": "hace 30 min", "nota": ""},
    ]


def _por_ciudad(dispositivos: list[dict]) -> list[dict]:
    conteo: dict[str, int] = {}
    for d in dispositivos:
        conteo[d["ciudad"]] = conteo.get(d["ciudad"], 0) + 1
    return sorted(
        ({"ciudad": c, "dispositivos": n} for c, n in conteo.items()),
        key=lambda x: -x["dispositivos"],
    )


def snapshot() -> dict:
    """El estado completo del tenant DEMO en un solo objeto — lo que consume la UI."""
    dispositivos = _dispositivos()
    exfil = _exfiltracion()
    riesgo = _usuarios_en_riesgo()
    fallidos = _intentos_fallidos()
    servicios = _salud_servicios()
    return {
        "demo": True,
        "kpis": {
            "usuarios": len(_USUARIOS),
            "intentos_fallidos_24h": sum(x["fallidos"] for x in _serie_login_fallidos()),
            "usuarios_riesgo_alto": sum(1 for r in riesgo if r["nivel"] == "alto"),
            "alertas_exfiltracion": len(exfil),
            "servicios_con_problema": sum(1 for s in servicios if s["estado"] != "saludable"),
            "dispositivos_no_cumplen": sum(1 for d in dispositivos if not d["cumple"]),
        },
        "login_fallidos_serie": _serie_login_fallidos(),
        "login_fallidos_top": fallidos,
        "usuarios_riesgo": riesgo,
        "salud_servicios": servicios,
        "exfiltracion": exfil,
        "dispositivos": dispositivos,
        "dispositivos_por_ciudad": _por_ciudad(dispositivos),
    }
