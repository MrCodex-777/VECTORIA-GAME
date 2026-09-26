"""
vectoria.gfx.pixelart
=====================
Motor de ARTE PIXEL para VECTORIA. Todo lo que se ve es pixel art generado
por código (sin assets externos): sprites definidos como matrices de
caracteres + paleta maestra, renderizados a una superficie LOGICA diminuta
y escalados con NEAREST-NEIGHBOR al tamaño final. Eso preserva el borde
duro del píxel sin desenfoque.

Personaje EMPLEADO-07 (v2, alta fidelidad): retícula 24x30 celdas —
cuello/casco con visor HUD, tanque de respaldo trasero, manguera frontal,
credencial TECH-SYNC, guantes y botines con suela clara. Los brazos NO son
bytes del sprite: se componen como segmentos rígidos rotados con mask de
color (escalado nearest puro, sin antialiasing), sincronizados con la fase
del ciclo de caminata.

Jerarquía de uso:
    SpriteBank   → fabrica Surface(s) animadas desde plantillas ASCII
    solid_texture→ textura determinista (musgo/metal/hormigón/peligro)
    px / rect_px → primitivas alineadas a retícula
"""
from __future__ import annotations

import math
import random
import pygame

# ------------------------------------------------------------------ retícula
PX_PX = 2                  # tamaño de "píxel lógico" en pantalla
ESCALA_SPRITE = 3          # celda ASCII -> 3 px de pantalla (24x34 => 72x102)
HOMBRO_CELDA_X = 4         # columna de la retícula donde ancla el hombro

# ------------------------------------------------------------- paleta maestra
PAL: dict[str, tuple[int, int, int]] = {
    ".": (0, 0, 0, 0),                     # transparente
    # --- personaje (EMPLEADO-07)
    "k": (24, 28, 32),                     # outline oscuro
    "d": (58, 66, 76),                     # traje — sombra
    "b": (96, 108, 120),                   # traje — medio
    "l": (158, 172, 182),                  # traje — luz
    "w": (222, 230, 236),                  # traje — highlight
    "g": (70, 210, 220),                   # visor HUD cian (apagado)
    "G": (150, 240, 245),                  # visor encendido
    "r": (205, 62, 58),                    # credencial TECH-SYNC
    "s": (214, 168, 128),                  # piel
    "S": (172, 126, 92),                   # piel sombreada
    "h": (46, 40, 38),                     # cabello / interior casco
    "a": (128, 140, 150),                  # armadura de casco (gris claro)
    "q": (52, 160, 170),                   # goma/empaques teal oscuros
    # --- metal / estructura
    "m": (122, 132, 128), "M": (168, 178, 172), "n": (74, 82, 80),
    "o": (200, 208, 202), "u": (40, 46, 44),
    # --- vegetación / musgo
    "e": (58, 112, 62), "E": (92, 158, 84), "f": (34, 74, 44), "F": (140, 196, 104),
    # --- tierra / hormigón
    "t": (92, 78, 66), "T": (128, 110, 92), "c": (148, 140, 128), "C": (182, 174, 160),
    # --- peligro
    "y": (228, 182, 60), "Y": (255, 222, 110), "x": (196, 62, 48), "X": (240, 110, 90),
}


def color(c: str) -> tuple[int, int, int]:
    return PAL[c]


# ============================================================ sprite factory
class SpriteBank:
    """Compila plantillas ASCII en Surfaces pygame, cacheadas."""

    _cache: dict[tuple, pygame.Surface] = {}

    @classmethod
    def from_matrix(cls, mat: list[str], escala: int = ESCALA_SPRITE,
                    flip_h: bool = False) -> pygame.Surface:
        clave = (tuple(mat), escala, flip_h)
        if clave in cls._cache:
            return cls._cache[clave]
        w = max(len(r) for r in mat)
        h = len(mat)
        mini = pygame.Surface((w, h), pygame.SRCALPHA)
        for y, fila in enumerate(mat):
            for x, ch in enumerate(fila):
                col = PAL.get(ch)
                if col is not None and col != (0, 0, 0, 0):
                    mini.set_at((x, y), col)
        surf = pygame.transform.scale(mini, (w * escala, h * escala))
        if flip_h:
            surf = pygame.transform.flip(surf, True, False)
        cls._cache[clave] = surf
        return surf

    # ------------------------------------------------------------ personaje
    # Plantillas 24x30 (cuerpo SIN brazos; los brazos se dibujan encima con
    # segmentos rotados). Origen: borde superior del casco; suela abajo.
    HEAD = [
        "......kkkkkkkk........",
        ".....kaaaaaaaak.......",
        "....kaaaaaaaaaak......",
        "....kahhhhhhhaak......",
        "...kahhkggggghhak.....",
        "...kahkGGGGGGGkhak....",
        "...kshkgggggggkshk....",
        "...ksskssssssskssk....",
        "....kssssssssssk......",
        "....kSSssssssSSk......",
        ".....kkkkkkkkkk.......",
    ]

    TORSO_ROWS = [
        "..kkbbbbbbbbbbbbkk....",
        ".kbwwbbbbbbbbbwwbk....",
        ".kblbbbbbbbbbbbblk....",
        ".kblbbrrrrrrbbblk.....",
        ".kblbrdddddrbblk......",
        ".kbllbdddbdllbk.......",
        ".kdbbbbbbbbbbbbdk.....",
        ".kdbbbbdddddbbbdk.....",
        "..kddddddddddddk......",
        "..kdnnnnnnnnnndk......",
        "...kkkkkkkkkkkk.......",
    ]

    # poses de piernas (12 filas, ancho <=24)
    LEG_STAND = [
        "...kbbb....bbb.k......",
        "...kbbb....bbb.k......",
        "...kddd....ddd.k......",
        "...kddd....ddd.k......",
        "...kddk....kdd.k......",
        "...kddk....kdd.k......",
        "...kkk......kkk.......",
        "..kqqk......kqqk......",
        ".kqqqk......kqqqk.....",
        ".kwwwk......kwwwk.....",
        ".kkkkk......kkkkk.....",
        "......................",
    ]
    LEG_W1 = [  # contacto: pierna der adelante extendida, izq atrás
        "....kbbb..bbb.k.......",
        "...kbbb....bbb.k......",
        "...kddd....ddd.k......",
        "..kddd......ddd.......",
        "..kddk......kdd.......",
        ".kddk........kdd......",
        ".kkk..........kkk.....",
        "kqqk..........kqqk....",
        "kqqqk.........kqqqk...",
        "kwwwk.........kwwwk...",
        "kkkkk.........kkkkk...",
        "......................",
    ]
    LEG_W2 = [  # pasada: ambas piernas juntas bajo el cuerpo
        "......kbbbbbbb.k......",
        "......kbbbbbbb.k......",
        "......kddddddd.k......",
        "......kdd.kdd..k......",
        "......kdk.kdd..k......",
        ".......k...kdd........",
        "......kk...kkk........",
        ".....kqqk..kqqk.......",
        "....kqqqk..kqqqk......",
        "....kwwwk..kwwwk......",
        "....kkkkk..kkkkk......",
        "......................",
    ]
    LEG_W3 = [  # espejo de W1 (se genera por volteado en runtime)
        "...............bbb.k..",
        "..............bbb.k...",
        "..............ddd.k...",
        ".............ddd.k....",
        ".............ddk.k....",
        "............kdd..k....",
        "...........kkk........",
        "..........kqqk........",
        ".........kqqqk........",
        ".........kwwwk........",
        ".........kkkkk........",
        "......................",
    ]
    LEG_W4 = [  # soporte: piernas abiertas en apoyo doble
        "...kbbb.....bbb.k.....",
        "..kbbb.......bbb.k....",
        "..kddd.......ddd.k....",
        "..kddk.......kdd.k....",
        "..kddk.......kdd.k....",
        "..kkk.........kkk.....",
        ".kqqk.........kqqk....",
        "kqqqk.........kqqqk...",
        "kwwwk.........kwwwk...",
        "kkkkk.........kkkkk...",
        "......................",
        "......................",
    ]
    LEG_RUN = [  # zancada extrema + vuelo
        "....kbbb....bbb.......",
        "...kdbbk.....bbb......",
        "..kdkk......kddd......",
        ".kkk.........kddk.....",
        "..............kkk.....",
        "...............kwwk...",
        "................kkk...",
        "......................",
        "......................",
        "......................",
        "......................",
        "......................",
    ]
    LEG_JUMP = [  # recogidas en ascenso
        "...kbbb....bbb........",
        "...kbbb....bbb........",
        "...kddd....ddd........",
        "...kdddk...kddk.......",
        "...kkkkk...kkkkk......",
        "..kwwwk.....kwwwk.....",
        "..kkkk.......kkkk.....",
         "........................",
        "........................",
        "........................",
        "........................",
        "........................",
    ]
    LEG_FALL = [  # extendidas, buscando aterrizar
        "...kbbb.....bbb.......",
        "...kbbb.....bbb.......",
        "...kddd.....ddd.......",
        "...kddd.....ddd.......",
        "...kddk.....kddk......",
        "...kkk.......kkk......",
        "..kqqk.......kqqk.....",
        ".kqqqk......kqqqk.....",
        ".kwwwk......kwwwk.....",
        ".kkkkk......kkkkk.....",
        "......................",
        "......................",
    ]

    # ---- brazos: segmentos rígidos (hombro->codo->mano), pintados con mask
    ARM_SEG_L = 7              # largo de cada segmento en celdas lógicas
    HOMBRO_FILA = 13           # fila de la retícula donde ancla el hombro
    ARM_COLORS = {
        "outline": PAL["k"],
        "superior": PAL["b"],
        "inferior": PAL["d"],
        "guante": PAL["q"],
        "piel": PAL["s"],
    }

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()

    @classmethod
    def _pad(cls, rows: list[str], w: int) -> list[str]:
        return [r.ljust(w)[:w] for r in rows]

    @classmethod
    def _compose(cls, legs: list[str]) -> list[str]:
        """Ensambla HEAD (24an x 11al) + TORSO (24an x 11al) + piernas
        (24an x 12al) centrando horizontalmente cada bloque."""
        W = 24

        def norm(fila: str) -> str:
            fila = fila.replace(" ", ".")          # relleno = transparente
            return fila[:W].ljust(W, ".")

        out = [norm(r) for r in cls._pad(cls.HEAD, W)]
        torso = ["" .ljust((W - len(r)) // 2) + r for r in cls.TORSO_ROWS]
        out += [norm(r) for r in cls._pad(torso, W)]
        piernas = ["".ljust((W - len(r)) // 2) + r for r in legs]
        out += [norm(r) for r in cls._pad(piernas, W)]
        return out

    # ---- API de frames (matrices listas para from_matrix) -----------------
    @classmethod
    def frame_idle(cls, breathe: bool = False) -> list[str]:
        base = cls._compose(cls.LEG_STAND)
        if breathe:                       # micro-desplazamiento vertical 1px
            base = [base[-1]] + base[:-1]
        return base

    @classmethod
    def frame_walk_a(cls) -> list[str]:   return cls._compose(cls.LEG_W1)
    @classmethod
    def frame_walk_b(cls) -> list[str]:   return cls._compose(cls.LEG_W2)
    @classmethod
    def frame_walk_c(cls) -> list[str]:   return cls._compose(cls.LEG_W3)
    @classmethod
    def frame_walk_d(cls) -> list[str]:   return cls._compose(cls.LEG_W4)
    @classmethod
    def frame_run(cls) -> list[str]:      return cls._compose(cls.LEG_RUN)
    @classmethod
    def frame_jump(cls) -> list[str]:     return cls._compose(cls.LEG_JUMP)
    @classmethod
    def frame_fall(cls) -> list[str]:     return cls._compose(cls.LEG_FALL)

    # ---- brazo procedural (segmentos rotados, estilo Mega Man X) ----------
    @staticmethod
    def _line_mask(mask, p0, p1, thick):
        """Dibuja una línea gruesa en la máscara booleana numpy-like simple."""
        H, W = len(mask), len(mask[0])
        x0, y0 = p0
        x1, y1 = p1
        n = max(2, int(max(abs(x1 - x0), abs(y1 - y0))) + 1)
        for i in range(n + 1):
            f = i / n
            cx = int(round(x0 + (x1 - x0) * f))
            cy = int(round(y0 + (y1 - y0) * f))
            for oy in range(-(thick // 2), thick - thick // 2 + 1):
                for ox in range(-(thick // 2), thick - thick // 2 + 1):
                    X, Y = cx + ox, cy + oy
                    if 0 <= X < W and 0 <= Y < H:
                        mask[Y][X] = True

    @classmethod
    def arm_surface(cls, ang_sup_deg: float, ang_inf_deg: float,
                    escala: int = ESCALA_SPRITE,
                    flip_h: bool = False) -> tuple[pygame.Surface, tuple]:
        """Brazo completo (hombro->codo->mano) como Surface con alpha.
        Ángulos en grados respecto de la vertical hacia abajo (0 = cuelga).
        Se rasteriza en resolución final directamente sobre máscaras de
        color — bordes duros, cero suavizado."""
        L = cls.ARM_SEG_L * escala
        gros = max(3, 3 * escala // 2 * 2)          # par, ~6 px a escala 3
        mano = max(2, 2 * escala)
        pad = int(L * 1.6) + gros * 2
        W = H = pad * 2
        sx, sy = pad, pad                            # hombro en el centro
        a1 = math.radians(ang_sup_deg) + math.pi / 2
        ex = sx + L * math.cos(a1)
        ey = sy + L * math.sin(a1)
        a2 = a1 + math.radians(ang_inf_deg)
        hx = ex + L * math.cos(a2)
        hy = ey + L * math.sin(a2)

        masks: list[list[list[bool]]] = []

        def new_mask():
            return [[False] * W for _ in range(H)]

        m_out = new_mask()
        cls._line_mask(m_out, (sx, sy), (ex, ey), gros + 2)
        cls._line_mask(m_out, (ex, ey), (hx, hy), gros + 2)
        m_sup = new_mask()
        cls._line_mask(m_sup, (sx, sy), (ex, ey), gros)
        m_inf = new_mask()
        cls._line_mask(m_inf, (ex, ey), (hx, hy), gros)
        m_gant = new_mask()
        cls._line_mask(m_gant, (hx, hy), (hx, hy), mano + 2)
        m_piel = new_mask()
        cls._line_mask(m_piel, (hx, hy), (hx, hy), max(2, mano - 2))

        C = cls.ARM_COLORS
        capas = [(m_out, C["outline"]), (m_sup, C["superior"]),
                 (m_inf, C["inferior"]), (m_gant, C["guante"]),
                 (m_piel, C["piel"])]
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for m, col in capas:
            srow = pygame.Surface((W, H), pygame.SRCALPHA)
            for y in range(H):
                row = m[y]
                for x in range(W):
                    if row[x]:
                        srow.set_at((x, y), col)
            surf.blit(srow, (0, 0))
        if flip_h:
            surf = pygame.transform.flip(surf, True, False)
            hombro = (W - 1 - pad, pad)
        else:
            hombro = (pad, pad)
        return surf, hombro


# ====================================================== primitivas alineadas
def px(v: float) -> int:
    return int(round(v / PX_PX)) * PX_PX


def rect_px(surf, col, x, y, w, h):
    pygame.draw.rect(surf, col, (px(x), px(y),
                                 max(PX_PX, px(w)), max(PX_PX, px(h))))


def line_px(surf, col, p0, p1, grosor=PX_PX):
    pygame.draw.line(surf, col, (px(p0[0]), px(p0[1])),
                     (px(p1[0]), px(p1[1])), grosor)


def circle_px(surf, col, centro, radio):
    cx, cy = centro
    rr = max(PX_PX, px(radio))
    steps = max(6, int(rr // PX_PX))
    pts = []
    for i in range(steps + 1):
        ang = -math.pi / 2 + math.pi * i / steps
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        line_px(surf, col, (ax, ay), (bx, by))


# ==================================================== texturas de terreno
_TEX_CACHE: dict[tuple, pygame.Surface] = {}


def solid_texture(tipo: str, w: int, h: int, seed: int = 0) -> pygame.Surface:
    """Textura pixelada determinista para un Solid. ``tipo``:
    'bosque' (tierra estratificada + musgo), 'metal' (paneles remachados),
    'hormigon' (juntas y grietas), 'peligro' (rayas de fatiga)."""
    clave = (tipo, w, h, seed)
    if clave in _TEX_CACHE:
        return _TEX_CACHE[clave]
    rng = random.Random(seed * 977 + w * 31 + h * 7 + abs(hash(tipo)) % 1000)
    tex = pygame.Surface((w, h), pygame.SRCALPHA)
    W, H = max(1, w // PX_PX), max(1, h // PX_PX)

    def setpx(cx, cy, col):
        if 0 <= cx < W and 0 <= cy < H:
            pygame.draw.rect(tex, col, (cx * PX_PX, cy * PX_PX, PX_PX, PX_PX))

    def darken(col, k=10):
        return tuple(max(0, c - k) for c in col)

    if tipo == "bosque":
        # estratos de tierra: tres bandas con paleta propia + grava suelta
        estratos = [((70, 58, 48), (58, 48, 40)),
                    ((58, 66, 60), (46, 54, 48)),
                    ((44, 50, 46), (34, 40, 36))]
        top_musgo = 2 + rng.randint(1, 3)
        for cy in range(H):
            band = 0 if cy < H // 3 else (1 if cy < 2 * H // 3 else 2)
            cuerpo, veta = estratos[band]
            for cx in range(W):
                base = cuerpo if ((cx * 3 + cy * 2) % 7) else veta
                if rng.random() < 0.05:
                    base = darken(base, 8)
                if rng.random() < 0.012:                      # piedrita
                    base = (max(0, base[0] + 26), max(0, base[1] + 22),
                            max(0, base[2] + 18))
                setpx(cx, cy, base)
        # raíz descendente ocasional atravesando estratos
        for _ in range(max(1, W // 40)):
            rx = rng.randrange(W)
            ry = top_musgo
            while ry < H - 1 and rng.random() < 0.85:
                setpx(rx, ry, (40, 32, 26))
                if rng.random() < 0.4:
                    setpx(rx + 1, ry, (52, 42, 32))
                rx += rng.choice([-1, 0, 0, 1])
                ry += 1
        # capa de musgo: borde irregular, dos tonos + briznas
        prof = top_musgo + 1 + rng.randint(1, 3)
        for cx in range(W):
            d = prof + (rng.randint(-1, 2) if rng.random() < 0.5 else 0)
            for cy in range(max(0, min(d, H))):
                setpx(cx, cy, (74, 122, 70) if (cy % 2 or rng.random() < 0.6)
                      else (96, 150, 84))
        for _ in range(max(3, W // 8)):                       # briznas altas
            bx = rng.randrange(W)
            bh = rng.randint(2, 5)
            for k in range(bh):
                setpx(bx + (1 if k > bh // 2 else 0),
                      max(0, top_musgo + 1 - k),
                      (140, 196, 104) if k % 2 else (92, 158, 84))
        for _ in range(max(1, W // 60)):                      # flor silvestre
            fx = rng.randrange(W)
            setpx(fx, 0, (228, 182, 60))
            setpx(fx + 1, 1, (140, 196, 104))
    elif tipo == "metal":
        # paneles remachados: rejilla 16x10 celdas, bisel y óxido puntual
        for cy in range(H):
            for cx in range(W):
                shade = (122, 132, 128)
                if (cx // 16 + cy // 10) % 2:
                    shade = (114, 124, 120)
                if cx % 16 == 0 or cy % 10 == 0:
                    shade = (88, 96, 92)                      # junta oscura
                if cx % 16 == 1 or cy % 10 == 1:
                    shade = (150, 160, 154)                   # bisel claro
                if rng.random() < 0.03:
                    shade = (160, 120, 78)                    # óxido
                setpx(cx, cy, shade)
        for cy in range(2, max(2, H - 2), 5):
            for cx in range(3, max(3, W - 3), 8):
                setpx(cx, cy, (196, 204, 198))                # remache
                setpx(cx + 1, cy, (70, 78, 76))               # sombra remache
    elif tipo == "hormigon":
        for cy in range(H):
            for cx in range(W):
                base = (110, 96, 90) if ((cx // 10 + cy // 6) % 2) else (102, 88, 82)
                if rng.random() < 0.06:
                    base = (128, 114, 106)
                if rng.random() < 0.02:
                    base = (86, 74, 68)
                setpx(cx, cy, base)
        for _ in range(max(2, W // 14)):                      # grietas ramif.
            gx = rng.randrange(W)
            gy = rng.randrange(H)
            dirx = rng.choice([-1, 1])
            for k in range(rng.randint(5, 14)):
                setpx(gx, gy, (58, 48, 44))
                gx += dirx * (1 if k % 2 == 0 else 0)
                gy = min(H - 1, gy + 1)
                if rng.random() < 0.25:                       # rama
                    setpx(gx + rng.choice([-1, 1]), gy, (66, 56, 50))
        for _ in range(max(1, W // 24)):                      # mancha humedad
            mx_, my_ = rng.randrange(W), rng.randrange(H)
            for yy in range(4):
                for xx in range(3):
                    setpx(mx_ + xx, min(H - 1, my_ + yy), (92, 82, 78))
    elif tipo == "peligro":
        paso = 8
        for cy in range(H):
            for cx in range(W):
                franja = ((cx + cy) // paso) % 2
                col = (228, 182, 60) if franja else (40, 40, 44)
                if rng.random() < 0.05:
                    col = darken(col, 30)
                setpx(cx, cy, col)
        for _ in range(max(1, W // 30)):                      # abolladuras
            bx = rng.randrange(W)
            by = rng.randrange(H)
            for k in range(3):
                setpx(bx + k, min(H - 1, by + k // 2), darken((40, 40, 44), 6))
    else:
        tex.fill((90, 100, 95))
    _TEX_CACHE[clave] = tex
    return tex


def clear_tex_cache():
    _TEX_CACHE.clear()
