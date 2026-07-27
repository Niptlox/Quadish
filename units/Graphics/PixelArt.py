"""Пиксель-арт: спрайт задаётся сеткой пикселей, а не примитивами.

Раньше существа рисовались эллипсами и прямоугольниками с дробными
координатами (`int(w * 0.15)` и т.п.). На спрайте 16–35 пикселей такая
арифметика даёт разъезжающиеся лапы, разную толщину конечностей и
болтающиеся в воздухе сочленения — форму нельзя проконтролировать, потому
что она пересчитывается от размера.

Здесь каждый пиксель поставлен руками:

    build_sprite([
        ".BBB.",
        "BBBBB",
        ".K.K.",
    ], base="#708090", size=(10, 6))

Сетка рисуется 1:1, а потом при необходимости масштабируется методом
«ближайшего соседа» — пиксели остаются квадратными, картинка не мылится.

Палитра привязана к базовому цвету существа: у зайцев и оленей цвет
выбирается случайно из списка, поэтому оттенки (тень, подпалина) считаются
от него, а не задаются намертво.
"""
import pygame as pg

# Фиксированные цвета, не зависящие от базового цвета существа.
FIXED_COLORS = {
    '.': None,           # прозрачный
    'K': (28, 25, 23),   # обводка/контур
    'e': (12, 10, 9),    # глаз
    'w': (245, 245, 244),  # белый (белок, клык, брюхо)
    'h': (68, 64, 60),   # копыто/коготь/лапа
    'n': (214, 211, 209),  # рог/кость/клюв светлый
    'p': (244, 164, 164),  # нос/язык/ухо изнутри
    'r': (220, 38, 38),  # красный (гребень, глаз хищника)
    'o': (234, 88, 12),  # оранжевый
    'y': (253, 224, 71),  # жёлтый (глаз, клюв)
    'g': (34, 197, 94),  # зелёный
    'b': (56, 189, 248),  # голубой (стекло, лёд)
    'v': (129, 140, 248),  # сине-фиолетовый
    's': (120, 113, 108),  # камень
}


def shade(color, factor):
    """Осветлить (factor > 1) или затемнить (factor < 1) цвет."""
    c = pg.Color(color) if not isinstance(color, pg.Color) else color
    return (max(0, min(255, int(c.r * factor))),
            max(0, min(255, int(c.g * factor))),
            max(0, min(255, int(c.b * factor))))


def palette(base):
    """Палитра сетки: B — базовый цвет существа, D — тень, L — блик."""
    colors = dict(FIXED_COLORS)
    colors['B'] = pg.Color(base)
    colors['D'] = shade(base, 0.62)   # тень/нижняя сторона
    colors['L'] = shade(base, 1.28)   # блик/верхняя сторона
    colors['M'] = shade(base, 0.82)   # средний тон
    return colors


class PixelArtError(Exception):
    """Сетка спрайта описана неверно."""


def build_sprite(rows, base="#FFFFFF", size=None, extra=None, flip=False):
    """Собрать спрайт из сетки символов.

    rows  — строки одинаковой длины (см. палитру выше);
    base  — базовый цвет существа, от него считаются D/L/M;
    size  — итоговый размер; None = 1:1 с сеткой;
    extra — дополнительные цвета символов для этого спрайта;
    flip  — отразить по горизонтали (существо смотрит влево).
    """
    if not rows:
        raise PixelArtError("сетка спрайта пустая")
    width = len(rows[0])
    if width == 0:
        raise PixelArtError("нулевая ширина сетки спрайта")
    for y, row in enumerate(rows):
        if len(row) != width:
            raise PixelArtError(
                f"строка {y + 1} длиной {len(row)}, а первая — {width}: "
                "все строки сетки должны быть одной длины")

    colors = palette(base)
    if extra:
        colors.update(extra)

    surf = pg.Surface((width, len(rows)), pg.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch not in colors:
                raise PixelArtError(f"неизвестный символ сетки {ch!r}")
            color = colors[ch]
            if color is not None:
                surf.set_at((x, y), color)

    if flip:
        surf = pg.transform.flip(surf, True, False)
    if size is not None and tuple(size) != (width, len(rows)):
        # scale, а не smoothscale: пиксели должны остаться квадратными
        surf = pg.transform.scale(surf, (max(1, int(size[0])), max(1, int(size[1]))))
    return surf
