from units.Achievements import achievements
from units.UI.Button import createImagesButton, createVSteckButtons, Button, createVSteckTextButtons, \
    ChangeTextButton, TextButton, KeyboardNav
from units.UI.ClassUI import *
from units.UI.InventoryUI import *
from units.UI.ColorsUI import *
from units.UI.FontsUI import *
from units.UI.Translate import get_translated_text, get_translated_lst_text, get_translated_text_to_lang

from units.Graphics.Texture import WHITE
from units.Tiles import live_imgs, bg_live_img, goldlive_imgs, bg_livecreative_img, \
    title_background, title_text, title_background_layer_2

from units.Graphics.outline import add_outline_to_image
from units.sound import set_category_volume

ru_bool_lst = ["On", "Off"]
eng_bool_lst = [True, False]
bool_dict = {ru_bool_lst[0]: eng_bool_lst[0], ru_bool_lst[1]: eng_bool_lst[1]}


class SysMessege:
    # полупрозрачное всплывающие  сообщение внизу экрана
    bg = (82, 82, 91, 220)
    rect = pg.Rect((WSIZE[0] - 330, WSIZE[1] - 45), (300, 32))
    width = 300
    height = 35

    def __init__(self, align="bottom_right"):
        self.align = align
        self.surface = pg.Surface(self.rect.size).convert_alpha()
        self.left_tact = 0
        self.count_tact = 0
        self.update_rect()

    def update_rect(self):
        if self.align == "bottom_right":
            self.rect = pg.Rect((WSIZE[0] - self.width - 30, WSIZE[1] - self.height - 20), (self.width, self.height))
        if self.align == "bottom_center":
            self.rect = pg.Rect(((WSIZE[0] - self.width) // 2, WSIZE[1] - self.height - 20), (self.width, self.height))
        self.surface = pg.Surface(self.rect.size).convert_alpha()

    def new(self, text, count_tact=FPS * 3):
        tr_text = get_translated_text(text)
        text_msg = textfont_sys_msg.render(tr_text, True, "#FDE047")
        self.width = max(300, text_msg.get_width() + 20)
        self.update_rect()

        self.left_tact = count_tact
        self.count_tact = count_tact
        self.surface.set_alpha(255)
        self.surface.fill(self.bg)
        self.surface.blit(text_msg, (10, 5))

    def send_reload_game_for_change(self):
        text = get_translated_text_to_lang("Перезапустите игру для применения изменений", config.GameSettings.language)
        self.new(text)

    def clear(self):
        self.left_tact = 0
        self.count_tact = 0

    def draw(self, surface):
        if self.left_tact > 0:
            self.left_tact -= 1
            if self.left_tact < 32:
                self.surface.set_alpha(self.left_tact * 8)
            elif (self.count_tact - self.left_tact) < 8:
                self.surface.set_alpha((self.count_tact - self.left_tact) * 32)

            surface.blit(self.surface, self.rect)

    def update(self):
        pass

    def pg_event(self, event):
        pass


class AchievementMessege(SysMessege):
    # все тоже самое что и SysMessege но для ачивок
    rect = pg.Rect((WSIZE[0] - 330, WSIZE[1] - 75), (300, 62))
    font_title = pygame.font.SysFont("Fenix", 28, )  # yes rus
    font_text = pygame.font.SysFont("Fenix", 24, )  # yes rus
    height = 62

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
    # UI для отрисовки во время процесса игры
    def __init__(self, scene) -> None:
        super().__init__(scene)
        self.info_surface = SurfaceUI((0, 0, 250, 100)).convert_alpha()
        self.sys_message = SysMessege()
        self.achievement_message = AchievementMessege()
        # self.playerui = SurfaceAlphaUI((0, 0, 280, 120))
        self.playerui = SurfaceUI((0, 0, 450, 420)).convert_alpha()
        self.playerui.rect.bottom = self.rect.bottom
        self._playerui_state = None  # (lives, max_lives, creative) последней отрисовки
        self.new_sys_message("Привет игрок. Нажми [E]")

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
            f" fps: {int(true_fps)}     {self.scene.elapsed_time}", True, "white")
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
        state = (self.scene.player.lives, self.scene.player.max_lives, self.scene.player.creative_mode)
        if state == self._playerui_state:
            return
        self._playerui_state = state
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
    # заставка игры
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
        self.sys_message = SysMessege(align="bottom_center")
        self.objects = GroupUI([])

        print(self.scene, self)

        self.bg_x, self.bg_y = 0, 0
        self.bg2_x, self.bg2_y = 0, 0

        btns = [
            ("Играть", lambda _: self.scene.open_worlds()),
            ("Новый мир", lambda _: self.scene.new_game()),
            ("Настройки", lambda _: self.scene.set_ui(self.scene.settings_ui)),
            ("Справка", lambda _: self.scene.set_scene(self.scene.app.help_scene)),
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
        self.keynav = KeyboardNav(obj_btns)
        _font_dev_btn = pygame.font.Font(MAIN_FONT_PATH, 23, )
        dev_but = Button(lambda _: self.scene.open_developers(),
                         (self.rect.w - 200, self.rect.h - 60, 175, 35),
                         *createImagesButton((175, 35), "Разработчики", font=_font_dev_btn))
        self.objects.add(dev_but)
        lang_but = ChangeTextButton(self.change_lang,
                                    (25, self.rect.h - 60, 175, 35),
                                    "Language: {}", states_text_lst=config.GameSettings.all_languages,
                                    start_state_text=config.GameSettings.language,
                                    font=_font_dev_btn)
        self.objects.add(lang_but)

        self.tts = title_text_surf = SurfaceUI(((0, 0), self.game_title_text.get_size()))
        title_text_surf.blit(self.game_title_text, (0, 0))
        title_text_surf.set_colorkey(self.color_sky)
        title_text_surf.rect.centerx = self.rect.centerx
        title_text_surf.rect.top = center_pos_2lens(title_text_surf.rect.h, self.rect.h) - 220
        self.tts_scale = 1.05
        self.tts_speed = 0.005
        self.tts_size = self.tts.rect.size
        self._tts_drawn_scale = None  # масштаб последней отрисовки заголовка
        self.objects.add(title_text_surf)
        self.objects.add(self.sys_message)
        print("objects", self.objects.components)

    def draw_background(self):
        self.screen.fill(self.color_sky)
        x, y = pg.mouse.get_pos()
        x, y = self.rect.w - x, self.rect.h - y
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
        if self._tts_drawn_scale != self.tts_scale:
            # масштабируем заголовок только пока анимация реально идёт
            self._tts_drawn_scale = self.tts_scale
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
        if self.keynav.pg_event(event):
            return True
        self.objects.pg_event(event)

    def change_lang(self, button, lang):
        config.GameSettings.set_language(lang)
        self.sys_message.send_reload_game_for_change()


fps_values_lst = [30, 60, 120]


class MainSettingsUI(TitleUI):
    # меню с основными настройками
    window_sizes_lst = ["1240,720", "1054,612", "720,480"]

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
        self.keynav = KeyboardNav(obj_btns)

        self.tts = title_text_surf = SurfaceUI(((0, 0), self.game_title_text.get_size()))
        title_text_surf.blit(self.game_title_text, (0, 0))
        title_text_surf.set_colorkey(self.color_sky)
        title_text_surf.rect.topleft = center_pos_2lens(title_text_surf.rect.w, self.rect.w), \
            center_pos_2lens(title_text_surf.rect.h, self.rect.h) - 220
        self.tts_y = title_text_surf.rect.top

        self.objects.add(title_text_surf)
        self.objects.add(self.sys_message)

    def get_pre_buttons(self, btn_rect):
        if config.Window.size in self.window_sizes_lst:
            size_start_state_index = self.window_sizes_lst.index(config.Window.size)
        else:
            self.window_sizes_lst.append(config.Window.size)
            size_start_state_index = len(self.window_sizes_lst) - 1

        btns = [
            ChangeTextButton(self.set_window_size, btn_rect, "Размер: ({})",
                             states_text_lst=self.window_sizes_lst, start_state_index=size_start_state_index),
            ChangeTextButton(self.set_fullscreen, btn_rect,
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
            ChangeTextButton(self.set_max_fps, btn_rect,
                             "Лимит FPS: {}", states_text_lst=fps_values_lst,
                             start_state_index=fps_values_lst.index(config.GameSettings.max_fps)
                             if config.GameSettings.max_fps in fps_values_lst else 1),
            ("Звуки и музыка...", lambda _: self.scene.set_ui(self.scene.sound_settings_ui)),
            ("Создать мир обучения", lambda _: self.scene.create_tutorial_world()),
            ("В главное меню", lambda _: self.scene.set_ui(self.scene.title_ui)),

        ]
        return btns

    def set_window_size(self, button, size):
        config.Window.set_size(size)
        self.sys_message.send_reload_game_for_change()

    def set_fullscreen(self, button, state):
        config.Window.set_fullscreen(state)
        # с флагом SCALED фуллскрин можно переключать на лету, без перезапуска
        want = bool(bool_dict.get(state, state))
        try:
            if pg.display.is_fullscreen() != want:
                pg.display.toggle_fullscreen()
        except Exception:
            self.sys_message.send_reload_game_for_change()

    def set_max_fps(self, button, state):
        config.GameSettings.set_max_fps(state)
        self.sys_message.send_reload_game_for_change()


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
            ChangeTextButton(lambda _, state: set_category_volume("background", state / 100), btn_rect, "Музыка {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=self._volume_index(config.VolumeSettings.background_volume)),
            ChangeTextButton(lambda _, state: set_category_volume("game", state / 100), btn_rect, "Звуки игры {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=self._volume_index(config.VolumeSettings.game_volume)),
            ChangeTextButton(lambda _, state: set_category_volume("player", state / 100), btn_rect, "Игрок {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=self._volume_index(config.VolumeSettings.player_volume)),
            ChangeTextButton(lambda _, state: set_category_volume("creatures", state / 100), btn_rect, "Существа {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=self._volume_index(config.VolumeSettings.creatures_volume)),
            ChangeTextButton(lambda _, state: set_category_volume("ui", state / 100), btn_rect, "Интерфейс {}%",
                             states_text_lst=volume_values_lst,
                             start_state_index=self._volume_index(config.VolumeSettings.ui_volume)),
            ("Назад", lambda _: self.scene.set_ui(self.scene.settings_ui)),

        ]
        return btns

    @staticmethod
    def _volume_index(volume):
        """Индекс ближайшего значения громкости (устойчиво к произвольным числам в конфиге)."""
        value = volume * 100
        return min(range(len(volume_values_lst)), key=lambda i: abs(volume_values_lst[i] - value))


class WorldListUI(UI):
    """Экран «Мои миры»: карточка на мир (имя, дата, наигранное время),
    клик — играть, крестик — удалить (с подтверждением)."""
    bg = (82, 82, 91, 240)
    row_h = 40
    row_step = 62  # высота карточки с подписью
    font_sub = pygame.font.Font(MAIN_FONT_PATH, 16)

    def __init__(self, scene) -> None:
        super().__init__(scene)
        w, h = 460, 520
        self.rect = pg.Rect(0, 0, w, h)
        self.rect.center = WSIZE[0] // 2, WSIZE[1] // 2
        self.surface = pg.Surface(self.rect.size).convert_alpha()

        self.title_surf = pg.Surface((w, 40)).convert_alpha()
        self.title_surf.fill((82, 82, 91))
        self.title_surf.blit(textfont_btn.render(get_translated_text("Мои миры"), True, WHITE), (10, 5))

        self.list_top = 55
        self.scroll_y = 0
        self.worlds = []
        self.btns = []
        self.subtitles = []
        self.confirm_delete_id = None
        self.reload_worlds()

    def reload_worlds(self):
        from units.Map import WorldStorage
        self.worlds = WorldStorage.list_worlds()
        self.scroll_y = 0
        self.confirm_delete_id = None
        self._build()

    def _build(self):
        from units.Map import WorldStorage
        self.btns = []
        self.subtitles = []  # (y, отрендеренный текст)
        x = 20
        y = self.list_top + self.scroll_y
        w = self.rect.w - 40
        # кнопка нового мира
        self.btns.append(TextButton(lambda _: self.scene.new_world(),
                                    (x, y, w, self.row_h - 5), "+ Новый мир",
                                    screenXY=(self.rect.x + x, self.rect.y + y)))
        y += self.row_h + 10
        for meta in self.worlds:
            wid = meta["id"]
            name = meta.get("name", wid)
            self.btns.append(TextButton(lambda _, wid=wid: self.scene.play_world(wid),
                                        (x, y, w - 45, self.row_h), name,
                                        screenXY=(self.rect.x + x, self.rect.y + y)))
            del_text = "Точно?" if self.confirm_delete_id == wid else "X"
            self.btns.append(TextButton(lambda _, wid=wid: self.delete_world(wid),
                                        (x + w - 40, y, 40, self.row_h), del_text,
                                        screenXY=(self.rect.x + x + w - 40, self.rect.y + y)))
            sub = f"{WorldStorage.format_last_played(meta.get('last_played'))}  •  " \
                  f"{WorldStorage.format_playtime(meta.get('playtime'))}"
            if meta.get("tutorial"):
                sub = get_translated_text("обучение") + "  •  " + sub
            self.subtitles.append((y + self.row_h + 2, self.font_sub.render(sub, True, "#D4D4D8")))
            y += self.row_step

    def delete_world(self, wid):
        from units.Map import WorldStorage
        if self.confirm_delete_id == wid:
            WorldStorage.delete_world(wid)
            self.reload_worlds()
        else:
            # первый клик — просим подтвердить
            self.confirm_delete_id = wid
            self._build()

    def scroll(self, dy):
        # ограничение прокрутки: контент не выше первого и не ниже последнего
        content_h = self.row_h + 10 + self.row_step * len(self.worlds)
        min_scroll = min(0, self.rect.h - self.list_top - content_h - 15)
        self.scroll_y = max(min_scroll, min(0, self.scroll_y + dy))
        self._build()

    def pg_event(self, event: pg.event.Event) -> Union[bool, None]:
        if event.type == pg.MOUSEWHEEL:
            self.scroll(event.y * 40)
            return
        if event.type == pg.MOUSEBUTTONDOWN:
            if not self.rect.collidepoint(event.pos):
                return
        for btn in self.btns:
            btn.pg_event(event)

    def draw(self):
        self.screen.fill((39, 39, 42))
        self.surface.fill(self.bg)

        for btn in self.btns:
            if self.list_top - self.row_h < btn.rect.y < self.rect.h:
                btn.draw(self.surface)
        for y, sub in self.subtitles:
            if self.list_top < y < self.rect.h:
                self.surface.blit(sub, (28, y))
        self.surface.blit(self.title_surf, (0, 0))

        self.screen.blit(self.surface, self.rect)

        pygame.display.flip()


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


class PauseUI(UI):
    def __init__(self, scene):
        super(PauseUI, self).__init__(scene)
        self.rect = pg.Rect((0, 0, 370, 350))
        w, h = self.screen.get_size()
        self.rect.center = w // 2, h // 2
        self.surface = pg.Surface(self.rect.size).convert_alpha()
        self.surface.fill((82, 82, 91, 150))

        text = textfont_btn.render(
            get_translated_text(f"Пауза"), True, "white")
        t_w, t_h = text.get_size()
        self.surface.blit(text, (10, 10))
        # end surf
        # init btns
        btn_size = 350, 35
        btn_pos = center_pos_2lens(btn_size[0], self.rect.w), t_h + 10 + 10
        btn_rect = pg.Rect(btn_pos, btn_size)

        btns = [
            ("Продолжить", lambda _: self.scene.resume()),
            ("Сохранить", lambda _: self.scene.save_world()),
            ("Достижения", lambda _: self.scene.set_scene(self.scene.app.achievements_scene)),
            ("Как играть", lambda _: self.scene.set_scene(self.scene.app.help_scene)),
            ("Телепорт домой", lambda _: self.scene.tp_to_home()),
            ("Сохранить и выйти в меню", lambda _: self.scene.save_and_to_main_menu()),
        ]

        self.img_btns = [createImagesButton(btn_rect.size, t, font=textfont_btn)
                         for t, f in btns]
        funcs = [f for t, f in btns]

        self.btns = createVSteckButtons(btn_rect.size, btn_rect.centerx, btn_rect.top, 15, self.img_btns, funcs,
                                        screen_position=(self.rect.x,
                                                         self.rect.y))  # кнопки открывающие карты
        self.keynav = KeyboardNav(self.btns)

    def draw(self):
        self.screen.blit(self.display, (0, 0))
        surface = self.surface.copy()
        for btn in self.btns:
            btn.draw(surface)

        self.screen.blit(surface, self.rect)
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        if self.keynav.pg_event(event):
            return True
        for btn in self.btns:
            btn.pg_event(event)


class AchievementsUI(UI):
    bg = (82, 82, 91, 150)
    font_title = pygame.font.Font(CWDIR+'data/fonts/xenoa.ttf', 28, )
    font_text = pygame.font.Font(CWDIR+'data/fonts/xenoa.ttf', 21, )
    font_action = pygame.font.Font(CWDIR+'data/fonts/xenoa.ttf', 14, )

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
        key = tuple(achievs.completed)
        if key == getattr(self, "_ach_key", None):
            return
        self._ach_key = key
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
        title = textfont_btn.render(get_translated_text("Достижения"), True, "#FFFFFF")
        self.surface.blit(title, (10, 10))

        self.surface.blit(self.surface_achievements, (0, 35))

        self.screen.blit(self.surface, self.rect)
        pg.display.flip()


class HelpUI(UI):
    """Экран «Как играть»: секции управления с клавишами-чипами,
    прокрутка колесом/стрелками, Esc — закрыть."""
    bg_screen = (24, 24, 27)
    panel_bg = (39, 39, 42)
    section_color = "#FDE047"
    text_color = "#FFFFFF"
    lore_color = "#A1A1AA"
    chip_bg = (63, 63, 70)
    chip_border = (161, 161, 170)
    font_title = pygame.font.Font(MAIN_FONT_PATH, 32)
    font_section = pygame.font.Font(MAIN_FONT_PATH, 24)
    font_text = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 17)
    font_chip = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 15)
    font_hint = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 14)

    def __init__(self, scene):
        super(HelpUI, self).__init__(scene)
        from units.UI.HelpData import HELP_SECTIONS, LORE, LORE_TITLE
        w = min(680, WSIZE[0] - 40)
        h = min(600, WSIZE[1] - 40)
        self.rect = pg.Rect(0, 0, w, h)
        self.rect.center = WSIZE[0] // 2, WSIZE[1] // 2

        self.header_h = 52
        self.footer_h = 30
        self.scroll_y = 0
        self.content = self._render_content(HELP_SECTIONS, LORE_TITLE, LORE, w - 40)
        self.view_h = h - self.header_h - self.footer_h
        self.max_scroll = max(0, self.content.get_height() - self.view_h)

        self.title_surf = self.font_title.render(get_translated_text("Как играть"), True, self.section_color)
        self.hint_surf = self.font_hint.render(
            get_translated_text("Esc — закрыть   •   колесо / стрелки — прокрутка"), True, self.lore_color)

    # ---------- отрисовка контента ----------

    def _chip(self, text):
        """Клавиша-чип: скруглённый прямоугольник с подписью."""
        t = self.font_chip.render(text, True, self.text_color)
        chip = pg.Surface((t.get_width() + 16, 26)).convert_alpha()
        chip.fill((0, 0, 0, 0))
        r = chip.get_rect()
        pg.draw.rect(chip, self.chip_bg, r, border_radius=6)
        pg.draw.rect(chip, self.chip_border, r, width=1, border_radius=6)
        chip.blit(t, ((r.w - t.get_width()) // 2, (r.h - t.get_height()) // 2 - 1))
        return chip

    def _wrap(self, text, font, max_w):
        lines, line = [], ""
        for word in text.split():
            probe = (line + " " + word).strip()
            if font.size(probe)[0] <= max_w:
                line = probe
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def _render_content(self, sections, lore_title, lore, w):
        surf = pg.Surface((w, 4000)).convert_alpha()
        surf.fill((0, 0, 0, 0))
        x_desc = 220  # колонка описаний
        y = 6
        plus = self.font_chip.render("+", True, self.lore_color)
        for title, rows in sections:
            head = self.font_section.render(get_translated_text(title), True, self.section_color)
            surf.blit(head, (0, y))
            y += head.get_height() + 2
            pg.draw.line(surf, self.section_color, (0, y), (w, y))
            y += 10
            for keys, desc in rows:
                x = 8
                row_top = y
                for k_i, key in enumerate(keys):
                    if k_i:
                        surf.blit(plus, (x, row_top + 4))
                        x += plus.get_width() + 4
                    chip = self._chip(get_translated_text(key))
                    surf.blit(chip, (x, row_top))
                    x += chip.get_width() + 4
                lines = self._wrap(get_translated_text(desc), self.font_text, w - x_desc - 8)
                ty = row_top + (26 - self.font_text.get_height()) // 2 if len(lines) == 1 else row_top + 2
                for line in lines:
                    surf.blit(self.font_text.render(line, True, self.text_color), (x_desc, ty))
                    ty += self.font_text.get_height() + 2
                y = max(row_top + 26, ty) + 8
            y += 12
        # история мира
        head = self.font_section.render(get_translated_text(lore_title), True, self.section_color)
        surf.blit(head, (0, y))
        y += head.get_height() + 2
        pg.draw.line(surf, self.section_color, (0, y), (w, y))
        y += 10
        for line in self._wrap(get_translated_text(lore), self.font_text, w - 16):
            surf.blit(self.font_text.render(line, True, self.lore_color), (8, y))
            y += self.font_text.get_height() + 4
        return surf.subsurface((0, 0, w, min(y + 6, surf.get_height()))).copy()

    # ---------- события/отрисовка ----------

    def scroll(self, dy):
        self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - dy))

    def pg_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEWHEEL:
            self.scroll(event.y * 40)
        elif event.type == pg.KEYDOWN:
            if event.key in (pg.K_DOWN, pg.K_s):
                self.scroll(-40)
            elif event.key in (pg.K_UP, pg.K_w):
                self.scroll(40)
            elif event.key == pg.K_PAGEDOWN:
                self.scroll(-self.view_h)
            elif event.key == pg.K_PAGEUP:
                self.scroll(self.view_h)

    def draw(self):
        self.screen.fill(self.bg_screen)
        panel = pg.Surface(self.rect.size).convert_alpha()
        panel.fill(self.panel_bg)
        panel.blit(self.title_surf, (20, 8))
        panel.blit(self.content, (20, self.header_h),
                   (0, self.scroll_y, self.content.get_width(), self.view_h))
        # полоса прокрутки
        if self.max_scroll:
            track_h = self.view_h
            thumb_h = max(30, int(track_h * self.view_h / self.content.get_height()))
            thumb_y = self.header_h + int((track_h - thumb_h) * self.scroll_y / self.max_scroll)
            pg.draw.rect(panel, (63, 63, 70), (self.rect.w - 10, self.header_h, 4, track_h), border_radius=2)
            pg.draw.rect(panel, (161, 161, 170), (self.rect.w - 10, thumb_y, 4, thumb_h), border_radius=2)
        panel.blit(self.hint_surf, (20, self.rect.h - self.footer_h + 4))
        self.screen.blit(panel, self.rect)
        pg.display.flip()
