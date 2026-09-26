# VECTORIA — Documento de Diseño de Juego (GDD) v0.1
**Género:** Plataformas 2D / Exploración / Aventura con elementos sandbox
**Motor base:** Pygame + NumPy/SciPy (física simulada en tiempo real)
**Premisa central:** *"No puedes controlar aquello de lo que formas parte."*

---

## 1. Pitch narrativo

TECH-SYNC nació para **monitorear** fenómenos naturales. Terminó construyendo
**NÚCLEO**, una red global de nodos que supuestamente los **controla**. La tecnología
fue vendida en secreto a un gobierno para desertificar una región de Sudamérica
y extraer recursos bajo el suelo. El equilibrio planetario colapsó.

El protagonista —empleado de TECH-SYNC, sin memoria— debe reconstruir la verdad
a partir de registros de audio, terminales abandonados y arquitectura destruida.
Al final descubre que **él co-escribió las ecuaciones de control** del clima.
Decisión final: destruir NÚCLEO (devolver al mundo un caos ingobernable) o
mantenerla (seguir gobernando algo que ya no distingue entre operador y sistema).

**Regla de oro narrativa:** nada de *exámenes*. El jugador nunca ve "resuelve
esta integral". Ve un puente de péndulos que oscila, un abismo, y una consola
con la longitud del cable. Si el periodo es incorrecto, se estrella. Punto.

---

## 2. Estructura de progresión (biomas → conceptos)

| # | Bioma | Concepto ancla | Mecánica dieléctica | Castigo por error |
|---|-------|----------------|---------------------|-------------------|
| 0 | Bosque — *El Despertar* | MAS, ondas, péndulos y resortes | Sintonizar longitud L de péndulos industriales y k de resortes para cruzar | Choque mortal contra hormigón; caída al vacío |
| 1 | Montañas — *La Tierra bajo nuestros pies* | Derivada direccional, ∇f, resonancia | Escalar siguiendo gradiente durante derrumbes; curvas de nivel = roca estable | Deslizamiento, avalancha, frecuencia propia = colapso |
| 2 | Desierto — *El Proyecto* | Regla de la cadena, optimización, fluidos (ρ, P, caudal) | Reparar estaciones meteorológicas y tuberías ajustando flujos | Sobrepresión: junta revienta, arena caliente daña |
| 3 | Ciudad — *La Verdad Oculta* | Termodinámica, gases ideales, máquinas térmicas | Hornos y pistones: ajustar P·V = nRT para impulsar plataformas | Explosión de área por exceso de calor |
| 4 | Cielo — *El Desequilibrio Global* | Funciones multivariable, campos a escala | Rebalancear variables globales de NÚCLEO desde la atmósfera | Corrientes de chorro expulsan al jugador del mapa |
| 5 | Espacio — *La Última Respuesta* | Integrales múltiples (cilíndricas/esféricas) | Colocar satélites que definen límites r, θ, z → volumen exacto del escudo | Volumen erróneo: escudo parcial → descompresión |

Cada bioma introduce **una** herramienta de interfaz y **una** variación de
peligro. Nunca dos novedades simultáneas.

---

## 3. Interfaces dielécticas (el "menú" es parte del mundo)

1. **Consolas de calibración:** terminales físicamente montados sobre la máquina
   que controlan. Muestran la ecuación *de esa máquina*, no una hoja de fórmulas.
2. **HUD vectorial:** el personaje lleva un guante con láser que dibuja el
   vector de fuerza/velocidad actual sobre el objeto apuntado (feedback físico
   constante, estilo sandbox).
3. **Registros (LOGs):** fragmentos de lore reproducidos como texto en terminal
   con efecto de escritura. Cada LOG recontextualiza una mecánica aprendida:
   el jugador descubre que el péndulo que usó para saltar era un prototipo del
   sistema climático.

### Tolerancia de diseño
- Los acertijos aceptan un **rango** de soluciones (±5–8% sobre el valor ideal),
  porque el objetivo es diseñar-intuir-medir, no ser calculadora.
- La consola muestra lectura analógica (aguja/dígitos parciales): el jugador
  puede resolver por física *o* por observación del entorno (ambos válidos).

---

## 4. Sistema de muerte y "reinicio dieléctico"

Morir = el protocolo médico de TECH-SYNC te reanima en el último checkpoint.
El texto de respawn varía según bioma ("ANESTESIA LOCAL REAPLICADA — SU
CONTRASEÑA NO SE RECUPERÓ"). No hay vidas: cada fallo cuesta tiempo de escena,
como en los soulslikes, pero sin contadores en pantalla.

---

## 5. Arquitectura de código (src/)

```
src/
  entidades/    Entity, Player, Pendulum, SpringPlatform, Terminal, LogPickup
  fisicas/      mas.py (oscilador armónico disipado), pendulum_solver.py
  niveles/      Level (máquina de estados), bosque_despertar.py (nivel 0 jugable)
```

**Herencia clave:**
`Entity` → `PhysicsBody` (posición, velocidad, masa) → `Pendulum` / `SpringPlatform`.
`Pendulum` integra θ'' = −(g/L)·sinθ − c·θ' con SciPy `solve_ivp` (LSODA);
el render lee θ interpolada. Así la animación **es** la solución numérica:
si el diseñador cambia L, el juego entero obedece la matemática.

`Terminal` hereda de `Interactable`: recibe un `Callable` validador que compara
el estado de la máquina contra su condición de éxito (`is_calibrated()`).

---

## 6. Hoja de ruta
- [x] Núcleo motor + Nivel 0 (Bosque) con MAS real
- [ ] Bioma 1: campo topográfico procedural + curvas de nivel como plataformas
- [ ] Sistema de guardado de logs (lore persistente)
- [ ] Editor sandbox de máquinas (modo diseñador dentro del juego)
