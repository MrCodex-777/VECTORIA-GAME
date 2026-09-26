"""Valida la retícula de las plantillas ASCII del EMPLEADO-07.

Regla: toda plantilla se escribe con ancho <= ANCHO_RETICULA (24);
_compose centra y empareja a 24. El frame compuesto debe ser
rectangular 24x34 y usar solo caracteres con paleta definida.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ANCHO = 24
ALTO_PIERNAS = 12


def main() -> int:
    from src.gfx.pixelart import SpriteBank as SB, PAL

    errores = []
    for nombre in ("HEAD", "TORSO_ROWS"):
        for i, fila in enumerate(getattr(SB, nombre)):
            if len(fila) > ANCHO:
                errores.append(f"{nombre}[{i}] ancho={len(fila)} > {ANCHO}")

    piernas = ["LEG_STAND", "LEG_W1", "LEG_W2", "LEG_W3", "LEG_W4",
               "LEG_RUN", "LEG_JUMP", "LEG_FALL"]
    for nombre in piernas:
        rows = getattr(SB, nombre)
        if len(rows) != ALTO_PIERNAS:
            errores.append(f"{nombre} alto={len(rows)} != {ALTO_PIERNAS}")
        for i, fila in enumerate(rows):
            if len(fila) > ANCHO:
                errores.append(f"{nombre}[{i}] ancho={len(fila)} > {ANCHO}")

    # todo frame compuesto: rectangular 24x34 y solo claves de paleta
    for fn in ("frame_idle", "frame_walk_a", "frame_walk_b", "frame_walk_c",
               "frame_walk_d", "frame_run", "frame_jump", "frame_fall"):
        mat = getattr(SB, fn)()
        if len(mat) != 34:
            errores.append(f"{fn}() alto={len(mat)} != 34")
        for i, fila in enumerate(mat):
            if len(fila) != ANCHO:
                errores.append(f"{fn}()[{i}] ancho={len(fila)}")
            for ch in fila:
                if ch not in PAL:
                    errores.append(f"{fn}()[{i}] carácter '{ch}' sin paleta")

    if errores:
        print("FALLO retícula sprites:")
        for e in errores:
            print("  -", e)
        return 1
    print(f"OK: plantillas y frames compuestos encajan en la retícula {ANCHO}x34.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
