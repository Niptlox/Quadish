from pygame import Surface

from units.Texture import BLACK, WHITE
from units.Tiles import tile_imgs, sky, tile_words, live_imgs, bg_live_img
from units.UI.Button import createImagesButton, createVSteckButtons, Button
from units.common import *
from units.UI.ClassUI import SurfaceUI, UI, SurfaceAlphaUI

# INIT TEXT ==================================================

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


# =============================================================


class GameUI(UI):
    def __init__(self, app) -> None:
        super().__init__(app)

    def init_ui(self):
        super().init_ui()
        # self.sky_surface = pg.Surface(self.display.get_size()).convert_alpha()
        # self.sky_surface.fill(sky)

        self.info_surface = pygame.Surface((200, 80), pygame.SRCALPHA, 32)

        self.cell_size = TSIZE + 7
        self.inventory_rect = pg.Rect((0, 0, self.cell_size * self.app.player.inventory_size, self.cell_size))
        self.top_surface = pygame.Surface(self.inventory_rect.size).convert_alpha()
        self.inventory_info_index = None
        self.inventory_info_index_surface = pygame.Surface((1, 1))
        self.top_bg_color = (82, 82, 91, 150)
        self.recipes_rect = pg.Rect((0, TSIZE + 10, self.cell_size * len(RECIPES), self.cell_size))
        self.recipes_surface = pygame.Surface(self.recipes_rect.size, pygame.SRCALPHA, 32)
        self.recipes_info_index = None
        self.recipes_info_index_surface = pygame.Surface((1, 1))
        self.redraw_recipes()
        self.app.player.choose_active_cell()

        self.sys_message_rect = pg.Rect(((WSIZE[0] - 330, WSIZE[1] - 45), (300, 32)))
        self.sys_message_text = ""
        self.sys_message_left_tact = 0
        self.sys_message_count_tact = 0
        self.sys_message_surface = pg.Surface(self.sys_message_rect.size).convert_alpha()

        # self.playerui = SurfaceAlphaUI((0, 0, 280, 120))
        self.playerui = SurfaceAlphaUI((0, 0, 450, 420))
        self.playerui.rect.bottom = self.rect.bottom
        self.new_sys_message("Привет игрок")

    def draw_sky(self):
        # self.display.blit(self.sky_surface, (0, 0))
        self.display.fill(sky)

    def draw(self):
        # DRAW DISPLAY GAME TO WINDOW ========================================

        self.display.blit(self.top_surface, (0, 0))
        self.display.blit(self.recipes_surface, self.recipes_rect)
        if self.recipes_info_index is not None:
            self.display.blit(self.recipes_info_index_surface,
                              (
                                  self.recipes_rect.x + self.recipes_info_index * self.cell_size,
                                  self.recipes_rect.bottom))
        if self.inventory_info_index is not None:
            self.display.blit(self.inventory_info_index_surface,
                              (self.inventory_info_index * self.cell_size, self.cell_size))
        if show_info_menu:
            self.display.blit(self.info_surface, (WINDOW_SIZE[0] - 200, 0))
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

    def new_sys_message(self, text, count_tact=FPS * 3):
        self.sys_message_text = text
        self.sys_message_left_tact = count_tact
        self.sys_message_count_tact = count_tact
        self.sys_message_surface.set_alpha(255)
        self.sys_message_surface.fill(sys_message_bg)
        text_msg = textfont_sys_msg.render(text, 1, "#FDE047")

        self.sys_message_surface.blit(text_msg, (5, 5))

    def redraw_info(self):
        true_fps = self.app.clock.get_fps()
        self.info_surface.fill(self.top_bg_color)
        text_fps = textfont_info.render(
            f" fps: {int(true_fps)}", 1, "white")
        text_pos_real = textfont_info.render(
            f"rpos: {self.app.player.rect.x, self.app.player.rect.y}", 1, "white")
        text_pos = textfont_info.render(
            f" pos: {self.app.player.rect.x // TSIZE, self.app.player.rect.y // TSIZE}", 1, "white")
        text_ents = textfont_info.render(
            f"Ents: {len(self.app.screen_map.dynamic_tiles)}", 1, "white")
        self.info_surface.blit(text_fps, (8, 5))
        self.info_surface.blit(text_pos_real, (8, 25))
        self.info_surface.blit(text_pos, (8, 45))
        self.info_surface.blit(text_ents, (8, 65))

    def redraw_top(self):
        self.top_surface.fill(self.top_bg_color)
        x = 0
        i = 0
        cell_size = self.cell_size
        cell_size_2 = cell_size // 2
        for i in range(self.app.player.inventory_size):
            color = "#000000"
            if i == self.app.player.active_cell:
                color = "#FFFFFF"
            pygame.draw.rect(self.top_surface, color,
                             (x, 0, TSIZE + 7, TSIZE + 7), 1)
            cell = self.app.player.inventory[i]
            if cell is not None:
                img = cell.sprite
                iw, ih = img.get_size()
                self.top_surface.blit(img, (x + cell_size_2 - iw // 2, cell_size_2 - ih // 2))
                res = str(cell.count)
                tx, ty = (x + TSIZE + 3 - 7 * len(res), TSIZE - 8)
                text = textfont.render(res, 1, text_color_dark)
                self.top_surface.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, 1, text_color_light)
                self.top_surface.blit(text, (tx, ty))
            x += cell_size

    def redraw_recipes(self):
        self.recipes_surface.fill(self.top_bg_color)
        x = 0
        i = 0
        cell_size = self.cell_size
        cell_size_2 = cell_size // 2
        for i in range(len(RECIPES)):
            color = "#000000"
            pygame.draw.rect(self.recipes_surface, color,
                             (x, 0, TSIZE + 7, TSIZE + 7), 1)
            cell = RECIPES[i][0]
            img = tile_imgs[cell[0]]
            iw, ih = img.get_size()
            self.recipes_surface.blit(img, (x + cell_size_2 - iw // 2, cell_size_2 - ih // 2))
            res = str(cell[1])
            tx, ty = (x + TSIZE + 3 - 7 * len(res), TSIZE - 8)
            text = textfont.render(res, 1, text_color_dark)
            self.recipes_surface.blit(text, (tx + 1, ty + 1))
            text = textfont.render(res, 1, text_color_light)
            self.recipes_surface.blit(text, (tx, ty))
            x += cell_size

    def redraw_recipes_info(self):
        out, recipe = RECIPES[self.recipes_info_index]
        tx = 3
        ty = 3
        span = textfont.get_height() + 3
        self.recipes_info_index_surface = pygame.Surface((self.cell_size * 3.5, span * (len(recipe) + 3)),
                                                         pygame.SRCALPHA,
                                                         32)
        self.recipes_info_index_surface.fill(self.top_bg_color)
        name = tile_words[out[0]]
        self.recipes_info_index_surface.blit(textfont.render(name, True, text_color_light), (tx, ty))
        ty += span
        self.recipes_info_index_surface.blit(textfont.render("-" * 50, True, text_color_light), (0, ty))
        ty += span
        for index, cnt in recipe:
            res = f"{tile_words[index]}: {cnt if cnt > 0 else ''}"
            text = textfont.render(res, 1, text_color_light)
            self.recipes_info_index_surface.blit(text, (tx, ty))
            ty += span

    def redraw_inventory_info(self):
        item = self.app.player.inventory[self.inventory_info_index]
        if item is None:
            self.inventory_info_index = None
            return
        text = textfont.render(tile_words[item.index], True, text_color_light)
        w, h = text.get_size()
        self.inventory_info_index_surface = pygame.Surface((w + 6, h + 4)).convert_alpha()
        self.inventory_info_index_surface.fill(self.top_bg_color)
        self.inventory_info_index_surface.blit(text, (3, 2))

    def redraw_playerui(self):
        self.playerui.fill(color_none)
        cnt_in_row = 15
        step = live_imgs[0].get_width() + 5
        x, y = 10, self.playerui.rect.h - step - 5
        for i in range(self.app.player.max_lives // 10):
            if i * 10 < self.app.player.lives:
                self.playerui.blit(live_imgs[0], (x, y))
            else:
                if (i - 1) * 10 < self.app.player.lives and self.app.player.lives % 10 > 0:
                    self.playerui.blit(live_imgs[4 - self.app.player.lives % 10 // 2], (x, y))
                else:
                    self.playerui.blit(bg_live_img, (x, y))

            x += step
            if (i + 1) % cnt_in_row == 0:
                y -= step
                x = 10

    def pg_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == pg.BUTTON_LEFT:
                if self.recipes_rect.collidepoint(event.pos):
                    i = (event.pos[0] - self.recipes_rect.x) // self.cell_size
                    self.app.player.creating_item_of_i(i)
                    return True
        elif event.type == pg.MOUSEMOTION:
            if self.recipes_rect.collidepoint(event.pos):
                self.inventory_info_index = None
                i = (event.pos[0] - self.recipes_rect.x) // self.cell_size
                if i != self.recipes_info_index:
                    self.recipes_info_index = i
                    self.redraw_recipes_info()
            elif self.inventory_rect.collidepoint(event.pos):
                self.recipes_info_index = None
                i = (event.pos[0] - self.inventory_rect.x) // self.cell_size
                if i != self.recipes_info_index:
                    self.inventory_info_index = i
                    self.redraw_inventory_info()
            else:
                self.recipes_info_index = None
                self.inventory_info_index = None

        return False


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

    def pg_event(self, event: pg.event.Event):
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


# находит позицию xy чтобы один стоял в центре другого
def center_pos_2rects(len1, big_len):
    return big_len // 2 - len1 // 2


class PauseUI(UI):
    def init_ui(self):
        self.rect = pg.Rect((0, 0, 320, 320))
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
