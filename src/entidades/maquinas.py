"""
vectoria.entidades.maquinas
===========================
Máquinas TECH-SYNC que el jugador puede (y debe) recalibrar.

Composición, no copia de física: cada máquina ENCAPSULA un solver de
``src.fisicas.mas`` y proyecta su estado SI a píxeles con ESCALA. Así la
pantalla siempre miente menos que el motor.

    PenduloMaquina   → usa PenduloIndustrial  (θ real, plataforma colgante)
    ResorteMaquina   → usa ResortePlataforma  (plataforma vertical MAS)
    ConsolaCalibracion (Interactable)         → edita L o k en caliente
    Registro         (Interactable)           → lore tipo terminal
"""
from __future__ import annotations

import math
import pygame

from src.fisicas.mas import PenduloIndustrial, ResortePlataforma, G_EARTH
from .base import Entity, Interactable, Solid

ESCALA = 40.0          # píxeles por metro (nivel Bosque)
TOLERANCIA = 0.07      # ±7% sobre el periodo objetivo — rango, no examen


class MaquinaOscilante(Entity):
    """Base común: toda máquina expone periodo actual y calibración."""

    movil = True

    def __init__(self, x_pivote, y_pivote):
        super().__init__(x_pivote, y_pivote)
        self.osc = None                    # solver asignado por subclase
        self.delta_x_mov = 0.0
        self.delta_y_mov = 0.0
        self._anterior = (x_pivote, y_pivote)

    @property
    def periodo(self) -> float:
        return self.osc.periodo

    def es_calibrada(self, T_objetivo: float) -> bool:
        return abs(self.periodo - T_objetivo) / T_objetivo <= TOLERANCIA

    def _registrar_delta(self, nuevo: tuple[float, float], dt: float) -> None:
        paso = max(dt * 60.0, 1e-6)
        self.delta_x_mov = (nuevo[0] - self._anterior[0]) / paso
        self.delta_y_mov = (nuevo[1] - self._anterior[1]) / paso
        self._anterior = nuevo


class PenduloMaquina(MaquinaOscilante):
    """Grúa pendular T-900: plataforma colgada de un cable de longitud L.

    El jugador viaja SOBRE la plataforma; debe llegar al borde opuesto del
    abismo cuando θ≈0 (centro del arco). Si el periodo no coincide con la
    geometría del cañón, la inercia lo estrella contra la pared de hormigón
    (pared = Solid peligroso colocada por el nivel).
    """

    def __init__(self, x_pivote, y_pivote, longitud_m, theta0_deg=28.0):
        super().__init__(x_pivote, y_pivote)
        self.osc = PenduloIndustrial(longitud_m, masa=40.0,
                                     theta0_deg=theta0_deg, c=0.0)
        self.largo_px = longitud_m * ESCALA
        self.bob_w, self.bob_h = 74, 16
        self._rect = pygame.Rect(0, 0, self.bob_w, self.bob_h)
        self.theta = self.osc.x0

    def set_longitud(self, L: float) -> None:
        self.osc.set_longitud(L)
        self.largo_px = self.osc.longitud * ESCALA

    def update(self, dt, level) -> None:
        th = self.osc.paso(dt)            # integra MAS un frame
        self.theta = th
        bx = self.pos.x + self.largo_px * math.sin(th)
        by = self.pos.y + self.largo_px * math.cos(th)
        self._registrar_delta((bx, by), dt)
        self._rect.topleft = (int(bx - self.bob_w / 2), int(by))

    def plataforma_rect(self):
        return self._rect

    def draw(self, surf, cam):
        pv = cam.to_world_to_screen(self.pos)
        r = cam.to_screen(self._rect)
        pygame.draw.line(surf, (150, 150, 140), pv, r.center, 2)      # cable
        pygame.draw.circle(surf, (90, 90, 88), pv, 6)                 # pivote
        pygame.draw.rect(surf, (120, 132, 118), r, border_radius=3)   # plataforma
        pygame.draw.rect(surf, (60, 200, 210), (r.x, r.y, r.w, 3))    # franja HUD
        # vector velocidad tangencial (diegético: la física se ve, no se explica)
        v = self.osc.estado(self.osc.tiempo)[1]                        # dθ/dt
        vx = math.cos(self.theta) * v * self.largo_px / ESCALA
        fin = (r.centerx + int(vx * 4), r.centery - 24)
        pygame.draw.line(surf, (255, 150, 110), (r.centerx, r.centery - 24), fin, 2)
        dx = fin[0] - r.centerx
        pygame.draw.line(surf, (255, 150, 110), fin, (fin[0] - int(0.7*abs(dx)) - 3 if dx>0 else fin[0] + 3, fin[1] + 5), 2)


class ResorteMaquina(MaquinaOscilante):
    """Plataforma elevadora sobre muelle. Aterrizar subiendo = catapultado;
    aterrizar bajando bajo el techo = aplastado (techo peligroso del nivel)."""

    def __init__(self, x_base, y_base, k, amplitud_m=1.4):
        super().__init__(x_base, y_base)
        self.osc = ResortePlataforma(k=k, amplitud=amplitud_m)
        self.ancho, self.alto = 90, 18
        self._rect = pygame.Rect(0, 0, self.ancho, self.alto)
        self.amplitud_px = amplitud_m * ESCALA

    def set_k(self, k: float) -> None:
        self.osc.k = max(50.0, k)
        x, v = self.osc.estado(self.osc.tiempo)
        self.osc.reset(x0=x, v0=v)

    def update(self, dt, level) -> None:
        x = self.osc.paso(dt)              # integra MAS un frame
        cy = self.pos.y - x * ESCALA       # desplazamiento vertical armónico
        self._registrar_delta((self.pos.x, cy), dt)
        self._rect.topleft = (int(self.pos.x - self.ancho / 2), int(cy))

    def plataforma_rect(self):
        return self._rect

    def draw(self, surf, cam):
        base = cam.to_world_to_screen(self.pos)
        r = cam.to_screen(self._rect)
        top = r.midtop
        n = 7
        for i in range(n):                      # muelle en zigzag
            f0, f1 = i / n, (i + 1) / n
            p0 = (base[0] + (1 - 4 * ((i % 2))) * 10 * (1 - f0),
                  base[1] + (top[1] - base[1]) * f0)
            p1 = (base[0] + (1 - 4 * ((i % 2))) * 10 * (1 - f1),
                  base[1] + (top[1] - base[1]) * f1)
            pygame.draw.line(surf, (170, 170, 160), p0, p1, 2)
        pygame.draw.rect(surf, (120, 132, 118), r, border_radius=3)
        pygame.draw.rect(surf, (60, 200, 210), (r.x, r.y, r.w, 3))


class ConsolaCalibracion(Interactable):
    """Terminal dieléctrica: muestra la ecuación de la máquina, nunca la
    respuesta. Flechas <-/> ajustan L (m) o k (N/m). Se abre/cierra con E."""

    PASO_L = 0.4        # metros por pulsación (gruesa)
    PASO_K = 237.0      # N/m ≈ 5 % de k objetivo (T=2 s, m=120 kg)

    def __init__(self, x, y, maquina: MaquinaOscilante, objetivo_T: float,
                 nota: str = ""):
        super().__init__(x, y)
        self.maquina = maquina
        self.objetivo_T = objetivo_T
        if not self.es_pendulo:
            # El paso de k se deriva de la meta del diseñador: T = 2π√(m/k)
            k_obj = maquina.osc.masa * (2.0 * math.pi / objetivo_T) ** 2
            self.PASO_K = max(1.0, round(0.05 * k_obj))
        self.nota = nota
        self.abierta = False
        self.mensaje = ""
        self._t_mensaje = 0.0

    @property
    def es_pendulo(self) -> bool:
        return isinstance(self.maquina, PenduloMaquina)

    def ajustar(self, signo: int, multiplicador: float | None = None) -> None:
        """Ajuste con dos pasos: grueso (flechas ↑↓) y fino (W/S).

        ``multiplicador`` permite forzar el modo sin leer el teclado
        (usado por las pruebas headless; en juego se autodetecta).
        Garantiza que la tolerancia ±7% sea alcanzable desde cualquier
        valor inicial: PASO_K = 5 % de k objetivo ⇒ máximo ~2 pulsaciones
        gruesas dentro de rango.
        """
        if multiplicador is None:
            teclas = pygame.key.get_pressed()
            fino = bool(teclas[pygame.K_UP] or teclas[pygame.K_w])
            grueso = bool(teclas[pygame.K_DOWN] or teclas[pygame.K_s])
            multiplicador = 0.1 if fino else (3.0 if grueso else 1.0)
        if self.es_pendulo:
            val = self.maquina.osc.longitud + signo * self.PASO_L * multiplicador
            self.maquina.set_longitud(val)
        else:
            val = self.maquina.osc.k + signo * self.PASO_K * multiplicador
            self.maquina.set_k(val)

    def accion(self, player, level) -> None:
        self.abierta = not self.abierta
        self.bloquea_juego = self.abierta
        level.consola_activa = self if self.abierta else None
        if not self.abierta and level.estado == "CONSOLA":
            level.estado = "JUGANDO"

    def feedback(self) -> str:
        err = (self.maquina.periodo - self.objetivo_T) / self.objetivo_T
        if abs(err) <= TOLERANCIA:
            return "SINCRONIA OK // NODO ESTABLE"
        if err > 0:
            return "DESINCRONIA: periodo LARGO — ACORTA el cable / SUBE k"
        return "DESINCRONIA: periodo CORTO — ALARGA el cable / BAJA k"

    def draw_overlay(self, surf: pygame.Surface) -> None:
        w, h = surf.get_size()
        panel = pygame.Rect(w // 2 - 300, 60, 600, 250)
        s = pygame.Surface(panel.size, pygame.SRCALPHA)
        s.fill((8, 14, 16, 235))
        surf.blit(s, panel)
        pygame.draw.rect(surf, (60, 200, 210), panel, 2)
        f = pygame.font.SysFont("monospace", 17)
        fb = pygame.font.SysFont("monospace", 15)
        param = f"L = {self.maquina.osc.longitud:4.1f} m" if self.es_pendulo \
            else f"k = {self.maquina.osc.k:6.0f} N/m"
        lineas = [
            ("TECH-SYNC // CONSOLE DE CALIBRACION T-900", (60, 200, 210)),
            ("", None),
            ("> T = 2*pi*sqrt(L/g)          [MAS ideal]", (200, 210, 205)),
            (f"> {param}", (255, 255, 255)),
            (f"> T_medido = {self.maquina.periodo:4.2f} s   "
             f"T_objetivo = {self.objetivo_T:4.2f} s +/-7%", (255, 255, 255)),
            (f"> {self.feedback()}",
             (120, 230, 140) if "OK" in self.feedback() else (255, 150, 110)),
            ("", None),
            (self.nota, (150, 160, 155)),
            ("[<- / ->] ajustar     [E] cerrar terminal", (140, 150, 145)),
        ]
        for i, (txt, col) in enumerate(lineas):
            if txt:
                surf.blit(f.render(txt, True, col), (panel.x + 18, panel.y + 14 + i * 26))


class Registro(Interactable):
    """Fragmento de lore. Se reproduce como terminal con efecto escritura."""

    def __init__(self, x, y, titulo: str, lineas: list[str]):
        super().__init__(x, y)
        self.titulo = titulo
        self.lineas = lineas

    def accion(self, player, level) -> None:
        if not self.usado:
            level.abrir_registro(self)


class VentanaRegistro:
    """Overlay de lectura (efecto máquina de escribir). No es entidad: es UI."""

    def __init__(self, registro: Registro):
        self.registro = registro
        self.texto_completo = "\n".join(registro.lineas)
        self.n_chars = 0.0
        self.cerrada = False

    def update(self, dt) -> None:
        self.n_chars = min(len(self.texto_completo), self.n_chars + dt * 90)

    def draw(self, surf: pygame.Surface) -> None:
        w, h = surf.get_size()
        panel = pygame.Rect(w // 2 - 340, h // 2 - 170, 680, 340)
        s = pygame.Surface(panel.size, pygame.SRCALPHA)
        s.fill((6, 10, 12, 242))
        surf.blit(s, panel)
        pygame.draw.rect(surf, (60, 200, 210), panel, 2)
        f = pygame.font.SysFont("monospace", 16)
        fb = pygame.font.SysFont("monospace", 14)
        surf.blit(f.render(f"■ REGISTRO RECUPERADO — {self.registro.titulo}",
                           True, (120, 230, 140)), (panel.x + 16, panel.y + 12))
        visible = self.texto_completo[:int(self.n_chars)]
        for i, linea in enumerate(visible.split("\n")):
            surf.blit(fb.render(linea, True, (205, 215, 210)),
                      (panel.x + 20, panel.y + 44 + i * 22))
        if int(self.n_chars) < len(self.texto_completo):
            if int(pygame.time.get_ticks() / 300) % 2:
                surf.blit(fb.render("█", True, (60, 200, 210)),
                          (panel.x + 20, panel.y + 44 + 22 * len(visible.split("\n"))))
        else:
            surf.blit(fb.render("[E] archivar en libreta personal",
                                True, (140, 150, 145)),
                      (panel.x + 20, panel.bottom - 30))