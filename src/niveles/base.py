"""
vectoria.niveles.base
=====================
Máquina de estados del nivel: JUGANDO / CONSOLA / REGISTRO / MUERTO / VICTORIA.

La cámara es simple (scroll horizontal suave). El nivel registra 'solidos'
(plataformas + máquinas móviles) y 'interactuables'. Los overlays dieléctricos
(consola, registro) bloquean el movimiento del jugador pero NO el reloj de las
máquinas: la física sigue corriendo mientras lees. Ese es el contrato:
el mundo no espera.
"""
from __future__ import annotations

import pygame
from src.entidades.base import Solid, Interactable
from src.entidades.maquinas import ConsolaCalibracion, Registro, VentanaRegistro


class Camera:
    def __init__(self, ancho_pantalla):
        self.x = 0.0
        self.ancho = ancho_pantalla

    def seguir(self, target_rect, dt):
        deseado = target_rect.centerx - self.ancho / 2
        self.x += (deseado - self.x) * min(1.0, dt * 5.0)
        self.x = max(0.0, self.x)

    def to_screen(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.move(-int(self.x), 0)

    def to_world_to_screen(self, punto) -> tuple:
        return (punto[0] - self.x, punto[1])


class Level:
    ANCHO_MUNDO = 4200
    G_PX = 0.55                    # gravedad en px/frame² (calibrada al salto)

    def __init__(self, surface):
        self.surface = surface
        self.solidos: list[Solid] = []
        self.maquinas: list = []
        self.interactuables: list[Interactable] = []
        self.checkpoints: list[tuple[float, float]] = [(80, 300)]
        self.cp_actual = 0
        self.consola_activa: ConsolaCalibracion | None = None
        self.ventana_registro: VentanaRegistro | None = None
        self.estado = "JUGANDO"
        self.t_muerte = 0.0
        self.mensaje_sistema = ""
        self._t_mensaje = 0.0
        self.player = None
        self.camara = Camera(surface.get_width())
        self.reloj = 0.0

    # ------------------------------------------------------------ hooks
    def construir(self):
        raise NotImplementedError

    def objetivo_cumplido(self) -> bool:
        return False

    # ------------------------------------------------------------ eventos
    def manejar_evento(self, ev) -> bool:
        """Devuelve True si el evento fue consumido por una UI."""
        if self.estado == "REGISTRO":
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_e, pygame.K_RETURN):
                r = self.ventana_registro.registro
                r.usado = True
                self.ventana_registro = None
                self.estado = "JUGANDO"
                return True
        if self.consola_activa is not None:
            if ev.type == pygame.KEYDOWN:
                c = self.consola_activa
                if ev.key == pygame.K_LEFT:
                    c.ajustar(-1); return True
                if ev.key == pygame.K_RIGHT:
                    c.ajustar(+1); return True
                if ev.key in (pygame.K_e, pygame.K_ESCAPE):
                    c.accion(None, self); return True
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_e and self.estado == "JUGANDO":
            for it in self.interactuables:
                if it.disponible(self.player):
                    it.accion(self.player, self)
                    return True
        return False

    def abrir_registro(self, reg: Registro) -> None:
        self.ventana_registro = VentanaRegistro(reg)
        self.estado = "REGISTRO"

    # ------------------------------------------------------------ update
    def avisar(self, msg: str, dur=3.0) -> None:
        self.mensaje_sistema = msg
        self._t_mensaje = dur

    def matar(self, causa: str) -> None:
        if self.estado != "MUERTO":
            self.estado = "MUERTO"
            self.t_muerte = 1.6
            self.causa_muerte = causa

    def update(self, dt: float, teclas) -> None:
        dt = min(max(dt, 0.0), 0.05)      # anti-bucle si el SO congela el frame
        self.reloj += dt
        # las máquinas NUNCA se detienen (contrato diegético)
        for m in self.maquinas:
            m.update(dt, self)
        if self.ventana_registro:
            self.ventana_registro.update(dt)
        if self._t_mensaje > 0:
            self._t_mensaje -= dt

        UI_BLOQUEANTE = ("REGISTRO", "CONSOLA")
        if any(getattr(it, "bloquea_juego", False) for it in self.interactuables
               if getattr(it, "abierta", False)):
            self.estado = "CONSOLA" if self.estado == "JUGANDO" else self.estado
        elif self.estado == "CONSOLA":
            self.estado = "JUGANDO"

        if self.estado in UI_BLOQUEANTE:
            return                      # el mundo sigue; el input, no

        if self.estado == "MUERTO":
            self.t_muerte -= dt
            if self.t_muerte <= 0:
                cx, cy = self.checkpoints[self.cp_actual]
                self.player.pos.update(cx, cy)
                self.player.vel.update(0, 0)
                self.estado = "JUGANDO"
            return

        if self.estado == "JUGANDO":
            self.player.controlar(teclas)
        elif self.estado != "MUERTO":
            pass
        solidos_col = self.solidos + [m for m in self.maquinas]
        self.player.mover_con_colision(dt, self.G_PX, solidos_col)

        # checkpoints invisibles
        for i, (cx, cy) in enumerate(self.checkpoints):
            if i > self.cp_actual and self.player.pos.x > cx:
                self.cp_actual = i

        # muerte por peligro o caída
        pr = self.player.rect
        for s in self.solidos:
            if s.peligroso and pr.colliderect(s.rect):
                self.matar("CONTACTO CON ESTRUCTURA COMPROMETIDA")
                return
        if pr.top > self.surface.get_height() + 120:
            self.matar("CAÍDA AL VACÍO — PROTOCOLO DE REANIMACIÓN")
            return

        if self.objetivo_cumplido():
            self.estado = "VICTORIA"

        self.camara.seguir(pr, dt)

    # ------------------------------------------------------------ draw
    def dibujar_fondo(self):
        raise NotImplementedError

    def draw(self) -> None:
        s = self.surface
        h = s.get_height()
        self.dibujar_fondo()
        for sol in self.solidos:
            sol.draw(s, self.camara)
        for m in self.maquinas:
            m.draw(s, self.camara)
        for it in self.interactuables:
            self._draw_interactable(it)
        self.player.draw(s, self.camara)

        f = pygame.font.SysFont("monospace", 15)
        fb = pygame.font.SysFont("monospace", 18)
        # pista contextual de interacción
        if self.estado == "JUGANDO":
            for it in self.interactuables:
                if it.disponible(self.player) and not getattr(it, "usado", False):
                    txt = "[E] " + ("ABRIR TERMINAL" if isinstance(it, ConsolaCalibracion)
                                    else "INSPECCIONAR REGISTRO")
                    x, y = self.camara.to_world_to_screen((it.pos.x - 60, it.pos.y - 52))
                    s.blit(fb.render(txt, True, (60, 200, 210)), (x, y))
        if self.consola_activa:
            self.consola_activa.draw_overlay(s)
        if self.ventana_registro:
            self.ventana_registro.draw(s)
        if self._t_mensaje > 0:
            msg = fb.render(self.mensaje_sistema, True, (255, 230, 140))
            s.blit(msg, (24, h - 46))
        if self.estado == "MUERTO":
            overlay = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            overlay.fill((120, 10, 10, 90))
            s.blit(overlay, (0, 0))
            t = fb.render(f"■ {getattr(self,'causa_muerte','FALLO')} ■", True, (255, 120, 110))
            t2 = f.render("TECH-SYNC MEDICAL: reanimando sujeto EMPLEADO-07...",
                          True, (220, 220, 220))
            s.blit(t, t.get_rect(center=(s.get_width() // 2, h // 2 - 12)))
            s.blit(t2, t2.get_rect(center=(s.get_width() // 2, h // 2 + 16)))
        if self.estado == "VICTORIA":
            self._draw_victoria(s)

    def _draw_interactable(self, it):
        r = self.camara.to_screen(it.rect)
        col = (60, 200, 210) if isinstance(it, ConsolaCalibracion) else (230, 200, 90)
        if getattr(it, "usado", False):
            col = (90, 95, 92)
        pygame.draw.rect(self.surface, (20, 26, 28), r.inflate(8, 8))
        pygame.draw.rect(self.surface, col, r, 2)
        pulso = abs(((self.reloj * 2) % 1) - 0.5) * 2
        if not getattr(it, "usado", False):
            pygame.draw.circle(self.surface, col,
                               (r.centerx, r.y - 12), int(3 + 2 * pulso))

    def _draw_victoria(self, s):
        pass
