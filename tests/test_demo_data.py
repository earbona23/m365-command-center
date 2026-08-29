from app.demo import demo_data


def test_snapshot_tiene_todas_las_secciones():
    s = demo_data.snapshot()
    for clave in ("kpis", "login_fallidos_serie", "usuarios_riesgo",
                  "salud_servicios", "exfiltracion", "dispositivos",
                  "dispositivos_por_ciudad"):
        assert clave in s, f"falta la sección {clave}"


def test_serie_login_cubre_24_horas():
    assert len(demo_data.snapshot()["login_fallidos_serie"]) == 24


def test_es_determinista():
    # Dos llamadas deben dar exactamente lo mismo: los tests dependen de ello
    # y dos personas viendo el demo deben ver idéntico.
    assert demo_data.snapshot() == demo_data.snapshot()


def test_kpis_coinciden_con_los_datos():
    s = demo_data.snapshot()
    assert s["kpis"]["alertas_exfiltracion"] == len(s["exfiltracion"])
    assert s["kpis"]["usuarios_riesgo_alto"] == sum(
        1 for r in s["usuarios_riesgo"] if r["nivel"] == "alto")


def test_demo_esta_rotulado_como_demo():
    assert demo_data.snapshot()["demo"] is True
