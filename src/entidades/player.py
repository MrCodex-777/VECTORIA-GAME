"""
vectoria.entidades.player
=========================
EMPLEADO 07 — plataformas con inercia "humana" (sin frenado instantáneo:
el personaje pesa, y las consolas de la lore insisten en eso).

Colisiones AABB resueltas por ejes contra todos los Solid del nivel,
incluidas las plataformas móviles de las máquinas (se hereda su velocidad).
"""
from __future__ import annotations

import math
import random
import pygame
from .base import PhysicsBody


class Player(PhysicsBody):
    ANCHO, ALTO = 26, 46           # hitbox alineada a la retícula de 2 px
    VEL_X = 3.6          # impulso horizontal por frame (inercial)
    SALTO = -10.8
    MAX_CAIDA = 17.0

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

    # -------------------------------------------------------------- animación
    def _estado_anim(self) -> str:
        if not self.pies:
            return "jump" if self.vel.y < -0.5 else "fall"
        if abs(self.vel.x) > 4.2:
            return "run"
        if abs(self.vel.x) > 0.6:
            return "walk"
        return "idle"

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
                    if self.vel.y > 6:                   # impacto duro: squash
                        self._aterraje_t = 0.12
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
    _FRAME_KEY = {"idle": "frame_idle", "run": "frame_run",
                  "jump": "frame_jump", "fall": "frame_fall"}
    WALK_KEYS = ("frame_walk_a", "frame_walk_b", "frame_walk_c", "frame_walk_d")

    def __init__(self, x, y):
        super().__init__(x, y, self.ANCHO, self.ALTO)
        self.pies = False
        self.mirando = 1
        self._plataforma_ayer = None
        # --- animación pixel art
        self.t_anim = 0.0
        self._caminante = 0.0          # acumulador de distancia para fases
        self._frames: dict[str, list[pygame.Surface]] = {}
        self._arms: dict[tuple, pygame.Surface] = {}
        self._polvo_t = 0.0
        self._aterraje_t = 0.0         # squash breve al aterrizar

    def _get_frames(self, estado: str) -> list[pygame.Surface]:
        """Frames del cuerpo (sin brazos). walk = ciclo de 4 poses."""
        if estado not in self._frames:
            from src.gfx.pixelart import SpriteBank as SB, ESCALA_SPRITE as ES
            if estado == "walk":
                mats = [getattr(SB, k)() for k in self.WALK_KEYS]
            elif estado == "idle":
                mats = [SB.frame_idle(False), SB.frame_idle(True)]
            else:
                mats = [getattr(SB, self._FRAME_KEY[estado])()]
            base = [SB.from_matrix(m, ES) for m in mats]
            self._frames[estado] = base + [pygame.transform.flip(s, True, False)
                                           for s in base]
        return self._frames[estado]

    def _get_arm(self, ang_sup: int, ang_inf: int,
                 flip: bool) -> pygame.Surface:
        """Brazo rotado cacheado por (ángulos, flip). Ángulos enteros para
        que la caché permanezca pequeña (retícula de 2°)."""
        clave = (ang_sup, ang_inf, flip)
        if clave not in self._arms:
            from src.gfx.pixelart import SpriteBank as SB, ESCALA_SPRITE as ES
            self._arms[clave] = SB.arm_surface(ang_sup, ang_inf, escala=ES,
                                               flip_h=flip)
        return self._arms[clave]

    def _pose_brazos(self, estado: str, fase: int) -> tuple[int, int, int, int]:
        """Devuelve (sup_tras, inf_tras, sup_del, inf_del) en grados,
        mirando siempre hacia la derecha; se voltea según `mirando`.
        Sincronizados con la fase del ciclo de piernas."""
        if estado == "idle":
            b = 2 if int(self.t_anim * 1.6) % 2 == 0 else -2   # respiración
            return (6, 8 + b, -6, 10 - b)
        if estado == "walk":
            ciclo = [(38, -28, -38, -22),                     # contacto der adelante
                     (6, -6, -4, -8),                          # apoyo doble
                     (-38, -20, 38, -28),                      # contacto izq adelante
                     (-6, -8, 6, -6)][fase % 4]                # apoyo doble
            return ciclo
        if estado == "run":
            ciclo = [(62, -70, -55, -35),
                     (20, -30, -20, -45),
                     (-58, -35, 60, -75),
                     (-18, -45, 18, -30)][fase % 4]
            return ciclo
        if estado == "jump":
            return (-55, -70, 48, -95)      # atrás colgando, delante arriba
        # fall: brazos arriba pidiendo equilibrio
        return (-95, -40, 95, -45)

    def update_anim(self, dt: float) -> None:
        self.t_anim += dt
        if self._aterraje_t > 0:
            self._aterraje_t -= dt

    def draw(self, surf, cam):
        from src.gfx.pixelart import ESCALA_SPRITE as ES, HOMBRO_CELDA_X
        r = cam.to_screen(self.rect)
        if r.right < -60 or r.left > surf.get_width() + 60:
            return
        estado = self._estado_anim()
        frames = self._get_frames(estado)   # [base..., volteados...]

        # fase del ciclo: walk/run = 4 poses; idle respira con 2
        if estado in ("walk", "run"):
            paso = 0.05 if estado == "walk" else 0.09
            self._caminante += abs(self.vel.x) * paso
            fase = int(self._caminante) % 4
        elif estado == "idle":
            fase = int(self.t_anim * 1.6) % 2
        else:
            fase = 0
        n_base = len(frames) // 2
        idx = min(fase, n_base - 1)
        sprite = frames[idx]
        volteado = self.mirando < 0
        if volteado:
            sprite = frames[n_base + idx]

        sw, sh = sprite.get_size()
        blit_x = r.centerx - sw // 2
        blit_y = r.bottom - sh
        # squash & stretch duro (pixel art: scale nearest, sin suavizado)
        vy = self.vel.y
        if estado == "jump" and vy < -6:
            sprite = pygame.transform.scale(sprite, (sw - 6, sh + 6))
            blit_y -= 6
            blit_x += 3
        elif estado == "fall" and vy > 8:
            sprite = pygame.transform.scale(sprite, (sw - 4, sh + 4))
            blit_y -= 4
            blit_x += 2
        elif self._aterraje_t > 0:
            sprite = pygame.transform.scale(sprite, (sw + 6, sh - 6))
            blit_y += 6

        # sombra dura alineada a retícula
        sy = r.bottom
        ancho_sombra = int(sw * 0.7) // 2 * 2
        pygame.draw.ellipse(surf, (12, 18, 14),
                            (r.centerx - ancho_sombra // 2, sy - 4,
                             ancho_sombra, 6))

        # ---- brazos: trasero detrás del torso, delantero encima
        a_tras = self._pose_brazos(estado, fase)[:2]
        a_del = self._pose_brazos(estado, fase)[2:]
        hombro_dx = HOMBRO_CELDA_X * ES           # columna del hombro (celda 4)
        hombro_dy = 13 * ES                        # fila del hombro (celda 13)

        def blit_arm(ang_sup, ang_inf, enfrente: bool):
            arm, off = self._get_arm(round(ang_sup / 2) * 2,
                                     round(ang_inf / 2) * 2, volteado)
            hx = blit_x + (hombro_dx if not volteado else sw - hombro_dx)
            hy = blit_y + hombro_dy
            surf.blit(arm, (hx - off[0], hy - off[1]))

        blit_arm(*a_tras, enfrente=False)
        surf.blit(sprite, (blit_x, blit_y))
        blit_arm(*a_del, enfrente=True)

        # polvo al correr/aterrizar (partículas cuadradas de 2 px)
        self._polvo_t -= 1 / 60
        if self._polvo_t <= 0 and estado in ("run", "walk") and self.pies \
                and abs(self.vel.x) > 3:
            self._polvo_t = 0.12
        if self._polvo_t > 0:
            rnd = random.Random(int(self.pos.x) // 7 + int(self.t_anim * 20))
            for _ in range(3):
                ox = rnd.randint(-14, 14)
                oy = -rnd.randint(0, 5)
                px_ = (r.centerx + ox) // 2 * 2
                py_ = (r.bottom + oy) // 2 * 2
                pygame.draw.rect(surf, (150, 160, 140), (px_, py_, 2, 2))

        # parpadeo del visor HUD (vida en el sprite)
        if int(self.t_anim * 3) % 7 == 0:
            vx = r.centerx + (6 if self.mirando > 0 else -10)
            pygame.draw.rect(surf, (170, 250, 250), (vx, blit_y + 15, 6, 3))
