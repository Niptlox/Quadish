from math import ceil
from typing import Union

from pygame import Surface

from units.Items import ItemsTile, Items
from units.Texture import WHITE
from units.Tiles import tile_imgs, sky, tile_words, live_imgs, bg_live_img, goldlive_imgs
from units.Tools import TOOLS
from units.UI.Button import createImagesButton, createVSteckButtons, Button
from units.UI.ClassUI import SurfaceUI, UI, ScrollSurface
from units.common import *

# INIT TEXT ==================================================
from units.creating_items import RECIPES

pygame.font.init()
# textfont = pygame.font.SysFont('Jokerman', 19)
textfont = pygame.font.SysFont("Fenix", 19, )  # yes rus
textfont_sys_msg = pygame.font.SysFont("Fenix", 30, )  # yes rus
# textfont = pygame.font.Font('data/fonts/Teletactile.ttf', 10, bold=True)
textfont_info = pygame.font.Font('data/fonts/Teletactile.ttf', 10, )  # no rus
textfont_btn = pygame.font.SysFont("Fenix", 35, )

# texframe = font.render(text, False, text_color)
text_color = "#1C1917"
text_color_dark = "#1C1917"
text_color_light = "#F5F5F4"

sys_message_bg = (68, 64, 60, 150)

color_none = (0, 0, 0, 0)

bg_color = (82, 82, 91, 150)
bg_color_dark = (52, 52, 51, 150)

# =============================================================

# OBJECT IN MOUSE =============================================
__object_in_mouse = None
__place_of_object_in_mouse = (None, -1)


def set_obj_mouse(obj, place=None):
    global __object_in_mouse, __place_of_object_in_mouse
    __object_in_mouse = obj
    __place_of_object_in_mouse = place


def get_obj_mouse() -> Union[Items, None]:
    return __object_in_mouse


def get_place_obj_mouse() -> tuple:
    return __place_of_object_in_mouse


# =============================================================

class GameUI(UI):
    def __init__(self, app) -> None:
        super().__init__(app)

    def init_ui(self):
        super().init_ui()
        # self.sky_surface = pg.Surface(self.display.get_size()).convert_alpha()
        # self.sky_surface.fill(sky)

        self.info_surface = SurfaceUI((0, 0, 250, 100)).convert_alpha()

        self.sys_message_rect = pg.Rect((WSIZE[0] - 330, WSIZE[1] - 45), (300, 32))
        self.sys_message_text = ""
        self.sys_message_left_tact = 0
        self.sys_message_count_tact = 0
        self.sys_message_surface = pg.Surface(self.sys_message_rect.size).convert_alpha()

        # self.playerui = SurfaceAlphaUI((0, 0, 280, 120))
        self.playerui = SurfaceUI((0, 0, 450, 420)).convert_alpha()
        self.playerui.rect.bottom = self.rect.bottom
        self.new_sys_message("Привет игрок")

    def draw_sky(self):
        # self.display.blit(self.sky_surface, (0, 0))
        self.display.fill(sky)

    def draw(self):
        # DRAW DISPLAY GAME TO WINDOW ========================================
        if show_info_menu:
            self.display.blit(self.info_surface, (WINDOW_SIZE[0] - 250, 0))
        if self.sys_message_left_tact > 0:
            self.sys_message_left_tact -= 1
            if self.sys_message_left_tact < 32:
                self.sys_message_surface.set_alpha(self.sys_message_left_tact * 8)
            elif (self.sys_message_count_tact - self.sys_message_left_tact) < 8:
                self.sys_message_surface.set_alpha((self.sys_message_count_tact - self.sys_message_left_tact) * 32)

            self.display.blit(self.sys_message_surface, self.sys_message_rect)

        self.redraw_playerui()
        self.playerui.draw(self.display)
        # pygame.transform.scale(display,(WINDOW_SIZE[0]//1.8, WINDOW_SIZE[1]//1.8)), (100, 100)
        self.screen.blit(self.display, (0, 0))
        pygame.display.flip()

    def new_sys_message(self, text, count_tact=FPS * 3, draw_now=False):
        self.sys_message_text = text
        self.sys_message_left_tact = count_tact
        self.sys_message_count_tact = count_tact
        self.sys_message_surface.set_alpha(255)
        self.sys_message_surface.fill(sys_message_bg)
        text_msg = textfont_sys_msg.render(text, True, "#FDE047")
        self.sys_message_surface.blit(text_msg, (5, 5))
        if draw_now:
            self.sys_message_left_tact -= 8
            self.draw()

    def redraw_info(self):
        true_fps = self.app.clock.get_fps()
        self.info_surface.fill(bg_color)
        text_fps = textfont_info.render(
            f" fps: {int(true_fps)}", True, "white")
        text_pos_real = textfont_info.render(
            f"rpos: {self.app.player.rect.x, self.app.player.rect.y}", True, "white")
        text_pos = textfont_info.render(
            f" pos: {self.app.player.rect.x // TSIZE, self.app.player.rect.y // TSIZE}", True, "white")
        text_ents = textfont_info.render(
            f"Ents: {len(self.app.screen_map.dynamic_tiles)}", True, "white")
        chunk_ents = self.app.game_map.chunk(self.app.player.update_chunk_pos())[3][1]
        text_c_ents = textfont_info.render(
            f"CEnts: {chunk_ents}", True, "white")
        self.info_surface.blit(text_fps, (8, 5))
        self.info_surface.blit(text_pos_real, (8, 25))
        self.info_surface.blit(text_pos, (8, 45))
        self.info_surface.blit(text_ents, (8, 65))
        self.info_surface.blit(text_c_ents, (8, 85))

    def redraw_playerui(self):
        lives_in_heart = 10
        self.playerui.fill(color_none)
        imgs = live_imgs
        cnt_in_row = 15
        step = imgs[0].get_width() + 5
        x, y = 10, self.playerui.rect.h - step - 5
        startx, starty = x, y
        iy = 0

        for i in range(self.app.player.max_lives // lives_in_heart):
            if i == cnt_in_row * 2:
                x, y = startx, starty
                iy = 0
                imgs = goldlive_imgs
            if i < self.app.player.lives // lives_in_heart:
                self.playerui.blit(imgs[0], (x, y))
            else:
                if (i - 1) < self.app.player.lives // lives_in_heart and self.app.player.lives % lives_in_heart > 0:
                    self.playerui.blit(imgs[4 - self.app.player.lives % lives_in_heart // 2], (x, y))
                else:
                    if i < cnt_in_row * 2:
                        self.playerui.blit(bg_live_img, (x, y))

            x += step
            if (i + 1) % cnt_in_row == 0:
                y -= 15
                iy += 2
                x = startx + iy


class SwitchMapUI(UI):
    bg = (82, 82, 91, 150)

    def __init__(self, app, title) -> None:
        self.title = title
        super().__init__(app)

    def init_ui(self):
        w, h = 300, 500
        self.rect = pg.Rect(0, 0, w, h)
        self.rect.center = WSIZE[0] // 2, WSIZE[1] // 2
        self.surface = pg.Surface(self.rect.size).convert_alpha()

        self.title_surf = pg.Surface((w, 40)).convert_alpha()
        self.title_surf.fill((82, 82, 91))
        self.title_surf.blit(textfont_btn.render(self.title, True, WHITE), (10, 10))

        btn_rect = pg.Rect(0, 20 + 40, 200, 35)
        self.btns_scroll = [(w - btn_rect.w) // 2 - 15, btn_rect.y]
        self.btns_scroll_step = 20 + btn_rect.height

        n = self.app.game.game_map.save_slots
        imgs = [createImagesButton(btn_rect.size, f"Карта #{i}", font=textfont_btn)
                for i in range(n)]
        self.img_btns = imgs
        funcs = [lambda b, i=i: self.open_map(b, i) for i in range(n)]
        btns = createVSteckButtons(btn_rect.size, btn_rect.centerx + 15, 10, 15, imgs, funcs,
                                   screen_position=(self.rect.x + self.btns_scroll[0],
                                                    self.rect.y + self.btns_scroll[1]))  # кнопки открывающие карты
        self.btns_rect = pg.Rect(btns[0].rect.x, btns[0].rect.y, btns[-1].rect.right + 15, btns[-1].rect.bottom + 15)
        self.btns_surf = pg.Surface(self.btns_rect.size).convert_alpha()
        self.btns_surf.fill(self.bg)

        self.btns = btns

    def pg_event(self, event: pg.event.Event) -> Union[bool, None]:
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 5:
                self.btns_scroll[1] -= self.btns_scroll_step
                for btn in self.btns:
                    btn.screenRect.y -= self.btns_scroll_step
            elif event.button == 4:
                if self.btns_scroll[1] < 55:
                    self.btns_scroll[1] += self.btns_scroll_step
                    for btn in self.btns:
                        btn.screenRect.y += self.btns_scroll_step
            else:
                if not self.rect.collidepoint(event.pos):
                    return
        for btn in self.btns:
            btn.pg_event(event)

    def draw(self):
        self.screen.blit(self.display, (0, 0))

        self.surface.fill(self.bg)

        for btn in self.btns:
            btn.draw(self.btns_surf)
        self.surface.blit(self.btns_surf, self.btns_scroll)
        self.surface.blit(self.title_surf, (0, 0))

        self.screen.blit(self.surface, self.rect)

        pygame.display.flip()

    def set_disabled_btns(self, ar):
        for i in range(len(ar)):
            self.btns[i].set_disabled(ar[i])

    def set_check_btns(self, ar):
        check = Surface((10, 10))
        check.fill("#EF4444")
        for i in range(len(ar)):
            if ar[i]:
                img = self.img_btns[i][0].copy()
                img.blit(check, (0, 0))
                self.btns[i].imgUpB = img
            else:
                self.btns[i].imgUpB = self.img_btns[i][0]

    def open_map(self, but, num):
        res = self.app.open_map(num)


class EndUI(UI):
    def init_ui(self):
        self.rect_surface = pg.Rect((0, 0, 220, 100))
        w, h = self.screen.get_size()
        self.rect_surface.center = w // 2, h // 2
        self.surface = pg.Surface(self.rect_surface.size).convert_alpha()
        self.surface.fill((82, 82, 91, 150))
        text = textfont_btn.render(
            f"Вы погибли...", True, "red")
        w, h = text.get_size()
        self.surface.blit(text, (self.rect_surface.w // 2 - w // 2, self.rect_surface.h // 2 - h // 2))
        rect_btn = pg.Rect((self.rect_surface.x + 10, self.rect_surface.bottom + 15,
                            self.rect_surface.w - 20, 35))
        self.btn_relive = Button(lambda _: self.app.relive(), rect_btn,
                                 *createImagesButton(rect_btn.size, "Возродиться"))

    def draw(self):
        self.screen.blit(self.display, (0, 0))
        self.screen.blit(self.surface, self.rect_surface)
        self.btn_relive.draw(self.screen)
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        self.btn_relive.pg_event(event)
        if event.type == pg.KEYDOWN:
            self.app.relive()


# находит позицию xy чтобы один стоял в центре другого
def center_pos_2rects(len1, big_len):
    return big_len // 2 - len1 // 2


class PauseUI(UI):
    def init_ui(self):
        self.rect = pg.Rect((0, 0, 320, 400))
        w, h = self.screen.get_size()
        self.rect.center = w // 2, h // 2
        self.surface = pg.Surface(self.rect.size).convert_alpha()
        self.surface.fill((82, 82, 91, 150))

        text = textfont_btn.render(
            f"Пауза", True, "white")
        t_w, t_h = text.get_size()
        self.surface.blit(text, (10, 10))
        # end surf
        # init btns
        btn_size = 250, 35
        btn_pos = center_pos_2rects(btn_size[0], self.rect.w), t_h + 10 + 10
        btn_rect = pg.Rect(btn_pos, btn_size)

        btns = [
            ("Сохранить карту", lambda _: self.app.set_scene(self.app.app.savem_scene)),
            ("Открыть карту", lambda _: self.app.set_scene(self.app.app.openm_scene)),
            ("Справка по игре", lambda _: self.app.app.open_help()),
            ("Телепорт домой", lambda _: self.app.tp_to_home()),
            ("Сохранить и выйти", lambda _: self.app.save_and_exit()),
            ("Выйти", lambda _: self.app.exit()),
            ("1400x800" if FULLSCREEN else "Полный экран", lambda _: self.app.editfullscreen()),
        ]

        self.img_btns = [createImagesButton(btn_rect.size, t, font=textfont_btn)
                         for t, f in btns]
        funcs = [f for t, f in btns]

        self.btns = createVSteckButtons(btn_rect.size, btn_rect.centerx, btn_rect.top, 15, self.img_btns, funcs,
                                        screen_position=(self.rect.x,
                                                         self.rect.y))  # кнопки открывающие карты

    def draw(self):
        self.screen.blit(self.display, (0, 0))
        surface = self.surface.copy()
        for btn in self.btns:
            btn.draw(surface)

        self.screen.blit(surface, self.rect)
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        for btn in self.btns:
            btn.pg_event(event)


cell_size = int(TSIZE * 1.5)  # in interface


class InventoryUI(SurfaceUI):
    cell_size = cell_size

    def __init__(self, inventory, size_table):
        self.inventory = inventory
        super(InventoryUI, self).__init__(((0, 0), WSIZE))
        self.convert_alpha()
        self.fill((0, 0, 0, 0))

        self.table_inventory = SurfaceUI((0, 0, size_table[0] * self.cell_size + 40,
                                          size_table[1] * self.cell_size + 40)).convert_alpha()
        self.table_inventory.rect.center = self.rect.center
        self.work_rect = self.table_inventory.rect

        self.inventory_info_index = None
        self.inventory_info_index_surface = pygame.Surface((1, 1))
        self.top_bg_color = (82, 82, 91, 150)

    def redraw_table_inventory(self):
        self.table_inventory.fill(bg_color)
        self.table_inventory.fill(bg_color_dark,
                                  (20, 20, self.table_inventory.rect.w - 40, self.table_inventory.rect.h - 40))
        # pg.draw.rect(self.table_inventory, self.top_bg_color,)
        x = 20
        y = 20
        i = 0
        cell_size = self.cell_size
        cell_size_2 = cell_size // 2
        for i in range(self.inventory.inventory_size):
            if i > 0 and i % self.inventory.size_table[0] == 0:
                y += cell_size
                x = 20
            color = "#000000"
            # if i == self.inventory.active_cell:
            #     color = "#FFFFFF"
            pygame.draw.rect(self.table_inventory, color,
                             (x, y, self.cell_size, self.cell_size), 1)
            cell = self.inventory[i]
            if cell is not None:
                img = cell.sprite
                iw, ih = img.get_size()
                self.table_inventory.blit(img, (x + cell_size_2 - iw // 2, y + cell_size_2 - ih // 2))
                res = str(cell.count)
                tx, ty = (x + self.cell_size - 4 - 7 * len(res), y + self.cell_size - 15)
                text = textfont.render(res, True, text_color_dark)
                self.table_inventory.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, True, text_color_light)
                self.table_inventory.blit(text, (tx, ty))
            x += cell_size

    def redraw_inventory_info(self):
        item = self.inventory[self.inventory_info_index]
        if item is None:
            self.inventory_info_index = -1
            return
        text = textfont.render(tile_words[item.index], True, text_color_light)
        w, h = text.get_size()
        self.inventory_info_index_surface = pygame.Surface((w + 6, h + 4)).convert_alpha()
        self.inventory_info_index_surface.fill(self.top_bg_color)
        self.inventory_info_index_surface.blit(text, (3, 2))

    def draw(self, surface):
        self.fill(color_none)
        self.table_inventory.draw(self)
        if get_obj_mouse():
            self.blit(get_obj_mouse().sprite, pg.mouse.get_pos())
        elif self.inventory_info_index != -1:
            mx, my = pg.mouse.get_pos()
            self.blit(self.inventory_info_index_surface, (mx, my + 26))
        surface.blit(self, self.rect)

    def convert_table_mpos_to_i(self, pos):
        offset = 20
        i = (pos[0] - (self.table_inventory.rect.x + offset)) // self.cell_size + \
            (pos[1] - (self.table_inventory.rect.y + offset)) // self.cell_size * self.inventory.size_table[0]
        return i

    def pg_event(self, event: pg.event.Event) -> Union[bool, None]:
        if event.type == pg.MOUSEBUTTONDOWN:
            if get_obj_mouse() and not self.work_rect.collidepoint(event.pos):
                # DISCARD ITEM
                discard_vector = (TSIZE * (2 if event.pos[0] > self.rect.centerx else -2), 10)
                self.inventory.discard_item(items=get_obj_mouse(), discard_vector=discard_vector)
                set_obj_mouse(None)
                return True
            i = self.convert_table_mpos_to_i(event.pos)
            if 0 <= i < self.inventory.inventory_size:

                if get_obj_mouse():
                    # PUT OBJ
                    item = self.inventory.get_cell_from_inventory(i)
                    self.inventory.set_cell(i, get_obj_mouse())
                    set_obj_mouse(item)
                    self.inventory.redraw()
                else:
                    # GET OBJ
                    item = None
                    if event.button == pg.BUTTON_LEFT:
                        item = self.inventory.get_cell_from_inventory(i, del_in_inventory=True)
                    elif event.button == pg.BUTTON_RIGHT:
                        _item = self.inventory.get_cell_from_inventory(i, del_in_inventory=False)
                        item = _item.copy()
                        _item.count //= 2
                        item.count -= _item.count
                        if _item.count == 0:
                            self.inventory[i] = None
                        self.inventory.redraw()
                    elif event.button == pg.BUTTON_MIDDLE and self.inventory.owner.creative_mode:
                        item = self.inventory.get_cell_from_inventory(i, del_in_inventory=False).copy()
                        item.count = item.cell_size
                    set_obj_mouse(item, place=(self, i))
                return True
        elif event.type == pg.MOUSEMOTION:
            i = self.convert_table_mpos_to_i(event.pos)
            if self.rect.collidepoint(event.pos) and 0 <= i < self.inventory.inventory_size:
                self.inventory_info_index = i
                self.redraw_inventory_info()
            else:
                self.inventory_info_index = -1
        return False


class InventoryPlayerUI(InventoryUI):
    cell_size = cell_size

    def __init__(self, inventory):
        super(InventoryPlayerUI, self).__init__(inventory, inventory.size_table)
        self.convert_alpha()
        self.fill((0, 0, 0, 0))

        # self.info_surface = SurfaceUI((0, 0, 250, 80)).convert_alpha()

        self.work_inventory = SurfaceUI((15, 15, self.inventory.size_table[0] * self.cell_size,
                                         self.cell_size)).convert_alpha()
        self.table_inventory = SurfaceUI((0, 0, self.inventory.size_table[0] * self.cell_size + 40,
                                          self.inventory.size_table[1] * self.cell_size + 10 + 40)).convert_alpha()
        self.work_inventory.rect.centerx = self.rect.centerx
        self.table_inventory.rect.center = self.rect.center
        self.work_rect = self.table_inventory.rect

        self.inventory_info_index = -1
        self.inventory_info_index_surface = pygame.Surface((1, 1))
        self.top_bg_color = (82, 82, 91, 150)
        self.recipes = ScrollSurfaceRecipes(self.inventory,
                                            pg.Rect((0, 0, self.cell_size * 5, self.table_inventory.rect.h)))
        self.recipes.rect.y = self.table_inventory.rect.y
        self.recipes.rect.left = self.table_inventory.rect.right + 20

        self.all_tiles = ScrollSurfaceAllTiles(self.inventory, self.recipes.rect)

        self.opened_full_inventory = False

    def redraw_table_inventory(self):
        self.table_inventory.fill(bg_color)
        self.table_inventory.fill(bg_color_dark,
                                  (20, 20, self.table_inventory.rect.w - 40, self.table_inventory.rect.h - 40))
        x = 20
        y = 20
        i = 0
        cell_size_2 = cell_size // 2
        for i in range(self.inventory.inventory_size):
            if i == self.inventory.size_table[0]:
                y += 10
            if i > 0 and i % self.inventory.size_table[0] == 0:
                y += cell_size
                x = 20
            color = "#000000"
            if i == self.inventory.active_cell:
                color = "#FFFFFF"
            pygame.draw.rect(self.table_inventory, color,
                             (x, y, self.cell_size, self.cell_size), 1)
            cell = self.inventory[i]
            if cell is not None:
                img = cell.sprite
                iw, ih = img.get_size()
                self.table_inventory.blit(img, (x + cell_size_2 - iw // 2, y + cell_size_2 - ih // 2))
                res = str(cell.count)
                tx, ty = (x + self.cell_size - 4 - 7 * len(res), y + self.cell_size - 15)
                text = textfont.render(res, True, text_color_dark)
                self.table_inventory.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, True, text_color_light)
                self.table_inventory.blit(text, (tx, ty))
            x += cell_size

    def redraw_top(self):
        self.recipes.redraw()
        self.redraw_table_inventory()
        self.work_inventory.fill(self.top_bg_color)
        x = 0
        y = 0
        i = 0
        cell_size = self.cell_size
        cell_size_2 = cell_size // 2
        for i in range(self.inventory.size_table[0]):
            color = "#000000"
            if i == self.inventory.active_cell:
                color = "#FFFFFF"
            pygame.draw.rect(self.work_inventory, color,
                             (x, 0, self.cell_size, self.cell_size), 1)
            cell = self.inventory[i]
            if cell is not None:
                img = cell.sprite
                iw, ih = img.get_size()
                self.work_inventory.blit(img, (x + cell_size_2 - iw // 2, cell_size_2 - ih // 2))
                res = str(cell.count)
                tx, ty = (x + self.cell_size - 4 - 7 * len(res), y + self.cell_size - 15)
                text = textfont.render(res, True, text_color_dark)
                self.work_inventory.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, True, text_color_light)
                self.work_inventory.blit(text, (tx, ty))
            x += cell_size

    def draw(self, surface):
        self.fill(color_none)

        self.work_inventory.draw(self)
        if self.opened_full_inventory:
            # pg.draw.rect(self, bg_color, self.rect)
            self.table_inventory.draw(self)
            if self.inventory.owner.creative_mode:
                self.all_tiles.draw(self)
            else:
                self.recipes.draw(self)
            if get_obj_mouse():
                self.blit(get_obj_mouse().sprite, pg.mouse.get_pos())
            elif self.inventory_info_index != -1:
                mx, my = pg.mouse.get_pos()
                self.blit(self.inventory_info_index_surface, (mx, my + 26))
        else:
            if self.inventory_info_index != -1:
                self.blit(self.inventory_info_index_surface,
                          (self.work_inventory.rect.x + self.inventory_info_index * self.cell_size,
                           self.work_inventory.rect.y + self.cell_size))

        surface.blit(self, self.rect)

    def convert_table_mpos_to_i(self, pos):
        offset = 20
        sy = (self.table_inventory.rect.y + offset + self.cell_size + 10)
        i = -1
        if pos[1] > sy:
            i = self.inventory.size_table[0] + (
                    pos[0] - (self.table_inventory.rect.x + offset)) // self.cell_size + (
                        pos[1] - sy) // self.cell_size * self.inventory.size_table[0]
        else:
            if (self.table_inventory.rect.y + offset) < pos[1] < (
                    self.table_inventory.rect.y + offset + self.cell_size):
                i = (pos[0] - (self.table_inventory.rect.x + offset)) // self.cell_size
        return i

    def pg_event(self, event: pg.event.Event):
        if self.opened_full_inventory:
            if self.inventory.owner.creative_mode:
                if self.all_tiles.pg_event(event):
                    return True
            else:
                if self.recipes.pg_event(event):
                    return True
        if event.type == pg.KEYDOWN and event.key == pg.K_e:
            # OPEN OR CLOSE  full INVENTORY
            self.opened_full_inventory = not self.opened_full_inventory
            self.recipes.info_index = None
            self.inventory_info_index = -1
            return True
        if self.opened_full_inventory:
            if super(InventoryPlayerUI, self).pg_event(event):
                return True
        else:
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == pg.BUTTON_LEFT:
                    if self.work_inventory.rect.collidepoint(event.pos):
                        i = (event.pos[0] - self.work_inventory.rect.x) // self.cell_size
                        self.inventory.choose_active_cell(i)
                        return True
            elif event.type == pg.MOUSEMOTION:
                if self.work_inventory.rect.collidepoint(event.pos):
                    i = (event.pos[0] - self.work_inventory.rect.x) // self.cell_size
                    self.inventory_info_index = i
                    self.redraw_inventory_info()
                else:
                    self.inventory_info_index = -1
        return False


class InventoryPlayerChestUI(SurfaceUI):
    def __init__(self, player_inventory):
        super(InventoryPlayerChestUI, self).__init__(((0, 0), WSIZE))
        self.player_inventory_ui = InventoryPlayerUI(player_inventory)
        self.player_inventory_ui.opened_full_inventory = True
        self.player_inventory_ui.table_inventory.rect.y = 100

        self.chest_inventory_ui = InventoryUI(None, Chest_size_table)
        self.chest_inventory_ui.table_inventory.rect.y = self.player_inventory_ui.table_inventory.rect.bottom + 40
        self.work_rect = pg.Rect.union(self.chest_inventory_ui.work_rect, self.player_inventory_ui.work_rect)
        self.player_inventory_ui.work_rect = self.chest_inventory_ui.work_rect = self.work_rect
        set_obj_mouse(None)
        self.opened = False

    def set_chest_inventory(self, chest_inventory):
        self.chest_inventory_ui.inventory = chest_inventory
        self.chest_inventory_ui.redraw_table_inventory()
        self.player_inventory_ui.opened_full_inventory = True

    def draw(self, surface):
        self.player_inventory_ui.redraw_table_inventory()
        self.chest_inventory_ui.redraw_table_inventory()
        self.player_inventory_ui.draw(surface)
        self.chest_inventory_ui.draw(surface)
        if get_obj_mouse():
            mx, my = pg.mouse.get_pos()
            self.blit(get_obj_mouse().sprite, (mx, my))
        self.opened = self.player_inventory_ui.opened_full_inventory

    def pg_event(self, event: pg.event.Event):
        res = self.player_inventory_ui.pg_event(event)
        res = self.chest_inventory_ui.pg_event(event) or res
        return res


class ScrollSurfaceRecipes(ScrollSurface):
    cell_size = cell_size
    count_cells = len(RECIPES)

    def __init__(self, inventory, rect, scroll_size=(5 * cell_size, ceil(len(RECIPES) / 5) * cell_size)):
        super(ScrollSurfaceRecipes, self).__init__(rect, scroll_size=scroll_size, background=bg_color)
        self.info_index = None
        self.info_index_surface = None
        self.inventory = inventory

    def redraw_recipes_info(self):
        out, recipe = RECIPES[self.info_index]
        tx = 3
        ty = 3
        name = tile_words[out[0]]
        name_surface = textfont.render(name, True, text_color_light)
        span = textfont.get_height() + 3
        self.info_index_surface = pygame.Surface(
            (max(140, name_surface.get_width() + 6), span * (len(recipe) + 3)),
            pygame.SRCALPHA,
            32)
        self.info_index_surface.fill(bg_color)
        self.info_index_surface.blit(name_surface, (tx, ty))
        ty += span
        self.info_index_surface.blit(textfont.render("-" * 50, True, text_color_light), (0, ty))
        ty += span
        for index, cnt in recipe:
            res = f"{tile_words[index]}: {cnt if cnt > 0 else ''}"
            text = textfont.render(res, True, text_color_light)
            self.info_index_surface.blit(text, (tx, ty))
            ty += span

    def redraw(self):
        gray_cell = Surface((self.cell_size, self.cell_size - 1)).convert_alpha()
        gray_cell.fill("#A3A3A3AA")
        self.scroll_surface.fill(color_none)
        x = 0
        y = 0
        i = 0
        cell_size_2 = self.cell_size // 2
        for i in range(len(RECIPES)):
            if i % 5 == 0 and i > 0:
                y += cell_size
                x = 0
            color = "#000000"
            pygame.draw.rect(self.scroll_surface, color,
                             (x, y, self.cell_size, self.cell_size - 1), 1)
            cell = RECIPES[i][0]
            img = tile_imgs[cell[0]]
            iw, ih = img.get_size()
            self.scroll_surface.blit(img, (x + cell_size_2 - iw // 2, y + cell_size_2 - ih // 2))
            res = str(cell[1])
            tx, ty = (x + self.cell_size - 4 - 7 * len(res), y + self.cell_size - 15)

            text = textfont.render(res, True, text_color_dark)
            self.scroll_surface.blit(text, (tx + 1, ty + 1))
            text = textfont.render(res, True, text_color_light)
            self.scroll_surface.blit(text, (tx, ty))
            if cell[0] not in self.inventory.available_create_items:
                self.scroll_surface.blit(gray_cell, (x, y))
            x += self.cell_size

    def draw(self, surface):
        self.main_scrolling()
        self.fill(bg_color)
        self.inventory.update_available_create_items()
        self.redraw()
        self.blit(self.scroll_surface, self.scroll_surface.rect)
        surface.blit(self, self.rect)
        if self.info_index is not None:
            mx, my = pg.mouse.get_pos()
            surface.blit(self.info_index_surface, (mx, my + 26))

    def creating_item_of_i(self, i, cnt=1):
        self.inventory.creating_item_of_i(i, cnt=cnt)

    def pg_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                event.pos = (event.pos[0] - self.scroll_surface.rect.x, event.pos[1] - self.scroll_surface.rect.y)
                if event.button in (pg.BUTTON_LEFT, pg.BUTTON_MIDDLE):
                    i = (event.pos[0] - self.rect.x) // self.cell_size + (
                            event.pos[1] - self.rect.y) // self.cell_size * 5
                    if i < self.count_cells:
                        cnt = 1
                        if self.inventory.owner.creative_mode and event.button == pg.BUTTON_MIDDLE:
                            cnt = 999
                        self.creating_item_of_i(i, cnt=cnt)
                    return True
        elif event.type == pg.MOUSEWHEEL:
            if self.rect.collidepoint(pg.mouse.get_pos()):
                self.mouse_scroll(dy=event.y * self.cell_size // 3)
                self.info_index = None
                return True
        elif event.type == pg.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                event.pos = (event.pos[0] - self.scroll_surface.rect.x, event.pos[1] - self.scroll_surface.rect.y)
                i = (event.pos[0] - self.rect.x) // self.cell_size + (
                        event.pos[1] - self.rect.y) // self.cell_size * 5
                if 0 <= i < self.count_cells:
                    if i != self.info_index:
                        self.info_index = i
                        self.redraw_recipes_info()
                else:
                    self.info_index = None
            else:
                self.info_index = None


class ScrollSurfaceAllTiles(ScrollSurfaceRecipes):
    cell_size = cell_size
    count_cells = len(tile_words)

    def __init__(self, inventory, rect):
        scroll_size = (5 * cell_size, ceil(len(tile_words) / 5) * cell_size)
        super(ScrollSurfaceAllTiles, self).__init__(inventory, rect, scroll_size=scroll_size)
        self.redraw()

    def redraw_recipes_info(self):
        ttile, name = list(tile_words.items())[self.info_index]
        name_surface = textfont.render(name, True, text_color_light)
        self.info_index_surface = pygame.Surface(
            (name_surface.get_width() + 6, textfont.get_height() + 3),
            pygame.SRCALPHA,
            32)
        self.info_index_surface.fill(bg_color)
        self.info_index_surface.blit(name_surface, (3, 3))

    def redraw(self):
        self.scroll_surface.fill(color_none)
        x = 0
        y = 0
        i = 0
        cell_size_2 = cell_size // 2
        for i in range(len(tile_words)):
            if i % 5 == 0 and i > 0:
                y += cell_size
                x = 0
            color = "#000000"
            pygame.draw.rect(self.scroll_surface, color,
                             (x, y, self.cell_size, self.cell_size - 1), 1)
            ttile = list(tile_words.keys())[i]
            img = tile_imgs[ttile]
            iw, ih = img.get_size()
            self.scroll_surface.blit(img, (x + cell_size_2 - iw // 2, y + cell_size_2 - ih // 2))
            x += cell_size

    def creating_item_of_i(self, i, cnt=1):
        ttile = list(tile_words.keys())[i]
        if ttile in TOOLS:
            item = TOOLS[ttile](self.inventory.owner.game)
            item.set_owner(self)
        else:
            item = ItemsTile(self.inventory.owner.game, ttile, count=cnt)
        self.inventory.put_to_inventory(item)
