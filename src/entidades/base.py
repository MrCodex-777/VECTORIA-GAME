"""
vectoria.entidades.base
=======================
Jerarquía raíz de objetos del mundo:

    Entity                 (posición, render, update)
      ├── PhysicsBody      (velocidad, aceleración, integración semi-implícita)
      │     ├── Solid      (colisionable AABB — plataformas, muros, peligro)
      │     └── Player     (ver player.py)
      └── Interactable     (zona de acción con tecla E — consolas, registros)

Convención: coordenadas lógicas en píxeles; las entidades "físicas"
(PenduloMaquina, etc.) guardan además su estado SI y lo proyectan a pantalla.
"""
from __future__ import annotations

import pygame


class Entity:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.pos = pygame.math.Vector2(x, y)
        self.alive = True

    @property
    def rect(self) -> pygame.Rect:
        raise NotImplementedError

    def update(self, dt: float, level) -> None:
        pass

    def draw(self, surf: pygame.Surface, cam: "Camera") -> None:
        raise NotImplementedError


class PhysicsBody(Entity):
    """Cuerpo con cinemática propia. Gravedad desactivable por entidad."""

    gravedad = True

    def __init__(self, x, y, w, h, vx=0.0, vy=0.0):
        super().__init__(x, y)
        self.size = (w, h)
        self.vel = pygame.math.Vector2(vx, vy)
        self.acc = pygame.math.Vector2(0, 0)

    @property
    def rect(self):
        return pygame.Rect(int(self.pos.x), int(self.pos.y), *self.size)

    def integrar(self, dt: float, g_px: float) -> None:
        if self.gravedad:
            self.acc.y += g_px
        self.vel += self.acc
        self.vel.x *= 0.92          # fricción de aire/rueda horizontal
        self.pos += self.vel * dt * 60.0
        self.acc.update(0, 0)


class Solid(PhysicsBody):
    """Plataforma/muro estático colisionable. ``peligroso=True`` mata al tocar."""

    def __init__(self, x, y, w, h, color=(90, 100, 95), peligroso=False):
        super().__init__(x, y, w, h)
        self.gravedad = False
        self.color = color
        self.peligroso = peligroso

    def draw(self, surf, cam):
        pygame.draw.rect(surf, self.color, cam.to_screen(self.rect))
        pygame.draw.rect(surf, (40, 48, 44), cam.to_screen(self.rect), 2)


class Interactable(Entity):
    """Zona que responde a la tecla de acción cuando el jugador está dentro."""

    radio = 46

    def __init__(self, x, y):
        super().__init__(x, y)
        self.usado = False
        self.bloquea_juego = False   # True en consolas: pausa input pero no física

    @property
    def rect(self):
        return pygame.Rect(int(self.pos.x) - 18, int(self.pos.y) - 18, 36, 36)

    def disponible(self, player) -> bool:
        d = pygame.math.Vector2(player.rect.center) - self.pos
        return d.length() < self.radio

    def accion(self, player, level) -> None:
        raise NotImplementedError
