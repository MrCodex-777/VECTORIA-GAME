"""
vectoria.niveles.bosque_despertar
=================================
BIOMA 0 — "EL DESPERTAR" (tutorial). Diseñado según docs/GDD_Vectoria.md §2.

Mapa (4200 px, scroll horizontal):

 [A] Andén de reanimación      x 0..600     → LOG 0-A automático al nacer
 [B] Suelo estable + consola-1 x 600..1350  → LOG 0-B en el trayecto
 --- ABISMO DEL PÉNDULO ---    x 1350..2150
 [C] Plataforma intermedia     x 2150..2600 → resorte-2 protege el techo
 --- FOSA DEL RESORTE ---      x 2600..3350
 [D] Balconcito + consola-3    x 3350..3700 → LOG 0-C
 --- ARCO FINAL (péndulo 2) -- x 3700..4100
 [E] Elevador geológico        x 4100..4200 → LOG 0-D = victoria

Acertijos y su física real:
 B1 péndulo: cruzar exige T≈3.2 s → L = g(T/2π)² ≈ 2.5 m. Error ⇒ la
    inercia lo estrella contra el pilar de hormigón (Solid peligroso).
 B2 resorte: plataforma que sube/baja; si aterriza bajando bajo el dintel
    (techo peligroso) es aplastado. k objetivo: T≈2.0 s ⇒ k = m(2π/T)².
 B3 péndulo largo: T≈4.0 s para alcanzar el elevador. El jugador ya calibró
    dos máquinas: este es su examen sin exámen.
"""
from __future__ import annotations

import math
import pygame

from src.fisicas.mas import G_EARTH
from .base import Level
from src.entidades.base import Solid
from src.entidades.player import Player
from src.entidades.maquinas import (PenduloMaquina, ResorteMaquina,
                                    ConsolaCalibracion, Registro)

# ------------------------------- lore (docs/NARRATIVA.md) ------------------
LOG_0A = ("PROTOCOLO DE REANIMACIÓN v4.2", [
    "> TECH-SYNC // PROTOCOLO DE REANIMACIÓN v4.2",
    "> SUJETO: EMPLEADO 07. ESTADO: DESORIENTADO. AMNESIA: CONFIRMADA.",
    "> NOTA DEL DR. ARRIAGA: \"No le digan lo del incidente. Solo",
    "> devuélvanlo al campo. Si pregunta por qué hay vegetación creciendo",
    "> dentro del laboratorio... díganle que siempre hubo.\"",
])
LOG_0B = ("MANTENIMIENTO — GRÚA PENDULAR T-900", [
    "> REGISTRO DE MANTENIMIENTO — GRÚA PENDULAR T-900",
    "> \"Este prototipo no movía cargas. Movía SENSORES atmosféricos a",
    "> altitud constante. Alguien cambió la longitud del cable en 2031 y",
    "> nunca actualizó el periodo. Ahora oscila 'sola'. No la apaguen:",
    "> el departamento de RR.HH. dice que da 'vida al paisaje'.\"",
])
LOG_0C = ("AUDIO TRANSCRITO — CALIDAD 41%", [
    "> VOZ 1 (identificada como: USTED): \"...el MAS es ideal si no hay",
    "> fricción. En campo SIEMPRE hay fricción. Por eso amortiguamos:",
    "> c pequeño, crítico nunca. Si el sistema entra en resonancia con",
    "> el viento dominante, el nodo...\"",
    "> [RUIDO] \"...no es un sensor, Elena. Es un actuador. Lo construimos",
    "> para EMPUJAR la atmósfera.\"",
    "> VOZ 2: \"Entonces cuando falle, no será un error de medición.\"",
    "> VOZ 1: \"Será un golpe.\"",
])
LOG_0D = ("CIRCULAR 118 — PROYECTO ÁRIDO", [
    "> AVISO CORPORATIVO — CIRCULAR 118",
    "> \"La zona 4 (Bosque Atlántico) ha sido reclasificada como",
    "> 'entorno inestable controlado'. Gracias a nuestros sistemas,",
    "> la inestabilidad ahora es CONTROLADA. Las cuerdas de seguridad",
    "> son para herramientas, no para personal.\"",
    "> [escrito encima, con lápiz, tembloroso:]",
    "> \"Yo firmé esa circular.\"",
])


class BosqueDespertar(Level):
    NOMBRE = "BIOMA 0 — BOSQUE: EL DESPERTAR"

    def construir(self) -> None:
        h = self.surface.get_height()          # ~560
        suelo_y = h - 70

        # ---- [A] andén de reanimación
        self.solidos.append(Solid(-40, suelo_y, 660, 90, (74, 86, 78)))
        self.solidos.append(Solid(-40, 0, 60, suelo_y, (58, 66, 60)))       # muro inicial
        self.player = Player(80, suelo_y - Player.ALTO)
        self.checkpoints = [(80, suelo_y - Player.ALTO)]

        # ---- [B] suelo hasta el abismo
        self.solidos.append(Solid(700, suelo_y, 650, 90, (74, 86, 78)))
        self.checkpoints.append((760, suelo_y - Player.ALTO))

        # ---- B1: abismo del péndulo (x 1350..2150)
        self.pend1 = PenduloMaquina(1750, 40, longitud_m=1.2, theta0_deg=30)
        self.maquinas.append(self.pend1)
        self.solidos.append(Solid(2150, suelo_y, 460, 90, (74, 86, 78)))    # isla central
        # pilar de hormigón: si el periodo está mal, la inercia lo estrella ahí
        self.solidos.append(Solid(2060, 120, 60, suelo_y - 120,
                                  (110, 96, 90), peligroso=True))
        self.consola1 = ConsolaCalibracion(
            1290, suelo_y - 40, self.pend1, objetivo_T=3.2,
            nota="placa grabada: \"T = 2π√(L/g). La grúa llega AL CENTRO "
                 "del arco cada medio periodo. Hazla llegar viva.\"")
        self.interactuables.append(self.consola1)
        self.reg_b = Registro(980, suelo_y - 40, *LOG_0B)
        self.interactuables.append(self.reg_b)

        # ---- B2: fosa del resorte (x 2610..3350) sobre isla central
        self.resorte = ResorteMaquina(2950, suelo_y + 60, k=8000.0)
        self.maquinas.append(self.resorte)
        self.solidos.append(Solid(3350, suelo_y, 380, 90, (74, 86, 78)))
        self.checkpoints.append((3400, suelo_y - Player.ALTO))
        # dintel bajo: techo peligroso sobre la fosa
        self.solidos.append(Solid(2610, 150, 740, 40, (110, 96, 90),
                                  peligroso=True))
        self.consola2 = ConsolaCalibracion(
            2585, suelo_y - 40, self.resorte, objetivo_T=2.0,
            nota="placa grabada: \"ω = √(k/m), m_plataforma = 120 kg. "
                 "Sube cuando saltes. Nunca bajes cuando aterrices.\"")
        self.interactuables.append(self.consola2)
        self.reg_c = Registro(3520, suelo_y - 40, *LOG_0C)
        self.interactuables.append(self.reg_c)

        # ---- B3: arco final hacia el elevador (x 3730..4100)
        self.pend2 = PenduloMaquina(3980, 30, longitud_m=2.0, theta0_deg=24)
        self.maquinas.append(self.pend2)
        self.solidos.append(Solid(4100, suelo_y, 140, 90, (74, 86, 78)))    # meta
        self.meta_x = 4140
        self.consola3 = ConsolaCalibracion(
            3712, suelo_y - 40, self.pend2, objetivo_T=4.0,
            nota="placa grabada: \"último tramo. el elevador no espera."
                 " tú tampoco.\"")
        self.interactuables.append(self.consola3)
        self.reg_d = Registro(4160, suelo_y - 60, *LOG_0D)
        self.interactuables.append(self.reg_d)

        # decorado: pilares-caída en el vacío cuentan como muerte por caída
        self.reg_a = None                     # log de arranque se muestra aparte
        self._arranque_mostrado = False

    # ---------------------------------------------------------------- logic
    def objetivo_cumplido(self) -> bool:
        return self.player.pos.x > self.meta_x + 20 and self.reg_d.usado

    def update(self, dt, teclas):
        if not self._arranque_mostrado:
            self._arranque_mostrado = True
            self.abrir_registro(Registro(0, 0, *LOG_0A))
            super().update(dt, teclas)
            return
        super().update(dt, teclas)
        if self.estado == "JUGANDO":
            if self.pend1.es_calibrada(self.consola1.objetivo_T) \
                    and not getattr(self, "_aviso1", False):
                self._aviso1 = True
                self.avisar("NODO T-900 SINCRONIZADO — LA GRÚA RESPONDE A TI")

    # ------------------------------------------------------------- estética
    def dibujar_fondo(self):
        s = self.surface
        w, h = s.get_size()
        s.fill((16, 26, 24))
        # niebla verde: dos capas de siluetas con parallax (0.15x y 0.35x)
        for vel, col, alto in ((0.15, (24, 42, 34), 300), (0.35, (32, 54, 42), 210)):
            ox = int(-(self.camara.x * vel)) % 230
            for j in range(-1, w // 230 + 2):
                px = j * 230 - ox
                pygame.draw.rect(s, col, (px, h - alto - 40, 90, alto))
        # raíces/vegetación sobre estructuras (ruina orgánica)
        pygame.draw.rect(s, (20, 34, 26), (0, h - 40, w, 40))

    def _draw_victoria(self, s):
        fb = pygame.font.SysFont("monospace", 22)
        t = fb.render("BIOMA 0 COMPLETO — ASCENSOR GEOLOGICO AUTORIZADO",
                      True, (120, 230, 140))
        t2 = pygame.font.SysFont("monospace", 15).render(
            "Siguiente registro topográfico: MONTAÑAS — gradiente de ascenso",
            True, (200, 210, 205))
        s.blit(t, t.get_rect(center=(s.get_width() // 2, s.get_height() // 2 - 10)))
        s.blit(t2, t2.get_rect(center=(s.get_width() // 2, s.get_height() // 2 + 22)))
