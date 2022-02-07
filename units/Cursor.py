from units.Tiles import COLORKEY, load_img
from units.common import *

CURSOR_NORMAL = 0
CURSOR_DIG = 1
CURSOR_SET = 2


def cursor_add_img(img, img_id=None):
    global __cursor_num
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
        pygame.mouse.set_cursor(pg.cursors.Cursor(cursors[num]))


cur_size = (25, 25)
cursor_0 = pg.cursors.Cursor((0, 0), load_img("data/sprites/cursor/cursor_0.png", cur_size))
cursor_1 = pg.cursors.Cursor((0, 0), load_img("data/sprites/cursor/cursor_1.png", cur_size))
cursors = {
    CURSOR_NORMAL: cursor_0,
    CURSOR_DIG: cursor_1,

}

__cursor_num = None
set_cursor(CURSOR_NORMAL)
