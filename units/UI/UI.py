from math import ceil
from typing import Union

from pygame import Surface

from units.Achievements import achievements
from units.Items import ItemsTile, Items
from units.Texture import WHITE
from units.Tiles import tile_imgs, sky, tile_words, live_imgs, bg_live_img, goldlive_imgs, bg_livecreative_img, \
    title_background, title_text, title_background_layer_2
from units.Tools import TOOLS
from units.UI.Button import createImagesButton, createVSteckButtons, Button, createVSteckTextButtons, ChangeTextButton
from units.UI.ClassUI import SurfaceUI, UI, ScrollSurface, GroupUI
from units.common import *

# INIT TEXT ==================================================
from units.creating_items import RECIPES
from units.outline import add_outline_to_image
from units.sound import set_category_volume

pygame.font.init()
# textfont = pygame.font.SysFont('Jokerman', 19)
textfont = pygame.font.Font('data/fonts/xenoa.ttf', 12, )  # yes rus
textfont_sys_msg = pygame.font.Font('data/fonts/xenoa.ttf', 21, )  # yes rus
# textfont = pygame.font.Font('data/fonts/Teletactile.ttf', 10, bold=True)
textfont_info = pygame.font.Font('data/fonts/Teletactile.ttf', 10, )  # no rus
textfont_btn = pygame.font.SysFont("Fenix", 35, )

textfont_btn = pygame.font.Font('data/fonts/xenoa.ttf', 28, )  # rus

# texframe = font.render(text, False, text_color)
text_color = "#1C1917"
text_color_dark = "#1C1917"
text_color_light = "#F5F5F4"

sys_message_bg = (68, 64, 60, 150)

color_none = (0, 0, 0, 0)

bg_color = (82, 82, 91, 150)
bg_color_dark = (52, 52, 51, 150)

# =============================================================

ru_bool_lst = ["Вкл", "Выкл"]
eng_bool_lst = [True, False]
bool_dict = {ru_bool_lst[0]: eng_bool_lst[0], ru_bool_lst[1]: eng_bool_lst[1]}

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


class SysMessege:
    bg = (82, 82, 91, 150)
    rect = pg.Rect((WSIZE[0] - 330, WSIZE[1] - 45), (300, 32))

    def __init__(self):
        self.left_tact = 0
        self.count_tact = 0
        self.surface = pg.Surface(self.rect.size).convert_alpha()

    def new(self, text, count_tact=FPS * 3):
        self.left_tact = count_tact
        self.count_tact = count_tact
        self.surface.set_alpha(255)
        self.surface.fill(self.bg)
        text_msg = textfont_sys_msg.render(text, True, "#FDE047")
        self.surface.blit(text_msg, (5, 5))

    def draw(self, surface):
        if self.left_tact > 0:
            self.left_tact -= 1
            if self.left_tact < 32:
                self.surface.set_alpha(self.left_tact * 8)
            elif (self.count_tact - self.left_tact) < 8:
                self.surface.set_alpha((self.count_tact - self.left_tact) * 32)

            surface.blit(self.surface, self.rect)


class AchievementMessege(SysMessege):
    rect = pg.Rect((WSIZE[0] - 330, WSIZE[1] - 75), (300, 62))
    font_title = pygame.font.SysFont("Fenix", 28, )  # yes rus
    font_text = pygame.font.SysFont("Fenix", 24, )  # yes rus

    def new(self, id_name):
        count_tact = FPS * 3
        self.left_tact = count_tact
        self.count_tact = count_tact
        self.surface.set_alpha(255)
        self.surface.fill(self.bg)
        ach = achievements[id_name]
        title = self.font_title.render(ach["title"], True, "#FDE047")
        self.surface.blit(title, (5, 5))

        text = self.font_text.render(ach["description"], True, "#FFFFFF")
        self.surface.blit(text, (10, title.get_height() + 10))


# =============================================================

class GameUI(UI):
    def __init__(self, scene) -> None:
        super().__init__(scene)
        self.info_surface = SurfaceUI((0, 0, 250, 100)).convert_alpha()
        self.sys_message = SysMessege()
        self.achievement_message = AchievementMessege()
        # self.playerui = SurfaceAlphaUI((0, 0, 280, 120))
        self.playerui = SurfaceUI((0, 0, 450, 420)).convert_alpha()
        # self.playerui.rect.bottom = self.rect.bottom
        self.new_sys_message("Привет игрок")

    def draw_sky(self):
        # self.display.blit(self.sky_surface, (0, 0))
        sky_night = (15, 23, 42, 255)
        sky = (165, 243, 252, 255)
        sky_red = (135, 0, 0, 255)
        # if self.
        self.display.fill(sky)

    def draw(self):
        # DRAW DISPLAY GAME TO WINDOW ========================================
        if show_info_menu:
            self.display.blit(self.info_surface, (WINDOW_SIZE[0] - 250, 0))

        self.sys_message.draw(self.display)
        self.achievement_message.draw(self.display)
        self.redraw_playerui()
        self.playerui.draw(self.display)
        # pygame.transform.scale(display,(WINDOW_SIZE[0]//1.8, WINDOW_SIZE[1]//1.8)), (100, 100)

    def flip(self):
        self.screen.blit(self.display, (0, 0))
        pygame.display.flip()

    def new_sys_message(self, text, count_tact=FPS * 3, draw_now=False):
        self.sys_message.new(text, count_tact)
        if draw_now:
            self.draw()

    def new_achievement_completed(self, id_name):
        self.achievement_message.new(id_name)

    def redraw_info(self):
        true_fps = self.scene.clock.get_fps()
        self.info_surface.fill(bg_color)
        text_fps = textfont_info.render(
            f" fps: {int(true_fps)}", True, "white")
        text_pos_real = textfont_info.render(
            f"rpos: {self.scene.player.rect.x, self.scene.player.rect.y}", True, "white")
        text_pos = textfont_info.render(
            f" pos: {self.scene.player.rect.x // TSIZE, self.scene.player.rect.y // TSIZE}", True, "white")
        text_ents = textfont_info.render(
            f"Ents: {len(self.scene.screen_map.dynamic_tiles)}", True, "white")
        chunk_ents = self.scene.game_map.chunk(self.scene.player.update_chunk_pos())
        if chunk_ents is not None:
            chunk_ents = chunk_ents[3][1]
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
        cnt_in_row = 10
        step = imgs[0].get_width() + 5
        x, y = 10, self.playerui.rect.h - step - 5
        startx, starty = x, y
        iy = 0

        for i in range(self.scene.player.max_lives // lives_in_heart):
            if i == cnt_in_row * 2:
                x, y = startx, starty
                iy = 0
                imgs = goldlive_imgs
            if self.scene.player.creative_mode:
                self.playerui.blit(bg_livecreative_img, (x - 2, y - 2))
            if i < self.scene.player.lives // lives_in_heart:
                self.playerui.blit(imgs[0], (x, y))
            else:
                if (i - 1) < self.scene.player.lives // lives_in_heart and self.scene.player.lives % lives_in_heart > 0:
                    self.playerui.blit(imgs[4 - self.scene.player.lives % lives_in_heart // 2], (x, y))
                else:
                    if i < cnt_in_row * 2:
                        self.playerui.blit(bg_live_img, (x, y))

            x += step
            if (i + 1) % cnt_in_row == 0:
                y -= 15
                iy += 2
                x = startx + iy


class TitleUI(UI):
    color_sky = "#a5f3fc"
    background = title_background
    background_layer_2 = title_background_layer_2
    background = pg.transform.scale(background, (int(WSIZE[0] * 1.5), int(WSIZE[1] * 1.5)))
    background_layer_2 = pg.transform.scale(background_layer_2, background.get_size())
    background.set_colorkey(color_sky)
    game_title_text = title_text
    step_objects = 15

    def __init__(self, scn):
        super(TitleUI, self).__init__(scn)
        self.objects = GroupUI([])
        print(self.scene, self)

        self.bg_x, self.bg_y = 0, 0
        self.bg2_x, self.bg2_y = 0, 0

        btns = [
            ("Новый мир", lambda _: self.scene.new_game()),
            ("Настройки", lambda _: self.scene.set_ui(self.scene.settings_ui)),
            ("Справка", lambda _: self.scene.app.open_help()),
            ("Выйти", lambda _: self.scene.exit()),

        ]

        btn_size = 250, 35
        step = self.step_objects
        btn_pos = 230, 300
        btn_pos = self.rect.w // 2 - btn_size[0] // 2, self.rect.h // 2 - (btn_size[1] + step) / 2 * len(btns) + 40

        btn_rect = pg.Rect(btn_pos, btn_size)

        self.img_btns = [createImagesButton(btn_rect.size, t, font=textfont_btn)
                         for t, f in btns]
        funcs = [f for t, f in btns]

        obj_btns = createVSteckButtons(btn_rect.size, btn_rect.centerx, btn_rect.top, step, self.img_btns, funcs,
                                       screen_position=(self.rect.x, self.rect.y))  # кнопки открывающие карты

        self.objects.add_lst(obj_btns)
        _font_dev_btn = pygame.font.Font('data/fonts/xenoa.ttf', 23, )
        dev_but = Button(lambda _: self.scene.open_developers(),
                         (self.rect.w - 200, self.rect.h - 60, 175, 35),
                         *createImagesButton((175, 35), "Разработчики", font=_font_dev_btn))
        self.objects.add(dev_but)
        self.tts = title_text_surf = SurfaceUI(((0, 0), self.game_title_text.get_size()))
        title_text_surf.blit(self.game_title_text, (0, 0))
        title_text_surf.set_colorkey(self.color_sky)
        title_text_surf.rect.centerx = self.rect.centerx
        title_text_surf.rect.top = center_pos_2lens(title_text_surf.rect.h, self.rect.h) - 220
        self.tts_scale = 1.05
        self.tts_speed = 0.005
        self.tts_size = self.tts.rect.size
        self.objects.add(title_text_surf)
        print("objects", self.objects.components)

    def draw_background(self):
        self.screen.fill(self.color_sky)
        x, y = pg.mouse.get_pos()
        c = 4
        nx, ny = x // 40 - self.rect.w // 2, y // 40 - self.rect.h // 2
        if self.bg2_x == 0 and self.bg2_y == 0:
            self.bg2_x, self.bg2_y = nx, ny
        else:
            self.bg2_x += (nx - self.bg2_x) // c
            self.bg2_y += (ny - self.bg2_y) // c
        self.screen.blit(self.background_layer_2, (self.bg2_x, self.bg2_y))

        nx, ny = x // 20 - self.rect.w // 2, y // 20 - self.rect.h // 2
        if self.bg_x == 0 and self.bg_y == 0:
            self.bg_x, self.bg_y = nx, ny
        else:
            self.bg_x += (nx - self.bg_x) // c
            self.bg_y += (ny - self.bg_y) // c

        self.screen.blit(self.background, (self.bg_x, self.bg_y))
        # self.tts.rect.top = self.tts_y + y // 50
        self.tts_scale += self.tts_speed
        if self.tts_scale > 1.08 or self.tts_scale < 1.01:
            self.tts_speed *= 0
        tts = pg.transform.smoothscale(self.game_title_text,
                                       (self.tts_size[0] * self.tts_scale, self.tts_size[1] * self.tts_scale))
        self.tts.set(tts)
        self.tts.set_colorkey(self.color_sky)
        # self.tts.rect.x = self.tts_x

    def draw(self):

        self.draw_background()
        self.objects.draw(self.screen)
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        self.objects.pg_event(event)


class MainSettingsUI(TitleUI):
    window_sizes_lst = ["1240,720", "720,480"]

    def __init__(self, scene):
        super(MainSettingsUI, self).__init__(scene)
        self.objects = GroupUI([])

        btn_size = 400, 35
        btn_rect = pg.Rect((0, 0), btn_size)

        btns = self.get_pre_buttons(btn_rect)

        step = 15
        btn_pos = self.rect.w // 2 - btn_size[0] // 2, self.rect.h // 2 - (btn_size[1] + step) / 2 * len(btns) + 40
        btn_rect = pg.Rect(btn_pos, btn_size)
        obj_btns = createVSteckTextButtons(btn_rect.size, btn_rect.centerx, btn_rect.top, step, btns,
                                           screen_position=(self.rect.x, self.rect.y),
                                           font=textfont_btn)  # кнопки открывающие карты

        self.objects.add_lst(obj_btns)

        self.tts = title_text_surf = SurfaceUI(((0, 0), self.game_title_text.get_size()))
        title_text_surf.blit(self.game_title_text, (0, 0))
        title_text_surf.set_colorkey(self.color_sky)
        title_text_surf.rect.topleft = center_pos_2lens(title_text_surf.rect.w, self.rect.w), \
                                       center_pos_2lens(title_text_surf.rect.h, self.rect.h) - 220
        self.tts_y = title_text_surf.rect.top

        self.objects.add(title_text_surf)

    def get_pre_buttons(self, btn_rect):
        if config.Window.size in self.window_sizes_lst:
            size_start_state_index = self.window_sizes_lst.index(config.Window.size)
        else:
            self.window_sizes_lst.append(config.Window.size)
            size_start_state_index = len(self.window_sizes_lst) - 1

        btns = [
            ChangeTextButton(lambda _, state: config.Window.set_size(state), btn_rect, "Размер ({})",
                             states_text_lst=self.window_sizes_lst, start_state_index=size_start_state_index),
            ChangeTextButton(lambda _, state: config.Window.set_fullscreen(bool_dict[state]), btn_rect,
                             "Полноэкранный режим: {}", states_text_lst=ru_bool_lst,
                             start_state_index=eng_bool_lst.index(config.Window.fullscreen)),
            ChangeTextButton(lambda _, state: config.GameSettings.set_clouds_state(bool_dict[state]), btn_rect,
                             "Отображение облаков: {}", states_text_lst=ru_bool_lst,
                             start_state_index=eng_bool_lst.index(config.GameSettings.clouds)),
            ChangeTextButton(lambda _, state: config.GameSettings.set_stars_state(bool_dict[state]), btn_rect,
                             "Отображение звёзд: {}", states_text_lst=ru_bool_lst,
                             start_state_index=eng_bool_lst.index(config.GameSettings.stars)),
            ChangeTextButton(lambda _, state: config.GameSettings.set_item_index_state(bool_dict[state]), btn_rect,
                             "ID предмета: {}", states_text_lst=ru_bool_lst,
                             start_state_index=eng_bool_lst.index(config.GameSettings.view_item_index)),
            ("Звуки и музыка...", lambda _: self.scene.set_ui(self.scene.sound_settings_ui)),
            ("В главное меню", lambda _: self.scene.set_ui(self.scene.title_ui)),

        ]
        return btns


categories_sounds = {
    "ui",
    'player',
    'creatures',
    'game',
    'background',
}

volume_values_lst = [0, 10, 20, 30, 40, 50, 60, 70, 80, 100]


class SoundSettingsUI(MainSettingsUI):
    def get_pre_buttons(self, btn_rect):
        btns = [
            ("Громкость", lambda _: ()),
            ChangeTextButton(lambda _, state: set_category_volume("background", state / 100), btn_rect, "Музыка {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=volume_values_lst.index(config.VolumeSettings.background_volume * 100)),
            ChangeTextButton(lambda _, state: set_category_volume("player", state / 100), btn_rect, "Игрок {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=volume_values_lst.index(config.VolumeSettings.player_volume * 100)),
            ChangeTextButton(lambda _, state: set_category_volume("creatures", state / 100), btn_rect, "Существа {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=volume_values_lst.index(config.VolumeSettings.creatures_volume * 100)),
            ChangeTextButton(lambda _, state: set_category_volume("ui", state / 100), btn_rect, "Интерфейс {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=volume_values_lst.index(config.VolumeSettings.ui_volume * 100)),
            ("Назад", lambda _: self.scene.set_ui(self.scene.settings_ui)),

        ]
        print(btns)
        return btns


class SwitchMapUI(UI):
    bg = (82, 82, 91, 150)

    def __init__(self, scene, title) -> None:
        self.title = title
        super().__init__(scene)
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

        n = self.scene.game.game_map.save_slots
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
        res = self.scene.open_map(num)


font_end = pygame.font.Font('data/fonts/xenoa.ttf', 28, )  # rus


class EndUI(UI):
    def __init__(self, scn):
        super(EndUI, self).__init__(scn)
        self.rect_surface = pg.Rect((0, 0, 220, 100))
        w, h = self.screen.get_size()
        self.rect_surface.center = w // 2, h // 2
        self.surface = pg.Surface(self.rect_surface.size).convert_alpha()
        self.surface.fill((82, 82, 91, 150))

        text = font_end.render(f"Вы погибли...", True, "red")
        text = add_outline_to_image(text, 2, WHITE)

        w, h = text.get_size()
        self.surface.blit(text, (self.rect_surface.w // 2 - w // 2, self.rect_surface.h // 2 - h // 2))
        rect_btn = pg.Rect((self.rect_surface.x + 10, self.rect_surface.bottom + 15,
                            self.rect_surface.w - 20, 35))

        self.btn_relive = Button(lambda _: self.scene.relive(), rect_btn,
                                 *createImagesButton(rect_btn.size, "Возродиться", font=textfont_btn))

    def draw(self):
        self.screen.blit(self.display, (0, 0))
        self.screen.blit(self.surface, self.rect_surface)
        self.btn_relive.draw(self.screen)
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        self.btn_relive.pg_event(event)
        if event.type == pg.KEYDOWN:
            self.scene.relive()


# находит позицию xy чтобы один стоял в центре другого
def center_pos_2lens(len1, big_len):
    return big_len // 2 - len1 // 2


# находит позицию xy чтобы один стоял в центре другого
def center_pos_2rects(rect, big_rect):
    return center_pos_2lens(rect.w, big_rect.w), center_pos_2lens(rect.h, big_rect.h)


class PauseUI(UI):
    def __init__(self, scene):
        super(PauseUI, self).__init__(scene)
        self.rect = pg.Rect((0, 0, 370, 350))
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
        btn_size = 350, 35
        btn_pos = center_pos_2lens(btn_size[0], self.rect.w), t_h + 10 + 10
        btn_rect = pg.Rect(btn_pos, btn_size)

        btns = [
            ("Сохранить карту", lambda _: self.scene.set_scene(self.scene.app.savem_scene)),
            ("Открыть карту", lambda _: self.scene.set_scene(self.scene.app.openm_scene)),
            ("Достижения", lambda _: self.scene.set_scene(self.scene.app.achievements_scene)),
            ("Как играть", lambda _: self.scene.app.open_help()),
            ("Телепорт домой", lambda _: self.scene.tp_to_home()),
            ("Сохранить и выйти в меню", lambda _: self.scene.save_and_to_main_menu()),
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


class AchievementsUI(UI):
    bg = (82, 82, 91, 150)
    font_title = pygame.font.Font('data/fonts/xenoa.ttf', 28, )
    font_text = pygame.font.Font('data/fonts/xenoa.ttf', 21, )
    font_action = pygame.font.Font('data/fonts/xenoa.ttf', 14, )

    def __init__(self, scene, player_achievements):
        super(AchievementsUI, self).__init__(scene)
        # self.achievements = player_achievements
        self.rect = pg.Rect((0, 0, 370, 400))
        w, h = self.screen.get_size()
        self.rect.center = w // 2, h // 2
        self.surface = pg.Surface(self.rect.size).convert_alpha()
        self.surface.fill((82, 82, 91, 150))
        self.surface_achievements = pg.Surface((1, 1))

    def redraw_achievements(self):
        achievs = self.scene.app.game_scene.player.achievements
        height_block = 105
        height = height_block * len(achievs.completed) + 20
        self.surface_achievements = pg.Surface((self.rect.w, height)).convert_alpha()
        self.surface_achievements.fill(color_none)

        y = 15
        for id_name in achievs.completed:
            ach = achievements[id_name]
            surface = pg.Surface((self.surface_achievements.get_width() - 20, height_block - 10))
            surface.fill("#27272A")
            title = self.font_title.render(ach["title"], True, "#FDE047")
            surface.blit(title, (5, 0))

            pg.draw.line(surface, "#FDE047", (0, title.get_height() + 4), (500, title.get_height() + 4), width=2)

            text = self.font_text.render(ach["description"], True, "#FFFFFF")
            surface.blit(text, (5, title.get_height() + 9))

            text = self.font_action.render(ach["action"], True, "#FFFFFF")
            surface.blit(text, (surface.get_width() // 2 - text.get_width() // 2,
                                title.get_height() * 2 + 7))

            self.surface_achievements.blit(surface, (10, y))
            y += height_block

    def draw(self):
        self.redraw_achievements()
        self.screen.blit(self.display, (0, 0))
        self.surface.fill(self.bg)
        title = textfont_btn.render("Достижения", True, "#FFFFFF")
        self.surface.blit(title, (10, 10))

        self.surface.blit(self.surface_achievements, (0, 35))

        self.screen.blit(self.surface, self.rect)
        pg.display.flip()


cell_size = int(TSIZE * 1.5)  # in interface


class InventoryUI(SurfaceUI):
    cell_size = cell_size

    def __init__(self, inventory, size_table, margin_table=10, ui_owner=None):
        self.ui_owner = ui_owner
        self.inventory = inventory
        self.margin = margin_table
        super(InventoryUI, self).__init__(((0, 0), WSIZE))
        self.convert_alpha()
        self.fill((0, 0, 0, 0))

        self.table_inventory = SurfaceUI((0, 0, size_table[0] * self.cell_size + self.margin * 2,
                                          size_table[1] * self.cell_size + self.margin * 2)).convert_alpha()
        self.table_inventory.rect.center = self.rect.center
        self.work_rect = self.table_inventory.rect

        self.inventory_info_index = None
        self.inventory_info_index_surface = pygame.Surface((1, 1))
        self.top_bg_color = (82, 82, 91, 150)

    def set_work_rect(self, value):
        self.work_rect = value

    def redraw_table_inventory(self):
        self.table_inventory.fill(bg_color)
        self.table_inventory.fill(bg_color_dark,
                                  (self.margin, self.margin, self.table_inventory.rect.w - self.margin * 2,
                                   self.table_inventory.rect.h - self.margin * 2))
        # pg.draw.rect(self.table_inventory, self.top_bg_color,)
        x = self.margin
        y = self.margin
        i = 0
        cell_size = self.cell_size
        cell_size_2 = cell_size // 2
        for i in range(self.inventory.inventory_size):
            if i > 0 and i % self.inventory.size_table[0] == 0:
                y += cell_size
                x = self.margin
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
        string = tile_words[item.index]
        if config.GameSettings.view_item_index:
            string += f" #{item.index}"
        text = textfont.render(string, True, text_color_light)
        w, h = text.get_size()
        self.inventory_info_index_surface = pygame.Surface((w + 6, h + 4)).convert_alpha()
        self.inventory_info_index_surface.fill(self.top_bg_color)
        self.inventory_info_index_surface.blit(text, (3, 2))

    def get_draw_rect(self):
        return self.table_inventory.rect

    def draw(self, surface):
        self.redraw_table_inventory()
        self.fill(color_none)
        self.table_inventory.draw(self)
        if get_obj_mouse():
            self.blit(get_obj_mouse().sprite, pg.mouse.get_pos())
        elif self.inventory_info_index != -1:
            mx, my = pg.mouse.get_pos()
            self.blit(self.inventory_info_index_surface, (mx, my + 26))
        surface.blit(self, self.rect)

    def convert_table_mpos_to_i(self, pos):
        offset = self.margin
        if self.ui_owner:
            offset_ui = self.ui_owner.get_onscreen_pos()
            pos = pos[0] - offset_ui[0], pos[1] - offset_ui[1]
        if self.table_inventory.rect.collidepoint(pos):
            i = (pos[0] - (self.table_inventory.rect.x + offset)) // self.cell_size + \
                (pos[1] - (self.table_inventory.rect.y + offset)) // self.cell_size * self.inventory.size_table[0]
            return i
        return -1

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
                    if self.inventory.flag_not_put_in:
                        return True
                    if self.inventory.filter_items:
                        if get_obj_mouse().index not in self.inventory.filter_items:
                            return True
                    # положить объект из мыши
                    put_item = get_obj_mouse()
                    if event.button == pg.BUTTON_RIGHT:
                        # положить один предмет при нажатии првой кнопкой мыши
                        put_item = put_item.copy()
                        put_item.count = 1
                        get_obj_mouse().count -= 1
                        if get_obj_mouse().count <= 0:
                            set_obj_mouse(None)
                    else:
                        set_obj_mouse(None)
                    item = self.inventory.get_cell_from_inventory(i)
                    if item and item.index == put_item.index and item.count < item.cell_size:
                        put_item.add(item)
                        if item.count <= 0:
                            item = get_obj_mouse()
                    elif item is None:
                        item = get_obj_mouse()
                    else:
                        if get_obj_mouse():
                            put_item.add(get_obj_mouse())
                    self.inventory.set_cell(i, put_item)
                    set_obj_mouse(item)
                    self.inventory.redraw()
                else:
                    # взять объект в мышь
                    item = None
                    if event.button == pg.BUTTON_LEFT:
                        item = self.inventory.get_cell_from_inventory(i, del_in_inventory=True)
                    elif event.button == pg.BUTTON_RIGHT:
                        _item = self.inventory.get_cell_from_inventory(i, del_in_inventory=False)
                        if _item is None:
                            return True
                        item = _item.copy()
                        _item.count //= 2
                        item.count -= _item.count
                        if _item.count == 0:
                            self.inventory[i] = None
                        self.inventory.redraw()
                    elif event.button == pg.BUTTON_MIDDLE and self.inventory.game_map.creative_mode:
                        item = self.inventory.get_cell_from_inventory(i, del_in_inventory=False)
                        if item is None:
                            return True
                        item = item.copy()
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
        self.redraw_table_inventory()

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
        if not self.table_inventory.rect.collidepoint(pos):
            return -1
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


class BlockUI(SurfaceUI):
    def __init__(self, rect):
        super(BlockUI, self).__init__(rect)
        self.block_obj = None
        self.work_rect = self.rect

    def set_block(self, block_obj):
        self.block_obj = block_obj

    def set_work_rect(self, value):
        pass

    def get_draw_rect(self):
        return self.rect

    def get_onscreen_pos(self):
        return self.rect


class ChestUI(InventoryUI):
    def __init__(self):
        super(ChestUI, self).__init__(None, Chest_size_table)

    def set_chest_inventory(self, chest_inventory):
        self.inventory = chest_inventory
        self.redraw_table_inventory()

    def set_block(self, block_obj):
        self.set_chest_inventory(block_obj.inventory)


#         self.fuel_cell = Inventory(self.game_map, self, [1, 1])
#         self.input_cell = Inventory(self.game_map, self, [1, 1])
#         self.result_cell = Inventory(self.game_map, self, [1, 1])

class FurnaceUI(BlockUI):
    background = bg_color

    def __init__(self):
        rect = pg.Rect(0, 0, cell_size * 6, cell_size * 4)
        super(FurnaceUI, self).__init__(rect)
        self.convert_alpha()
        self.input_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.input_inventory_ui.get_draw_rect().topleft = cell_size * 0.5, cell_size * 0.5
        self.fuel_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.fuel_inventory_ui.get_draw_rect().topleft = cell_size * 0.5, cell_size * 2.5
        self.result_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.result_inventory_ui.get_draw_rect().topleft = cell_size * 4.5, cell_size * 1.5
        self.inventories = self.input_inventory_ui, self.fuel_inventory_ui, self.result_inventory_ui
        self._work_rect = None

    def set_work_rect(self, value):
        for inv in self.inventories:
            inv.work_rect = value

    def draw(self, surface):
        self.fill(self.background)
        for inv in self.inventories:
            inv.draw(self)
        surface.blit(self, self.rect)

    def set_block(self, block_obj):
        super(FurnaceUI, self).set_block(block_obj)
        self.input_inventory_ui.inventory = block_obj.input_cell
        self.fuel_inventory_ui.inventory = block_obj.fuel_cell
        self.result_inventory_ui.inventory = block_obj.result_cell

    def pg_event(self, event: pg.event.Event):
        res = False
        for inv in self.inventories:
            res = inv.pg_event(event) or res
        return res


class InventoryPlayerWithBlockUI(SurfaceUI):
    def __init__(self, player_inventory, block_ui: BlockUI):
        super(InventoryPlayerWithBlockUI, self).__init__(((0, 0), WSIZE))
        self.player_inventory_ui = InventoryPlayerUI(player_inventory)
        self.player_inventory_ui.opened_full_inventory = True
        self.player_inventory_ui.table_inventory.rect.y = 100

        self.block_ui = block_ui
        self.block_ui.get_draw_rect().y = self.player_inventory_ui.table_inventory.rect.bottom + 40
        self.block_ui.get_draw_rect().centerx = self.player_inventory_ui.table_inventory.rect.centerx

        self.work_rect = pg.Rect.union(self.block_ui.work_rect, self.player_inventory_ui.work_rect)
        self.block_ui.set_work_rect(self.work_rect)
        self.player_inventory_ui.set_work_rect(self.work_rect)
        set_obj_mouse(None)
        self.opened = False

    def set_block(self, block_obj, view=True):
        self.block_ui.set_block(block_obj)
        if view:
            self.player_inventory_ui.opened_full_inventory = True
            self.opened = True

    def draw(self, surface):
        self.block_ui.draw(surface)
        self.player_inventory_ui.draw(surface)
        if get_obj_mouse():
            mx, my = pg.mouse.get_pos()
            self.blit(get_obj_mouse().sprite, (mx, my))
        self.opened = self.player_inventory_ui.opened_full_inventory

    def pg_event(self, event: pg.event.Event):
        res = self.player_inventory_ui.pg_event(event)
        res = self.block_ui.pg_event(event) or res
        return res


class InventoryPlayerChestUI(InventoryPlayerWithBlockUI):
    def __init__(self, player_inventory):
        super(InventoryPlayerChestUI, self).__init__(player_inventory, ChestUI())


class InventoryPlayerFurnaceUI(InventoryPlayerWithBlockUI):
    def __init__(self, player_inventory):
        super(InventoryPlayerFurnaceUI, self).__init__(player_inventory, FurnaceUI())


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
        if config.GameSettings.view_item_index:
            name += f" #{out[0]}"

        name_surface = textfont.render(name, True, text_color_light)
        span = textfont.get_height()
        self.info_index_surface = pygame.Surface(
            (max(140, name_surface.get_width() + 6), span * (len(recipe) + 3) + 3),
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
        self.info_index_surface.blit(textfont.render("-" * 50, True, text_color_light), (0, ty))

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
        if config.GameSettings.view_item_index:
            name += f" #{ttile}"
        name_surface = textfont.render(name, True, text_color_light)
        self.info_index_surface = pygame.Surface(
            (name_surface.get_width() + 6, textfont.get_height() + 3),
            pygame.SRCALPHA,
            32)
        self.info_index_surface.fill(bg_color)
        self.info_index_surface.blit(name_surface, (3, 3))

    def redraw(self):
        self.scroll_surface.fill(color_none)
        x, y = 0, 0
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
