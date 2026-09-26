"""
VECTORIA — punto de entrada.
    python main.py            → Bioma 0: Bosque (El Despertar)
Físicas reales vía src.fisicas.mas (SciPy). Ver docs/GDD_Vectoria.md.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from src.niveles import BosqueDespertar


def main():
    pygame.init()
    screen = pygame.display.set_mode((1024, 560))
    pygame.display.set_caption("VECTORIA — Bioma 0: El Despertar")
    clock = pygame.time.Clock()

    level = BosqueDespertar(screen)
    level.construir()

    corriendo = True
    while corriendo:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                corriendo = False
            elif level.manejar_evento(ev):
                continue
        teclas = pygame.key.get_pressed()
        level.update(dt, teclas)
        level.draw()
        pygame.display.flip()
        if level.estado == "VICTORIA":
            pygame.time.wait(3500)
            corriendo = False
    from src.gfx.pixelart import clear_tex_cache, SpriteBank
    clear_tex_cache()
    SpriteBank.clear_cache()
    pygame.quit()


if __name__ == "__main__":
    main()
