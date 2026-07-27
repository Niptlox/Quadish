"""Курсоры игры.

Вид курсора настраивается («Курсор» в настройках). Стрелки-картинки из
data/sprites/cursor остались как вариант «Стрелка», остальные рисуются
процедурно: прицельным курсорам важна точность, поэтому центр у них
ПУСТОЙ — сквозь него виден тайл, по которому целишься.

Горячая точка (hotspot) у прицельных курсоров стоит ровно в центре, а не в
углу картинки: иначе курсор целился бы не туда, где нарисовано перекрестие.
"""
from units.Tiles import COLORKEY, load_img
from units.common import *

CURSOR_NORMAL = 0
CURSOR_DIG = 1
CURSOR_SET = 2

# Виды курсора для настройки. Порядок = порядок в выпадающем списке.
CURSOR_KINDS = ("arrow", "cross", "cross_dot", "corners", "circle", "system")
CURSOR_KIND_LABELS = ["Стрелка", "Крестик", "Крестик с точкой",
                      "Уголки", "Кружок", "Системный"]

CUR_SIZE = 24          # сторона процедурного курсора (чётная — центр ровный)
_LIGHT = (245, 245, 244)
_DARK = (24, 24, 27)


def _blank():
    surf = pg.Surface((CUR_SIZE, CUR_SIZE), pg.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    return surf


def _outlined_line(surf, x1, y1, x2, y2):
    """Линия с тёмной обводкой: светлый курсор должен быть виден и на
    светлом фоне (небо, песок)."""
    if x1 == x2:
        pg.draw.line(surf, _DARK, (x1 - 1, y1), (x1 - 1, y2))
        pg.draw.line(surf, _DARK, (x1 + 1, y1), (x1 + 1, y2))
    else:
        pg.draw.line(surf, _DARK, (x1, y1 - 1), (x2, y1 - 1))
        pg.draw.line(surf, _DARK, (x1, y1 + 1), (x2, y1 + 1))
    pg.draw.line(surf, _LIGHT, (x1, y1), (x2, y2))


def create_cross(gap=3, arm=8):
    """Перекрестие с пустым центром: точка прицела не закрыта пикселями."""
    surf = _blank()
    c = CUR_SIZE // 2
    _outlined_line(surf, c, c - gap - arm, c, c - gap)   # вверх
    _outlined_line(surf, c, c + gap, c, c + gap + arm)   # вниз
    _outlined_line(surf, c - gap - arm, c, c - gap, c)   # влево
    _outlined_line(surf, c + gap, c, c + gap + arm, c)   # вправо
    return surf


def create_cross_dot(gap=4, arm=7):
    """Перекрестие с одним пикселем ровно в центре — когда нужна именно
    точка прицела, а не пустой промежуток."""
    surf = create_cross(gap=gap, arm=arm)
    c = CUR_SIZE // 2
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        surf.set_at((c + dx, c + dy), _DARK)
    surf.set_at((c, c), _LIGHT)
    return surf


def create_corners(size=6, thick=2):
    """Четыре уголка вокруг цели: центр открыт полностью, блок под курсором
    видно целиком."""
    surf = _blank()
    c = CUR_SIZE // 2
    off = size + 1
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x = c + sx * off - (thick if sx > 0 else 0)
        y = c + sy * off - (thick if sy > 0 else 0)
        hx = x if sx > 0 else x
        pg.draw.rect(surf, _DARK, (min(hx, hx + sx * size) - 1, y - 1, size + 2, thick + 2))
        pg.draw.rect(surf, _DARK, (x - 1, min(y, y + sy * size) - 1, thick + 2, size + 2))
        pg.draw.rect(surf, _LIGHT, (min(hx, hx + sx * size), y, size, thick))
        pg.draw.rect(surf, _LIGHT, (x, min(y, y + sy * size), thick, size))
    return surf


def create_circle(r=7):
    """Кружок с пустой серединой."""
    surf = _blank()
    c = CUR_SIZE // 2
    pg.draw.circle(surf, _DARK, (c, c), r + 1, width=1)
    pg.draw.circle(surf, _LIGHT, (c, c), r, width=2)
    pg.draw.circle(surf, _DARK, (c, c), max(1, r - 2), width=1)
    return surf


def _procedural_cursor(surf):
    return pg.cursors.Cursor((CUR_SIZE // 2, CUR_SIZE // 2), surf)


cur_size = (25, 25)
cursor_0 = pg.cursors.Cursor((0, 0), load_img("data/sprites/cursor/cursor_0.png", cur_size))
cursor_1 = pg.cursors.Cursor((0, 0), load_img("data/sprites/cursor/cursor_1.png", cur_size))

# Наборы «обычный / копать» на каждый вид. У прицельных видов оба состояния
# одинаковы: прицел не должен прыгать при наведении на блок.
_KIND_CURSORS = {
    "arrow": {CURSOR_NORMAL: cursor_0, CURSOR_DIG: cursor_1},
    "system": {CURSOR_NORMAL: pg.cursors.Cursor(pg.SYSTEM_CURSOR_ARROW),
               CURSOR_DIG: pg.cursors.Cursor(pg.SYSTEM_CURSOR_CROSSHAIR)},
}
for _kind, _factory in (("cross", create_cross), ("cross_dot", create_cross_dot),
                        ("corners", create_corners), ("circle", create_circle)):
    _cur = _procedural_cursor(_factory())
    _KIND_CURSORS[_kind] = {CURSOR_NORMAL: _cur, CURSOR_DIG: _cur}


def current_kind():
    kind = config.GameSettings.cursor
    return kind if kind in _KIND_CURSORS else "arrow"


cursors = _KIND_CURSORS[current_kind()]
__cursor_num = None


def apply_cursor_kind():
    """Применить вид курсора из настроек — сразу, без перезапуска игры."""
    global cursors, __cursor_num
    cursors = _KIND_CURSORS[current_kind()]
    __cursor_num = None   # сбросить кэш, иначе set_cursor решит, что менять нечего
    set_cursor(CURSOR_NORMAL)


def cursor_add_img(img, img_id=None):
    """Курсор с картинкой предмета в руке.

    Только для вида «Стрелка»: у прицельных курсоров пририсованная картинка
    закрывала бы как раз то, во что целишься."""
    global __cursor_num
    if current_kind() != "arrow":
        return
    if img_id != __cursor_num:
        __cursor_num = img_id
        surf = pg.Surface((50, 50))
        surf.fill(COLORKEY)
        surf.set_colorkey(COLORKEY)
        cur = cursors[CURSOR_NORMAL].data[1].copy()
        surf.blit(cur, (0, 0))
        surf.blit(img, (12, 18))
        pygame.mouse.set_cursor(pg.cursors.Cursor((0, 0), surf))


def set_cursor(num):
    global __cursor_num
    if num != __cursor_num:
        __cursor_num = num
        # раньше здесь стоял цикл на 10 попыток без break: курсор ставился
        # десять раз подряд независимо от успеха
        cursor = cursors.get(num) or cursors[CURSOR_NORMAL]
        try:
            pygame.mouse.set_cursor(cursor)
        except Exception as exc:
            print("Cursor error", exc)


set_cursor(CURSOR_NORMAL)
