"""
vectoria.fisicas.mas
====================
Motor de Movimiento Armónico Simple para Vectoria.

Todos los objetos oscilantes del juego (péndulos industriales, resortes,
diafragmas de presión, nodos de NÚCLEO) derivan de ``OsciladorArmonico``.
La animación NO es una curva cosmética: es la solución numérica de la EDO

        x''(t) = -(k/m)·x  -  c·x'(t)          (amortiguamiento lineal)

integrada con SciPy (LSODA). Cambiar un parámetro en el juego cambia la
trayectoria del jugador, porque comparten la misma matemática.

Convención de unidades: SI dentro del módulo. El nivel define ``ESCALA``
(píxeles por metro) al convertir a coordenadas de pantalla.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp

G_EARTH = 9.81  # m/s²


@dataclass
class OsciladorArmonico:
    """OSC-0: base de todo MAS amortiguado del juego.

    Parámetros:
        masa   m (kg)
        k      constante recuperadora (N/m para resortes; mg/L para péndulo)
        c      coeficiente de amortiguamiento lineal (1/s)
        x0     elongación inicial (m o rad)
        v0     velocidad inicial
    """

    masa: float = 1.0
    k: float = 10.0
    c: float = 0.02
    x0: float = 1.0
    v0: float = 0.0
    _t: float = field(default=0.0, init=False)
    _sol: "solve_ivp | None" = field(default=None, init=False, repr=False)
    _horizon: float = field(default=600.0, init=False)

    # ---------- propiedades derivadas (lo que el jugador debe intuir) -------
    @property
    def omega(self) -> float:
        """Pulsación natural ω₀ = √(k/m)  [rad/s]."""
        return math.sqrt(self.k / self.masa)

    @property
    def periodo(self) -> float:
        """T = 2π/ω₀. Para el péndulo simple: T = 2π√(L/g)."""
        return 2.0 * math.pi / self.omega

    @property
    def amortiguado(self) -> bool:
        return self.c > 0.0

    # ---------- integración -------------------------------------------------
    def _rhs(self, t, y):
        x, v = y
        return [v, -(self.k / self.masa) * x - self.c * v]

    def reset(self, x0: float | None = None, v0: float = 0.0) -> None:
        if x0 is not None:
            self.x0 = x0
        self.v0 = v0
        self._t = 0.0
        self._sol = None

    def _ensure_solution(self) -> None:
        if self._sol is None:
            # Ventana de integración ≈10 periodos: suficiente para el juego.
            # Tolerancias ajustadas: el MAS lineal con DOP853 no necesita
            # 1e-11; con 1e-8/1e-10 la ventana se resuelve ~4x más rápido
            # sin error perceptible (el jugador trabaja con ±7%).
            self._horizon = max(20.0, 10.0 * self.periodo)
            self._sol = solve_ivp(
                self._rhs,
                (0.0, self._horizon),
                [self.x0, self.v0],
                method="DOP853",
                dense_output=True,
                rtol=1e-8,
                atol=1e-10,
            )

    def estado(self, t: float) -> tuple[float, float]:
        """Devuelve (posición, velocidad) en el tiempo absoluto t.

        Si la ventana de integración se agota, NO se descarta el trabajo:
        las condiciones iniciales del tramo siguiente son el estado físico
        real en el borde de la ventana (continuidad de x y v). Antes se
        reiniciaba en (x0, v0), lo que producía un salto visible y obligaba
        a re-integrar desde cero.
        """
        self._ensure_solution()
        while t >= self._horizon:          # ventana agotada → extender reloj
            xb, vb = (float(a) for a in self._sol.sol(self._horizon))
            t -= self._horizon
            self._t -= self._horizon
            self.x0, self.v0 = xb, vb      # continuar desde el estado real
            self._sol = None
            self._ensure_solution()
        x, v = self._sol.sol(t)
        return float(x), float(v)

    def paso(self, dt: float) -> float:
        """Avanza el reloj del simulador y devuelve la posición actual."""
        self._t += dt
        x, _ = self.estado(self._t)
        return x

    @property
    def tiempo(self) -> float:
        return self._t


class PenduloIndustrial(OsciladorArmonico):
    """Péndulo de cuerda larga (grúa T-900 de TECH-SYNC).

    Modelo linealizado: θ'' = -(g/L)θ - cθ'  →  k_efectivo = m·g/L.
    El jugador edita ``longitud`` desde una consola; el periodo resultante
    decide si la plataforma móvil llega alineada al borde del abismo.
    """

    def __init__(self, longitud: float, masa: float = 40.0,
                 theta0_deg: float = 28.0, c: float = 0.0):
        self.longitud = max(0.5, longitud)
        super().__init__(masa=masa, k=masa * G_EARTH / self.longitud,
                         c=c, x0=math.radians(theta0_deg))

    def set_longitud(self, L: float) -> None:
        """Recalibración en caliente desde la terminal (sin reiniciar fase)."""
        self.longitud = max(0.5, L)
        self.k = self.masa * G_EARTH / self.longitud
        # conservar el estado físico actual como nueva condición inicial
        x, v = self.estado(self._t)
        self.reset(x0=x, v0=v)

    @staticmethod
    def longitud_para_periodo(T: float) -> float:
        """Diseñador-inverso: L = g·(T/2π)². Usado por la consola para
        mostrar la ecuación, no la respuesta."""
        return G_EARTH * (T / (2.0 * math.pi)) ** 2


class ResortePlataforma(OsciladorArmonico):
    """Plataforma sobre muelle vertical. Si el jugador aterriza cuando la
    plataforma sube, el impulso lo lanza; si baja, lo hunde contra el techo
    de hormigón. k se ajusta con contrapesos colocados en la consola."""

    def __init__(self, k: float, masa_plat: float = 120.0,
                 amplitud: float = 1.4, c: float = 0.05):
        super().__init__(masa=masa_plat, k=k, c=c, x0=amplitud)

    @property
    def fuerza_maxima(self) -> float:
        return self.k * abs(self.x0)
