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
    """Plataforma/muro estático colisionable. ``peligroso=True`` mata al tocar.

    Render pixel-art: textura determinista por tipo ('bosque', 'metal',
    'hormigon', 'peligro') generada una sola vez y cacheada, con borde
    oscuro y highlight superior alineados a la retícula de 2 px.
    """

    def __init__(self, x, y, w, h, color=(90, 100, 95), peligroso=False,
                 textura: str | None = None):
        super().__init__(x, y, w, h)
        self.gravedad = False
        self.color = color
        self.peligroso = peligroso
        if textura is None:
            textura = "peligro" if peligroso else "bosque"
        self.textura = textura
        self._semilla_tex = int(self.pos.x * 13 + self.pos.y * 7 + w * 3 + h)
        self._tex: pygame.Surface | None = None

    @property
    def plataforma_rect(self):
        return self.rect

    def _textura_surf(self):
        if self._tex is None:
            from src.gfx.pixelart import solid_texture
            w, h = self.size
            self._tex = solid_texture(self.textura, w, h, seed=self._semilla_tex)
        return self._tex

    def draw(self, surf, cam):
        r = cam.to_screen(self.rect)
        if r.right < 0 or r.left > surf.get_width():
            return                                   # culling por cámara
        tex = self._textura_surf()
        surf.blit(tex, (r.x, r.y))
        from src.gfx.pixelart import line_px, color as pc
        line_px(surf, (18, 22, 20), (r.x, r.bottom - 2), (r.right, r.bottom - 2))
        line_px(surf, (18, 22, 20), (r.x, r.y), (r.x, r.bottom))
        line_px(surf, (18, 22, 20), (r.right - 2, r.y), (r.right - 2, r.bottom))
        top_brillo = pc("E") if self.textura == "bosque" else pc("M")
        line_px(surf, top_brillo, (r.x + 2, r.y + 2), (r.right - 4, r.y + 2))


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
