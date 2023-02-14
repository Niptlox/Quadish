from units.Achievements import achievements
from units.UI.Button import createImagesButton, createVSteckButtons, Button, createVSteckTextButtons, ChangeTextButton
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
    def __init__(self, scene) -> None:
        super().__init__(scene)
        self.info_surface = SurfaceUI((0, 0, 250, 100)).convert_alpha()
        self.sys_message = SysMessege()
        self.achievement_message = AchievementMessege()
        # self.playerui = SurfaceAlphaUI((0, 0, 280, 120))
        self.playerui = SurfaceUI((0, 0, 450, 420)).convert_alpha()
        self.playerui.rect.bottom = self.rect.bottom
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
        self.sys_message = SysMessege(align="bottom_center")
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
        self.objects.add(title_text_surf)
        self.objects.add(self.sys_message)
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

    def change_lang(self, button, lang):
        config.GameSettings.set_language(lang)
        self.sys_message.send_reload_game_for_change()


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
            ("Звуки и музыка...", lambda _: self.scene.set_ui(self.scene.sound_settings_ui)),
            ("В главное меню", lambda _: self.scene.set_ui(self.scene.title_ui)),

        ]
        return btns

    def set_window_size(self, button, size):
        config.Window.set_size(size)
        self.sys_message.send_reload_game_for_change()

    def set_fullscreen(self, button, state):
        config.Window.set_fullscreen(state)
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
        self.title = get_translated_text(title)
        super().__init__(scene)
        w, h = 300, 500
        self.rect = pg.Rect(0, 0, w, h)
        self.rect.center = WSIZE[0] // 2, WSIZE[1] // 2
        self.surface = pg.Surface(self.rect.size).convert_alpha()

        self.title_surf = pg.Surface((w, 40)).convert_alpha()
        self.title_surf.fill((82, 82, 91))
        self.title_surf.blit(textfont_btn.render(self.title, True, WHITE), (10, 5))

        btn_rect = pg.Rect(0, 20 + 40, 200, 35)
        self.btns_scroll = [(w - btn_rect.w) // 2 - 15, btn_rect.y]
        self.btns_scroll_step = 20 + btn_rect.height

        n = self.scene.game.game_map.save_slots
        tr_text = get_translated_text("Мир")
        imgs = [createImagesButton(btn_rect.size, tr_text+f" #{i}", font=textfont_btn)
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
        self.surface.blit(self.title_surf, (0, -5))

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
            ("Сохранить мир", lambda _: self.scene.set_scene(self.scene.app.savem_scene)),
            ("Открыть мир", lambda _: self.scene.set_scene(self.scene.app.openm_scene)),
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
        title = textfont_btn.render(get_translated_text("Достижения"), True, "#FFFFFF")
        self.surface.blit(title, (10, 10))

        self.surface.blit(self.surface_achievements, (0, 35))

        self.screen.blit(self.surface, self.rect)
        pg.display.flip()
