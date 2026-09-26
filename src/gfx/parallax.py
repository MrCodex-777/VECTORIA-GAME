"""
vectoria.gfx.parallax
=====================
Fondos pixel-art en capas con parallax para el Bioma Bosque. Cada capa es
una Surface teselable generada UNA vez (determinista) y desplazada a una
velocidad fracción de la cámara. Las capas lejanas usan paleta desaturada
(efecto niebla/atmósfera); las cercanas añaden vegetación muerta, cables
colgantes y estructuras TECH-SYNC en ruina.

Contrato: ``ParallaxBosque(surface).draw(cam_x)`` pinta todas las capas;
``capa_media()`` permite a los niveles dibujar decoraciones entre capas.
"""
from __future__ import annotations

import math
import random
import pygame

PX = 2  # retícula pixel art


def _pal(rng: random.Random, base, jitter=10):
    j = rng.randint(-jitter, jitter)
    return tuple(max(0, min(255, c + j)) for c in base)


class ParallaxBosque:
    ALTURA_CAPAS = (0.62, 0.78, 0.92)   # alto relativo de cada silueta

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        w, h = screen.get_size()
        self.w, self.h = w, h
        self.capas: list[tuple[float, pygame.Surface, int]] = []
        self._construir_capa(velocidad=0.12, col_base=(24, 40, 34),
                            alto=int(h * 0.62), semilla=11, tipo="troncos")
        self._construir_capa(velocidad=0.30, col_base=(34, 56, 42),
                             alto=int(h * 0.74), semilla=23, tipo="troncos")
        self._construir_capa(velocidad=0.55, col_base=(46, 74, 52),
                             alto=int(h * 0.88), semilla=37, tipo="ruina")
        self.hojadin = self._construir_hojadin(semilla=91)

    # ------------------------------------------------------------- builders
    def _construir_capa(self, velocidad, col_base, alto, semilla, tipo):
        rng = random.Random(semilla)
        cw, ch = 480, self.h
        surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
        base_y = ch - 30

        if tipo == "troncos":
            n_troncos = rng.randint(6, 9)
            xs = sorted(rng.randrange(0, cw - 30) for _ in range(n_troncos))
            for x in xs:
                tw = rng.choice([12, 16, 20, 26])
                th = rng.randint(alto // 2, alto)
                col = _pal(rng, col_base, 8)
                top = base_y - th
                pygame.draw.rect(surf, col, (x, top, tw, th))
                # corteza: vetas verticales oscuras
                oscuro = tuple(max(0, c - 14) for c in col)
                for k in range(1, tw, 4):
                    if rng.random() < 0.6:
                        pygame.draw.line(surf, oscuro, (x + k, top + 4),
                                         (x + k, base_y - 6), PX)
                # ramas quebradas
                for _ in range(rng.randint(1, 3)):
                    by = rng.randrange(top + 8, base_y - 30)
                    lrg = rng.randint(10, 26) * (1 if rng.random() < .5 else -1)
                    pygame.draw.line(surf, oscuro, (x + tw // 2, by),
                                     (x + tw // 2 + lrg, by - rng.randint(4, 14)), PX)
                # copa irregular (hongo de dosel)
                copa_w = tw + rng.randint(18, 42)
                copa_col = _pal(rng, tuple(c + 10 for c in col_base), 6)
                for i in range(0, copa_w, PX):
                    yy = top - int(10 * math.sin(math.pi * i / max(1, copa_w)))
                    pygame.draw.rect(surf, copa_col,
                                     (x + tw // 2 - copa_w // 2 + i, yy, PX,
                                      top - yy + rng.randint(2, 8)))
        else:  # "ruina": pilares TECH-SYNC rotos + cables
            for _ in range(rng.randint(3, 5)):
                px_ = rng.randrange(0, cw - 60)
                pw = rng.choice([26, 34, 44])
                ph = rng.randint(alto // 3, alto // 2)
                col = _pal(rng, (70, 78, 74), 8)
                top = base_y - ph
                pygame.draw.rect(surf, col, (px_, top, pw, ph))
                claro = tuple(min(255, c + 26) for c in col)
                oscuro = tuple(max(0, c - 18) for c in col)
                # diente roto en el borde superior
                for bx in range(px_, px_ + pw, PX):
                    dy = rng.choice([0, 0, 0, 4, 8, 12])
                    pygame.draw.rect(surf, oscuro, (bx, top, PX, dy))
                # ventanas oscuras
                for wy in range(top + 16, base_y - 12, 22):
                    for wx in range(px_ + 6, px_ + pw - 8, 14):
                        if rng.random() < 0.7:
                            pygame.draw.rect(surf, (18, 24, 22), (wx, wy, 8, 10))
                            pygame.draw.rect(surf, claro, (wx, wy, 8, 1), 1)
                # enredaderas sobre el pilar
                vid = _pal(rng, (52, 96, 56), 10)
                vx = rng.randrange(px_, px_ + pw)
                vy = top
                while vy < base_y - 8:
                    pygame.draw.rect(surf, vid, (vx, vy, PX, PX * 3))
                    vx += rng.choice([-PX, 0, PX])
                    vy += PX * 2
            # cables colgantes (catenarias simples)
            cable = (30, 34, 32)
            for _ in range(rng.randint(2, 4)):
                x0 = rng.randrange(0, cw - 120)
                x1 = x0 + rng.randint(70, 160)
                y0 = rng.randrange(20, 120)
                y1 = y0 + rng.randint(-20, 40)
                sag = rng.randint(14, 30)
                pts = []
                for t in range(0, 11):
                    f = t / 10
                    xx = x0 + (x1 - x0) * f
                    yy = y0 + (y1 - y0) * f + sag * math.sin(math.pi * f)
                    pts.append((int(xx), int(yy)))
                pygame.draw.lines(surf, cable, False, pts, PX)

        # suelo continuo de la capa
        pygame.draw.rect(surf, _pal(rng, tuple(max(0, c - 10) for c in col_base), 4),
                         (0, base_y, cw, self.h - base_y))
        self.capas.append((velocidad, surf, cw))

    def _construir_hojadin(self, semilla):
        """Partículas ambientales: esporas/hojas que flotan (no haceScroll)."""
        rng = random.Random(semilla)
        self._semillas_p = [(rng.uniform(0, self.w), rng.uniform(0, self.h),
                             rng.uniform(0.2, 0.9), rng.choice([(120, 170, 90),
                             (160, 200, 120), (90, 140, 80)]))
                            for _ in range(26)]
        return None

    # ------------------------------------------------------------------ API
    def draw(self, cam_x: float, t: float = 0.0):
        s = self.screen
        # cielo con degradado duro en bandas (pixel art sin antialiasing)
        bandas = [(20, 30, 30), (22, 36, 33), (26, 42, 36), (30, 48, 40),
                  (36, 56, 44)]
        bh = self.h / len(bandas)
        for i, col in enumerate(bandas):
            pygame.draw.rect(s, col, (0, int(i * bh), self.w, int(bh) + 1))
        # luna/nodo geostacionario apagado (guiño lore: red de satélites)
        mx, my = int(self.w * 0.78), int(self.h * 0.16)
        pygame.draw.circle(s, (58, 70, 66), (mx, my), 18)
        pygame.draw.circle(s, (44, 54, 52), (mx - 5, my - 4), 5)
        pygame.draw.circle(s, (44, 54, 52), (mx + 6, my + 3), 3)
        # halo de contaminación
        halo = pygame.Surface((90, 90), pygame.SRCALPHA)
        pygame.draw.circle(halo, (70, 90, 80, 40), (45, 45), 44)
        s.blit(halo, (mx - 45, my - 45))

        for vel, surf, cw in self.capas:
            ox = int(-cam_x * vel) % cw
            for j in range(-1, self.w // cw + 2):
                s.blit(surf, (j * cw - ox, 0))

        # hojines flotando (deriva sinusoidal, independientes de cámara)
        for (bx, by, fase, col) in self._semillas_p:
            x = (bx + t * 14 * fase) % (self.w + 20) - 10
            y = (by + math.sin(t * 0.8 + fase * 9) * 18 + t * 6 * fase) % self.h
            pygame.draw.rect(s, col, (int(x) // PX * PX, int(y) // PX * PX,
                                       PX, PX))
