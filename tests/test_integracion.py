"""Pruebas de humo + integración headless del Bioma 0."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import pygame
pygame.init()
SCREEN = pygame.display.set_mode((1024, 560))

from src.fisicas.mas import PenduloIndustrial, ResortePlataforma, G_EARTH
from src.niveles import BosqueDespertar


class Keys(set):
    def __getitem__(self, k): return k in self


def test_matematica():
    p = PenduloIndustrial(2.44)
    assert abs(p.periodo - 3.14) < 0.02, p.periodo
    L = PenduloIndustrial.longitud_para_periodo(3.2)
    assert abs(L - 2.54) < 0.02, L
    r = ResortePlataforma(k=120 * (2*math.pi/2.0)**2, masa_plat=120)
    assert abs(r.periodo - 2.0) < 1e-9
    print("[ok] matemática: T_pend=2π√(L/g), T_resorte=2π√(m/k)")


def test_pipeline_nivel():
    lvl = BosqueDespertar(SCREEN); lvl.construir()
    dt = 1/60
    lvl.update(dt, Keys())                       # log de arranque automático
    assert lvl.estado == "REGISTRO"
    lvl.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    assert lvl.estado == "JUGANDO"
    # calibración por consola (debajo del capó, pero vía API pública ajustar())
    for c in (lvl.consola1, lvl.consola2, lvl.consola3):
        for _ in range(2000):
            if c.maquina.es_calibrada(c.objetivo_T): break
            err = (c.maquina.periodo - c.objetivo_T)/c.objetivo_T
            c.ajustar(-1 if err > 0 else 1)
        assert c.maquina.es_calibrada(c.objetivo_T), c.objetivo_T
    # 120 s de simulación con el jugador quieto sobre plataforma: sin crashes
    for i in range(60*120):
        lvl.update(dt, Keys([pygame.K_RIGHT]))
        lvl.draw()
        if lvl.reloj > 100: break
    print(f"[ok] pipeline: {int(lvl.reloj)}s simulados, estado={lvl.estado}")


def test_victoria_y_render():
    lvl = BosqueDespertar(SCREEN); lvl.construir()
    dt = 1/60
    lvl.update(dt, Keys()); lvl.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    assert not lvl.objetivo_cumplido()
    lvl.reg_d.usado = True
    lvl.player.pos.update(4170, 300)
    lvl.update(dt, Keys())
    assert lvl.estado == "VICTORIA", lvl.estado
    lvl.draw()
    pygame.image.save(SCREEN, "assets/ui/captura_victoria.png")
    # overlay de consola
    lvl2 = BosqueDespertar(SCREEN); lvl2.construir()
    lvl2.update(dt, Keys()); lvl2.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    lvl2.consola1.abierta = True; lvl2.consola_activa = lvl2.consola1
    lvl2.update(dt, Keys()); lvl2.draw()
    pygame.image.save(SCREEN, "assets/ui/captura_consola.png")
    print("[ok] victoria + renders guardados")


if __name__ == "__main__":
    test_matematica()
    test_pipeline_nivel()
    test_victoria_y_render()
    print("TODAS LAS PRUEBAS PASAN")
