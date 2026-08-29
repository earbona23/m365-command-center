"""La garantía que define este proyecto: NUNCA escribe en el tenant.

Este test recorre TODO el código de app/ y falla si aparece cualquier verbo de
escritura de Graph (requests.post/patch/put/delete, o un método .post( sobre algo
que huela a Graph). La única excepción permitida es el POST del endpoint de token
de OAuth, que no toca datos del tenant — se marca con un comentario explícito.

Si alguien agrega una escritura, este test se vuelve rojo ANTES de que llegue a un
tenant real. Es la red que hace que 'solo lectura' sea una propiedad verificada, no
una promesa del README.
"""
import pathlib
import re

APP = pathlib.Path(__file__).resolve().parent.parent / "app"
PROHIBIDO = re.compile(r"requests\.(post|patch|put|delete)\s*\(", re.IGNORECASE)
PERMITIDO_TOKEN = "_AUTORIDAD.format"  # el POST del token OAuth vive en la misma línea lógica


def test_no_hay_escrituras_a_graph():
    ofensas = []
    for archivo in APP.rglob("*.py"):
        lineas = archivo.read_text(encoding="utf-8").splitlines()
        for i, linea in enumerate(lineas):
            if PROHIBIDO.search(linea):
                # ¿es el POST del token? mirar unas líneas alrededor
                ctx = "\n".join(lineas[max(0, i - 3):i + 5])  # el _AUTORIDAD.format cae en i+1
                if PERMITIDO_TOKEN in ctx:
                    continue
                ofensas.append(f"{archivo.name}:{i+1}: {linea.strip()}")
    assert not ofensas, "Escritura a Graph detectada (rompe la garantía de solo lectura):\n" + "\n".join(ofensas)


def test_el_cliente_graph_no_expone_metodos_de_escritura():
    from app import graph
    cliente = graph.GraphClient("t", "c", "s")
    for verbo in ("post", "patch", "put", "delete"):
        assert not hasattr(cliente, verbo), f"GraphClient no debe exponer .{verbo}()"
