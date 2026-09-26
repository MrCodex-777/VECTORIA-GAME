"""
vectoria.entidades.player
=========================
EMPLEADO 07 — plataformas con inercia "humana" (sin frenado instantáneo:
el personaje pesa, y las consolas de la lore insisten en eso).

Colisiones AABB resueltas por ejes contra todos los Solid del nivel,
incluidas las plataformas móviles de las máquinas (se hereda su velocidad).
"""
from __future__ import annotations

import pygame
from .base import PhysicsBody


class Player(PhysicsBody):
    ANCHO, ALTO = 26, 44
    VEL_X = 3.6          # impulso horizontal por frame (inercial)
    SALTO = -10.8
    MAX_CAIDA = 17.0

    def __init__(self, x, y):
        super().__init__(x, y, self.ANCHO, self.ALTO)
        self.pies = False
        self.mirando = 1
        self._plataforma_ayer = None

    # ------------------------------------------------------------------ input
    def controlar(self, teclas) -> None:
        izq = teclas[pygame.K_LEFT] or teclas[pygame.K_a]
        der = teclas[pygame.K_RIGHT] or teclas[pygame.K_d]
        if izq and not der:
            self.vel.x -= self.VEL_X
            self.mirando = -1
        elif der and not izq:
            self.vel.x += self.VEL_X
            self.mirando = 1
        salto = teclas[pygame.K_SPACE] or teclas[pygame.K_w] or teclas[pygame.K_UP]
        if salto and self.pies:
            self.vel.y = self.SALTO
            self.pies = False

    # ------------------------------------------------------------- colisiones
    def mover_con_colision(self, dt, g_px, solidos) -> None:
        """Integración + resolución AABB eje X luego eje Y."""
        if self.vel.y < self.MAX_CAIDA:
            self.acc.y += g_px
        self.vel += self.acc
        self.vel.x *= 0.90
        self.acc.update(0, 0)
        paso = dt * 60.0

        # --- eje X
        self.pos.x += self.vel.x * paso
        r = self.rect
        for s in solidos:
            sr = s.plataforma_rect() if hasattr(s, "plataforma_rect") else s.rect
            if r.colliderect(sr):
                if self.vel.x > 0:
                    self.pos.x = sr.left - self.size[0]
                elif self.vel.x < 0:
                    self.pos.x = sr.right
                self.vel.x = 0
                r = self.rect

        # --- eje Y
        self.pos.y += self.vel.y * paso
        self.pies = False
        r = self.rect
        for s in solidos:
            sr = s.plataforma_rect() if hasattr(s, "plataforma_rect") else s.rect
            if r.colliderect(sr):
                if self.vel.y > 0:                       # aterrizaje
                    self.pos.y = sr.top - self.size[1]
                    self.vel.y = 0
                    self.pies = True
                    self._plataforma_ayer = s
                elif self.vel.y < 0:                     # techo
                    self.pos.y = sr.bottom
                    self.vel.y = 0.5
                r = self.rect
        # arrastre por plataforma móvil (la máquina mueve al jugador)
        p = self._plataforma_ayer
        if p is not None and getattr(p, "movil", False) and self.pies:
            self.pos.x += p.delta_x_mov * paso
            self.pos.y += p.delta_y_mov * paso

    # ------------------------------------------------------------------ render
    def draw(self, surf, cam):
        r = cam.to_screen(self.rect)
        cuerpo = pygame.Rect(r.x, r.y + 10, r.w, r.h - 10)
        pygame.draw.rect(surf, (220, 228, 232), cuerpo, border_radius=4)   # traje
        cabeza = pygame.Rect(r.x + 4, r.y, r.w - 8, 14)
        pygame.draw.rect(surf, (245, 200, 160), cabeza, border_radius=3)
        visor_x = r.x + (r.w - 12 if self.mirando > 0 else 4)
        pygame.draw.rect(surf, (60, 200, 210), (visor_x, r.y + 4, 8, 4))   # HUD guante
        badge = pygame.Rect(r.x + r.w // 2 - 3, r.y + 16, 6, 6)
        pygame.draw.rect(surf, (200, 60, 60), badge)                        # credencial
