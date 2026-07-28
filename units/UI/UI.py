from units.Achievements import achievements
from units.UI.Button import createImagesButton, createVSteckButtons, Button, \
    ChangeTextButton, TextButton, KeyboardNav
from units.UI.ClassUI import *
from units.UI.InventoryUI import *
from units.UI.ColorsUI import *
from units.UI.FontsUI import *
from units.UI.Translate import get_translated_text, get_translated_text_to_lang

from units.Graphics.Texture import WHITE
from units.Tiles import live_imgs, bg_live_img, goldlive_imgs, bg_livecreative_img, \
    title_background, title_text, title_background_layer_2

from units.Graphics.outline import add_outline_to_image
from units.sound import set_category_volume
from units.Updater import UpdateChecker

ru_bool_lst = ["On", "Off"]
eng_bool_lst = [True, False]
bool_dict = {ru_bool_lst[0]: eng_bool_lst[0], ru_bool_lst[1]: eng_bool_lst[1]}


class SysMessege:
    # полупрозрачное всплывающие  сообщение внизу экрана (рисуется на реальном
    # экране SCREEN_SIZE, а не в уменьшенном мире — поэтому текст не мылится)
    bg = (82, 82, 91, 220)
    rect = pg.Rect((SCREEN_SIZE[0] - 330, SCREEN_SIZE[1] - 45), (300, 32))
    width = 300
    height = 35

    def __init__(self, align="bottom_right"):
        self.align = align
        self.bottom_offset = 0  # приподнять над низом (чтобы не накладываться)
        self.surface = pg.Surface(self.rect.size).convert_alpha()
        self.left_tact = 0
        self.count_tact = 0
        self.update_rect()

    def update_rect(self):
        off = 20 + self.bottom_offset
        sw, sh = SCREEN_SIZE
        if self.align == "bottom_right":
            self.rect = pg.Rect((sw - self.width - 30, sh - self.height - off), (self.width, self.height))
        if self.align == "bottom_center":
            self.rect = pg.Rect(((sw - self.width) // 2, sh - self.height - off), (self.width, self.height))
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
    rect = pg.Rect((SCREEN_SIZE[0] - 330, SCREEN_SIZE[1] - 75), (300, 62))
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
        # ачивка встаёт над строкой сообщений/подсказок, а не поверх неё
        self.achievement_message.bottom_offset = self.sys_message.height + 18
        self.achievement_message.update_rect()
        # self.playerui = SurfaceAlphaUI((0, 0, 280, 120))
        self.playerui = SurfaceUI((0, 0, 450, 420)).convert_alpha()
        self.playerui.rect.bottom = self.screen.get_height()
        self._playerui_state = None  # (lives, max_lives, creative) последней отрисовки
        self.new_sys_message("Привет игрок. Нажми [E]")

    def relayout(self):
        """Пересчитать HUD и вложенные интерфейсы под новый размер окна.

        Сюда же приходят инвентарь игрока и интерфейсы блоков: их раскладка
        считалась один раз при создании по SCREEN_SIZE, поэтому после
        растягивания окна они оставались в старом центре, а вместе с ними
        разъезжались координаты ячеек — клики попадали не туда."""
        super().relayout()
        self.sys_message.update_rect()
        self.achievement_message.bottom_offset = self.sys_message.height + 18
        self.achievement_message.update_rect()
        self.playerui.rect.bottom = self.screen.get_height()
        self._playerui_state = None  # заставить перерисовать полоску жизней

        scene = self.scene
        inventory_ui = getattr(getattr(scene, "player", None), "inventory", None)
        inventory_ui = getattr(inventory_ui, "ui", None)
        if inventory_ui is not None and hasattr(inventory_ui, "relayout"):
            inventory_ui.relayout()
        manager = getattr(scene, "blocks_ui_manager", None)
        if manager is not None:
            for block_ui in manager.blocks_ui.values():
                if hasattr(block_ui, "relayout"):
                    block_ui.relayout()

    def blit_world(self):
        """Растянуть отрендеренный мир (self.display, может быть меньше экрана)
        на реальный экран. Единственное место, где мир масштабируется — весь
        остальной HUD/UI рисуется прямо на self.screen и не размывается."""
        if self.display.get_size() == self.screen.get_size():
            self.screen.blit(self.display, (0, 0))
        else:
            pygame.transform.scale(self.display, self.screen.get_size(), self.screen)

    def draw(self):
        # HUD рисуется прямо на экран (self.screen), в его настоящем
        # разрешении — поэтому текст всегда чёткий, даже если мир (self.display)
        # рендерится в уменьшенном логическом размере.
        sw, sh = self.screen.get_size()
        if show_info_menu:
            self.screen.blit(self.info_surface, (sw - 250, 0))

        self.sys_message.draw(self.screen)
        self.achievement_message.draw(self.screen)
        self.draw_goal()
        self.redraw_playerui()
        self.playerui.draw(self.screen)

    # Текущая цель — одна строка в углу. Не окно и не подсказка с кнопкой:
    # песочнице нужен ответ на «а что делать?», а не сопровождающий.
    goal_font = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 16)

    def draw_goal(self):
        if not config.GameSettings.show_goal:
            return
        from units.Story import current_goal
        goal = current_goal(self.scene)
        if not goal:
            return
        if goal != getattr(self, "_goal_text", None):
            self._goal_text = goal
            surf = self.goal_font.render(goal, True, (228, 228, 231))
            shadow = self.goal_font.render(goal, True, (12, 12, 16))
            box = pygame.Surface((surf.get_width() + 14, surf.get_height() + 8),
                                 pygame.SRCALPHA, 32)
            box.fill((24, 24, 27, 140))
            box.blit(shadow, (8, 5))
            box.blit(surf, (7, 4))
            self._goal_surface = box
        self.screen.blit(self._goal_surface, (10, 10))

    def flip(self):
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
    raw_background = title_background
    raw_background_layer_2 = title_background_layer_2
    game_title_text = title_text
    step_objects = 15

    def __init__(self, scn):
        super(TitleUI, self).__init__(scn)
        # титульный экран/настройки рисуются прямо на self.screen (реальном
        # экране), а не на self.display (уменьшенный мир WSIZE) — базовый
        # self.rect унаследован бы от WSIZE и на широких экранах вся
        # раскладка ужалась бы в угол настоящего окна.
        self.rect = pg.Rect((0, 0), self.screen.get_size())
        # фон параллакса пересчитываем под текущий размер экрана (не как
        # атрибут класса единожды при импорте) — иначе после живого
        # растягивания окна по краям появлялись бы пустые полосы.
        self.background = pg.transform.scale(
            self.raw_background, (int(self.rect.w * 1.5), int(self.rect.h * 1.5)))
        self.background_layer_2 = pg.transform.scale(self.raw_background_layer_2, self.background.get_size())
        self.background.set_colorkey(self.color_sky)
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

        btn_size = int(250 * UI_SCALE), int(35 * UI_SCALE)
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

        # Проверка обновлений. Релизы публикуются автоматически по тегу, но
        # игрок об этом не узнавал: скачал сборку один раз — и остался на
        # ней. Сеть трогается только в фоновом потоке (units/Updater.py),
        # поэтому без интернета экран ведёт себя ровно как раньше.
        self.updater = UpdateChecker(GAME_VERSION)
        self._updater_state = None
        self.update_but = TextButton(lambda _: self.on_update_button(),
                                     (self.rect.w - 200, self.rect.h - 105, 175, 35),
                                     "Обновление", font=_font_dev_btn)
        self.objects.add(self.update_but)

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

    def on_update_button(self):
        """Одна кнопка на весь сценарий: сначала «проверить», потом
        «скачать». Отдельная кнопка загрузки простаивала бы почти всегда."""
        if self.updater.state == self.updater.AVAILABLE and self.updater.asset:
            self.updater.download_async()
        elif not self.updater.busy():
            self.updater.check_async()

    def poll_updater(self):
        """Показать смену состояния фоновой проверки. Сообщение шлём только
        при переходе, иначе оно висело бы вечно, обновляясь каждый кадр."""
        u = self.updater
        if u.state == u.DOWNLOADING:
            self.update_but.set_text(f"Скачивание {int(u.progress * 100)}%")
            return
        if u.state == self._updater_state:
            return
        self._updater_state = u.state
        labels = {u.CHECKING: "Проверка…", u.AVAILABLE: "Скачать",
                  u.DOWNLOADED: "Скачано", u.UPTODATE: "Обновление",
                  u.ERROR: "Обновление", u.IDLE: "Обновление"}
        self.update_but.set_text(labels.get(u.state, "Обновление"))
        if u.message and u.state != u.CHECKING:
            self.sys_message.new(u.message, count_tact=FPS * 6)

    def draw(self):
        self.poll_updater()
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

    def relayout(self):
        # self.__init__ полиморфно резолвится в __init__ актуального
        # подкласса (MainSettingsUI/SoundSettingsUI) — полностью
        # пересобирает раскладку под новый self.screen.get_size().
        self.__init__(self.scene)


def make_screen_icon(h=22):
    """Иконка монитора — чтобы было ясно, что настройка привязана к экрану."""
    w = int(h * 1.3)
    s = pg.Surface((w, h)).convert_alpha()
    s.fill((0, 0, 0, 0))
    fg = (212, 212, 216)
    pg.draw.rect(s, fg, (0, 0, w, h - 5), border_radius=3, width=2)
    pg.draw.rect(s, fg, (2, 2, w - 4, h - 9))
    pg.draw.rect(s, fg, (w // 2 - 4, h - 5, 8, 2))
    pg.draw.rect(s, fg, (w // 2 - 8, h - 3, 16, 2), border_radius=1)
    return s


class Dropdown:
    """Выпадающий список для настроек: шапка с текущим значением, по клику
    раскрывается перечень вариантов. Координаты — экранные."""
    bg = (63, 63, 70)
    bg_open = (39, 39, 42)
    bg_hover = (82, 82, 91)
    border = (161, 161, 170)
    accent = "#FDE047"

    def __init__(self, rect, label, options, index, on_select, font, icon=None):
        self.rect = pg.Rect(rect)
        self.label = label            # "Размер: {}" или "Монитор"
        self.options = list(options)  # отображаемые строки
        self.index = max(0, min(index, len(self.options) - 1))
        self.on_select = on_select    # (value, index) -> None
        self.font = font
        self.icon = icon
        self.opened = False
        self.opt_h = self.rect.h

    def current_text(self):
        val = self.options[self.index] if self.options else ""
        return self.label.format(val) if "{}" in self.label else f"{self.label}: {val}"

    def _opt_rect(self, i):
        return pg.Rect(self.rect.x, self.rect.bottom + 2 + i * self.opt_h, self.rect.w, self.opt_h)

    def draw(self, surface):
        pg.draw.rect(surface, self.bg_open if self.opened else self.bg, self.rect, border_radius=5)
        pg.draw.rect(surface, self.border, self.rect, width=1, border_radius=5)
        t = self.font.render(self.current_text(), True, WHITE)
        surface.blit(t, (self.rect.x + (36 if self.icon else 12),
                         self.rect.centery - t.get_height() // 2))
        if self.icon:
            surface.blit(self.icon, (self.rect.x + 8, self.rect.centery - self.icon.get_height() // 2))
        # стрелка
        cx, cy = self.rect.right - 16, self.rect.centery
        d = 4 if not self.opened else -4
        pg.draw.polygon(surface, self.border,
                        [(cx - 5, cy - d // 2), (cx + 5, cy - d // 2), (cx, cy + d)])

    def draw_options(self, surface):
        if not self.opened:
            return
        mouse = pg.mouse.get_pos()
        for i, opt in enumerate(self.options):
            r = self._opt_rect(i)
            hover = r.collidepoint(mouse)
            pg.draw.rect(surface, self.bg_hover if hover else self.bg_open, r, border_radius=4)
            color = self.accent if i == self.index else WHITE
            t = self.font.render(str(opt), True, color)
            surface.blit(t, (r.x + 12, r.centery - t.get_height() // 2))

    def pg_event(self, event) -> bool:
        if event.type != pg.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.opened:
            for i in range(len(self.options)):
                if self._opt_rect(i).collidepoint(event.pos):
                    self.index = i
                    self.opened = False
                    self.on_select(self.options[i], i)
                    return True
            self.opened = False  # клик вне списка — закрыть
            return self.rect.collidepoint(event.pos)
        if self.rect.collidepoint(event.pos):
            self.opened = True
            return True
        return False


fps_values_lst = [30, 60, 120]
view_tiles_lst = [30, 40, 50, 60, 70]


menu_size_labels = ["Авто", "Крошечный", "Малый", "Средний", "Большой", "Огромный"]


def mods_label():
    """Подпись пункта модов: сразу показывает, сколько загрузилось и были
    ли ошибки — иначе о сломанном моде можно узнать только из консоли."""
    from units import mods
    if not config.ModSettings.enabled:
        return "Модификации: {}"
    if mods.MOD_ERRORS:
        return f"Модификации ({len(mods.MODS)}, ошибок: {len(mods.MOD_ERRORS)})" + ": {}"
    if mods.MODS:
        return f"Модификации ({len(mods.MODS)})" + ": {}"
    return "Модификации (нет): {}"


class MainSettingsUI(TitleUI):
    # меню с основными настройками
    header_title = "Настройки"
    font_item = pygame.font.Font(MAIN_FONT_PATH, int(20 * UI_SCALE))

    def __init__(self, scene):
        super(MainSettingsUI, self).__init__(scene)
        # логотип в настройках не показываем (self.tts от TitleUI остаётся,
        # но не добавлен в objects — draw_background его обновляет вхолостую)
        self.objects = GroupUI([])

        htxt = add_outline_to_image(textfont_btn.render(get_translated_text(self.header_title), True, WHITE),
                                    2, "#1C1917")
        self.header_surf = htxt
        self.header_pos = (self.rect.centerx - htxt.get_width() // 2, 20)

        items = self.get_settings_items()
        n = max(1, len(items))
        w, wh = int(460 * UI_SCALE), int(34 * UI_SCALE)
        top = self.header_pos[1] + htxt.get_height() + 14
        avail = max(wh, self.rect.h - top - 18)
        slot = min(wh + 10, max(wh + 3, avail // n))
        start_y = top + max(0, (avail - slot * n) // 2)
        x = self.rect.centerx - w // 2

        self.widgets, self.dropdowns, self.buttons = [], [], []
        y = start_y
        for spec in items:
            rect = (x, y, w, wh)
            if spec[0] == "dd":
                _, label, options, index, on_select, icon = spec
                dd = Dropdown(rect, get_translated_text(label), options, index,
                              on_select, self.font_item, icon)
                self.widgets.append(dd)
                self.dropdowns.append(dd)
            else:
                _, text, func = spec
                b = TextButton(func, rect, text, font=self.font_item)
                self.widgets.append(b)
                self.buttons.append(b)
            y += slot
        self.keynav = KeyboardNav(self.buttons)

    # ---------- элементы настроек ----------

    def get_settings_items(self):
        gs = config.GameSettings
        win = config.Window
        n_mon = max(1, len(pygame.display.get_desktop_sizes()))
        scr_icon = make_screen_icon()

        def set_mon(value, i):
            win.set_monitor(i)
            self.sys_message.send_reload_game_for_change()

        def set_fs(value, i):
            # живое переключение — apply_resize сам пересоздаёт окно
            # и обновляет SCREEN_SIZE, затем relayout() пересобирает меню
            apply_resize(fullscreen=(i == 1))
            self.scene._on_screen_changed()

        def set_menu_size(value, i):
            win.set_menu_size(MENU_SIZES[i])
            # шрифты грузятся один раз при старте под нативный UI_SCALE —
            # в отличие от режима экрана, тут без перезапуска не обойтись
            self.sys_message.send_reload_game_for_change()

        def set_fps(value, i):
            gs.set_max_fps(value)
            self.sys_message.send_reload_game_for_change()

        def set_view_tiles(value, i):
            win.set_view_tiles_width(value)
            self.sys_message.send_reload_game_for_change()

        def set_dump(value, i):
            gs.set_dynamic_dump(bool_dict[value])
            try:
                self.scene.app.game_scene.game_map.dynamic_dump = bool_dict[value]
            except Exception:
                pass

        def set_cursor_kind(value, i):
            from units.Graphics.Cursor import CURSOR_KINDS, apply_cursor_kind
            gs.set_cursor(CURSOR_KINDS[i])
            apply_cursor_kind()   # применяется сразу, перезапуск не нужен

        def set_mods(value, i):
            config.ModSettings.set_enabled(bool_dict[value])
            # блоки/существа модов регистрируются один раз при импорте
            # units.Tiles — включение/выключение требует перезапуска
            self.sys_message.send_reload_game_for_change()

        fps_idx = fps_values_lst.index(gs.max_fps) if gs.max_fps in fps_values_lst else 1
        view_tiles_idx = view_tiles_lst.index(win.view_tiles_width) if win.view_tiles_width in view_tiles_lst else 2
        menu_size_idx = MENU_SIZES.index(win.menu_size) if win.menu_size in MENU_SIZES else 0
        from units.Graphics.Cursor import CURSOR_KINDS, CURSOR_KIND_LABELS as cursor_kind_labels
        cursor_idx = CURSOR_KINDS.index(gs.cursor) if gs.cursor in CURSOR_KINDS else 0
        # В основном меню — только то, что игрок меняет чаще всего.
        # Раньше здесь лежали все 15 пунктов одним списком: он не влезал в
        # низкое окно, а нужное приходилось искать глазами.
        items = [
            ("dd", "Размер меню: {}", menu_size_labels, menu_size_idx, set_menu_size, None),
            ("dd", "Режим экрана: {}", ["Оконный", "Полноэкранный"], 1 if win.fullscreen else 0, set_fs, scr_icon),
            ("btn", "Экран и производительность...",
             lambda _: self.scene.set_ui(self.scene.screen_settings_ui)),
            ("btn", "Графика и интерфейс...",
             lambda _: self.scene.set_ui(self.scene.graphics_settings_ui)),
            ("btn", "Звуки и музыка...", lambda _: self.scene.set_ui(self.scene.sound_settings_ui)),
            ("btn", "Мир и игра...", lambda _: self.scene.set_ui(self.scene.world_settings_ui)),
            ("btn", "Модификации...", lambda _: self.scene.set_ui(self.scene.mods_settings_ui)),
            ("btn", "В главное меню", lambda _: self.scene.set_ui(self.scene.title_ui)),
        ]
        return items

    def back_to_settings(self):
        return ("btn", "Назад", lambda _: self.scene.set_ui(self.scene.settings_ui))

    # ---------- события/отрисовка ----------

    def pg_event(self, event: pg.event.Event):
        open_dd = next((d for d in self.dropdowns if d.opened), None)
        if open_dd is not None:
            open_dd.pg_event(event)
            return
        if self.keynav.pg_event(event):
            return
        for wdg in self.widgets:
            if wdg.pg_event(event):
                for d in self.dropdowns:
                    if d is not wdg:
                        d.opened = False
                return

    def draw(self):
        self.draw_background()
        self.screen.blit(self.header_surf, self.header_pos)
        for wdg in self.widgets:
            wdg.draw(self.screen)
        for dd in self.dropdowns:      # раскрытый список — поверх остального
            dd.draw_options(self.screen)
        self.sys_message.draw(self.screen)
        pg.display.flip()


class ScreenSettingsUI(MainSettingsUI):
    """Всё, что про монитор и скорость отрисовки."""
    header_title = "Экран и производительность"

    def get_settings_items(self):
        gs = config.GameSettings
        win = config.Window
        n_mon = max(1, len(pygame.display.get_desktop_sizes()))
        scr_icon = make_screen_icon()

        def set_mon(value, i):
            win.set_monitor(i)
            self.sys_message.send_reload_game_for_change()

        def set_fps(value, i):
            gs.set_max_fps(value)
            self.sys_message.send_reload_game_for_change()

        def set_view_tiles(value, i):
            win.set_view_tiles_width(value)
            self.sys_message.send_reload_game_for_change()

        fps_idx = fps_values_lst.index(gs.max_fps) if gs.max_fps in fps_values_lst else 1
        view_tiles_idx = view_tiles_lst.index(win.view_tiles_width) if win.view_tiles_width in view_tiles_lst else 2
        return [
            ("dd", "Монитор: {}", [str(i + 1) for i in range(n_mon)],
             win.monitor if win.monitor < n_mon else 0, set_mon, scr_icon),
            ("dd", "Обзор (блоков в ширину): {}", [str(v) for v in view_tiles_lst], view_tiles_idx,
             set_view_tiles, scr_icon),
            ("dd", "Лимит FPS: {}", fps_values_lst, fps_idx, set_fps, None),
            ("dd", "Вертикальная синхронизация: {}", ru_bool_lst, 0 if gs.vsync else 1,
             lambda v, i: (gs.set_vsync(bool_dict[v]), self.sys_message.send_reload_game_for_change()), None),
            self.back_to_settings(),
        ]


class GraphicsSettingsUI(MainSettingsUI):
    """Что видно на экране: небо, курсор, подписи."""
    header_title = "Графика и интерфейс"

    def get_settings_items(self):
        gs = config.GameSettings

        def set_cursor_kind(value, i):
            from units.Graphics.Cursor import CURSOR_KINDS, apply_cursor_kind
            gs.set_cursor(CURSOR_KINDS[i])
            apply_cursor_kind()   # применяется сразу, перезапуск не нужен

        from units.Graphics.Cursor import CURSOR_KINDS, CURSOR_KIND_LABELS as cursor_kind_labels
        cursor_idx = CURSOR_KINDS.index(gs.cursor) if gs.cursor in CURSOR_KINDS else 0
        return [
            ("dd", "Отображение облаков: {}", ru_bool_lst, 0 if gs.clouds else 1,
             lambda v, i: gs.set_clouds_state(bool_dict[v]), None),
            ("dd", "Отображение звёзд: {}", ru_bool_lst, 0 if gs.stars else 1,
             lambda v, i: gs.set_stars_state(bool_dict[v]), None),
            ("dd", "ID предмета: {}", ru_bool_lst, 0 if gs.view_item_index else 1,
             lambda v, i: gs.set_item_index_state(bool_dict[v]), None),
            ("dd", "Курсор: {}", cursor_kind_labels, cursor_idx, set_cursor_kind, None),
            self.back_to_settings(),
        ]


class WorldSettingsUI(MainSettingsUI):
    """Настройки самого мира и служебные действия с ним."""
    header_title = "Мир и игра"

    def get_settings_items(self):
        gs = config.GameSettings

        def set_dump(value, i):
            gs.set_dynamic_dump(bool_dict[value])
            try:
                self.scene.app.game_scene.game_map.dynamic_dump = bool_dict[value]
            except Exception:
                pass

        return [
            ("dd", "Выгрузка карты: {}", ru_bool_lst, 0 if gs.dynamic_dump else 1, set_dump, None),
            ("btn", "Создать мир обучения", lambda _: self.scene.create_tutorial_world()),
            self.back_to_settings(),
        ]


class ModsSettingsUI(MainSettingsUI):
    """Большое меню модификаций: список модов с их состоянием.

    Общий выключатель оставлял только «всё или ничего», а ломает игру обычно
    ровно один мод — и узнать, какой именно, можно было только из консоли.
    Здесь каждый мод — строка: что он добавляет, включён ли, и текст ошибки,
    если не загрузился.
    """
    header_title = "Модификации"
    row_h = int(58 * UI_SCALE)
    font_row = pygame.font.Font(MAIN_FONT_PATH, int(17 * UI_SCALE))
    font_sub = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', int(13 * UI_SCALE))
    row_bg = (63, 63, 70)
    row_bg_off = (39, 39, 42)
    err_color = "#F87171"
    off_color = "#A1A1AA"

    def __init__(self, scene):
        super().__init__(scene)
        self._build_rows()

    def relayout(self):
        super().relayout()
        self._build_rows()

    def get_settings_items(self):
        """Сверху — общий выключатель и выход; сами моды рисуются списком."""
        def set_mods(value, i):
            config.ModSettings.set_enabled(bool_dict[value])
            # блоки/существа модов регистрируются один раз при импорте
            # units.Tiles — включение/выключение требует перезапуска
            self.sys_message.send_reload_game_for_change()

        return [
            ("dd", "Загружать моды: {}", ru_bool_lst,
             0 if config.ModSettings.enabled else 1, set_mods, None),
            self.back_to_settings(),
        ]

    def _build_rows(self):
        from units import mods
        self.mod_rows = []       # (info, rect, кнопка переключения)
        folders = mods.mod_folders()
        if not folders:
            return
        w = int(460 * UI_SCALE)
        x = self.rect.centerx - w // 2
        # список идёт под виджетами настроек (общий выключатель + «Назад»)
        top = max(w2.rect.bottom for w2 in self.widgets) + int(14 * UI_SCALE)
        btn_w = int(96 * UI_SCALE)
        for i, folder in enumerate(folders):
            info = mods.mod_info(folder)
            y = top + i * (self.row_h + 6)
            if y + self.row_h > self.rect.h - 10:
                break            # ниже экрана не рисуем: прокрутки тут нет
            rect = pg.Rect(x, y, w, self.row_h)
            label = "Выключить" if not info["disabled"] else "Включить"
            btn = TextButton(lambda _, f=folder: self.toggle_mod(f),
                             (rect.right - btn_w - 8, y + (self.row_h - int(28 * UI_SCALE)) // 2,
                              btn_w, int(28 * UI_SCALE)),
                             label, font=self.font_sub)
            self.mod_rows.append((info, rect, btn))

    def toggle_mod(self, folder):
        config.ModSettings.set_mod_disabled(folder, not config.ModSettings.is_disabled(folder))
        self._build_rows()
        # мод регистрирует блоки при импорте units.Tiles — без перезапуска
        # его содержимое из игры не убрать и не добавить
        self.sys_message.send_reload_game_for_change()

    def pg_event(self, event: pg.event.Event):
        for _info, _rect, btn in getattr(self, "mod_rows", ()):
            if btn.pg_event(event):
                return
        return super().pg_event(event)

    def draw(self):
        self.draw_background()
        self.screen.blit(self.header_surf, self.header_pos)
        for wdg in self.widgets:
            wdg.draw(self.screen)
        self._draw_rows()
        for dd in self.dropdowns:
            dd.draw_options(self.screen)
        self.sys_message.draw(self.screen)
        pg.display.flip()

    def _draw_rows(self):
        rows = getattr(self, "mod_rows", ())
        if not rows:
            text = self.font_row.render(
                get_translated_text("Моды не найдены: положите папку в data/modifications"),
                True, self.off_color)
            self.screen.blit(text, (self.rect.centerx - text.get_width() // 2,
                                    max(w.rect.bottom for w in self.widgets) + 20))
            return
        for info, rect, btn in rows:
            pg.draw.rect(self.screen, self.row_bg_off if info["disabled"] else self.row_bg,
                         rect, border_radius=6)
            pg.draw.rect(self.screen, (24, 24, 27), rect, width=1, border_radius=6)
            title = f"{info['name']} {info['version']}".strip()
            color = self.off_color if info["disabled"] else "#FFFFFF"
            self.screen.blit(self.font_row.render(title, True, color), (rect.x + 10, rect.y + 6))
            if info["error"]:
                sub = get_translated_text("Ошибка: ") + info["error"]
                sub_color = self.err_color
            elif info["disabled"]:
                sub, sub_color = get_translated_text("Выключен"), self.off_color
            else:
                sub = (get_translated_text("блоков: ") + str(info["blocks"]) + "   " +
                       get_translated_text("существ: ") + str(info["creatures"]))
                if info["author"]:
                    sub += "   " + info["author"]
                sub_color = "#A1A1AA"
            surf = self.font_sub.render(sub, True, sub_color)
            max_w = rect.w - 130
            if surf.get_width() > max_w:
                surf = surf.subsurface((0, 0, max_w, surf.get_height()))
            self.screen.blit(surf, (rect.x + 10, rect.y + self.row_h - surf.get_height() - 6))
            btn.draw(self.screen)


categories_sounds = {
    "ui",
    'player',
    'creatures',
    'game',
    'background',
}

volume_values_lst = [0, 10, 20, 30, 40, 50, 60, 70, 80, 100]


class SoundSettingsUI(MainSettingsUI):
    header_title = "Звук и музыка"

    def get_settings_items(self):
        vs = config.VolumeSettings

        def vol(cat):
            return lambda value, i: set_category_volume(cat, value / 100)

        return [
            ("dd", "Музыка: {}%", volume_values_lst, self._volume_index(vs.background_volume), vol("background"), None),
            ("dd", "Звуки игры: {}%", volume_values_lst, self._volume_index(vs.game_volume), vol("game"), None),
            ("dd", "Игрок: {}%", volume_values_lst, self._volume_index(vs.player_volume), vol("player"), None),
            ("dd", "Существа: {}%", volume_values_lst, self._volume_index(vs.creatures_volume), vol("creatures"), None),
            ("dd", "Интерфейс: {}%", volume_values_lst, self._volume_index(vs.ui_volume), vol("ui"), None),
            self.back_to_settings(),
        ]

    @staticmethod
    def _volume_index(volume):
        """Индекс ближайшего значения громкости (устойчиво к произвольным числам в конфиге)."""
        value = volume * 100
        return min(range(len(volume_values_lst)), key=lambda i: abs(volume_values_lst[i] - value))


class WorldListUI(TitleUI):
    """Экран «Мои миры» — в общем стиле меню.

    Раньше он был отдельным окном-панелью со своими шрифтами и мелкими
    кнопками: рядом с остальными меню это читалось как чужой экран. Теперь
    наследует фон, заголовок и ГЕОМЕТРИЮ настроек — ширина строки и высота
    кнопки те же самые, поэтому размеры кнопок совпадают везде.
    """
    header_title = "Мои миры"
    font_item = pygame.font.Font(MAIN_FONT_PATH, int(20 * UI_SCALE))
    font_sub = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', int(13 * UI_SCALE))
    font_hint = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', int(13 * UI_SCALE))
    sub_color = "#A1A1AA"
    card_bg = (63, 63, 70)
    row_w = int(460 * UI_SCALE)      # как у виджетов настроек
    row_h = int(34 * UI_SCALE)
    card_h = int(48 * UI_SCALE)      # строка мира выше: под ней подпись
    gap = int(8 * UI_SCALE)
    del_w = int(44 * UI_SCALE)

    def __init__(self, scene) -> None:
        super().__init__(scene)
        self.objects = GroupUI([])   # логотип и кнопки титула тут не нужны

        htxt = add_outline_to_image(textfont_btn.render(get_translated_text(self.header_title), True, WHITE),
                                    2, "#1C1917")
        self.header_surf = htxt
        self.header_pos = (self.rect.centerx - htxt.get_width() // 2, 20)

        x = self.rect.centerx - self.row_w // 2
        y = self.header_pos[1] + htxt.get_height() + 14
        half = (self.row_w - self.gap) // 2
        self.btn_tutorial = TextButton(lambda _: self.scene.create_tutorial_world(),
                                       (x, y, half, self.row_h), "Пройти обучение",
                                       font=self.font_item)
        self.btn_new = TextButton(lambda _: self.scene.new_world(),
                                  (x + half + self.gap, y, half, self.row_h), "+ Новый мир",
                                  font=self.font_item)
        self.list_top = y + self.row_h + int(14 * UI_SCALE)
        # «Назад» — снизу, на месте, где у настроек последний пункт списка
        self.btn_back = TextButton(lambda _: self.scene.back(),
                                   (x, self.rect.h - self.row_h - int(34 * UI_SCALE),
                                    self.row_w, self.row_h), "Назад", font=self.font_item)
        self.list_bottom = self.btn_back.rect.top - int(10 * UI_SCALE)

        self.scroll_y = 0
        self.worlds = []
        self.card_btns = []      # (name_btn, del_btn, meta, y)
        self.confirm_delete_id = None
        self.reload_worlds()

    def reload_worlds(self):
        from units.Map import WorldStorage
        self.worlds = WorldStorage.list_worlds()
        self.scroll_y = 0
        self.confirm_delete_id = None
        self._build()

    def _build(self):
        self.card_btns = []
        x = self.rect.centerx - self.row_w // 2
        for i, meta in enumerate(self.worlds):
            wid = meta["id"]
            y = self.list_top + i * (self.card_h + self.gap) + self.scroll_y
            name_btn = TextButton(lambda _, wid=wid: self.scene.play_world(wid),
                                  (x, y, self.row_w - self.del_w - self.gap, self.row_h),
                                  meta.get("name", wid), font=self.font_item)
            del_text = "?" if self.confirm_delete_id == wid else "X"
            del_btn = TextButton(lambda _, wid=wid: self.delete_world(wid),
                                 (x + self.row_w - self.del_w, y, self.del_w, self.row_h),
                                 del_text, font=self.font_item)
            self.card_btns.append((name_btn, del_btn, meta, y))

    def delete_world(self, wid):
        from units.Map import WorldStorage
        if self.confirm_delete_id == wid:
            WorldStorage.delete_world(wid)
            self.reload_worlds()
        else:
            self.confirm_delete_id = wid  # первый клик — просим подтвердить
            self._build()

    def scroll(self, dy):
        content_h = len(self.worlds) * (self.card_h + self.gap)
        view_h = self.list_bottom - self.list_top
        min_scroll = min(0, view_h - content_h)
        self.scroll_y = max(min_scroll, min(0, self.scroll_y + dy))
        self._build()

    def pg_event(self, event: pg.event.Event) -> Union[bool, None]:
        if event.type == pg.MOUSEWHEEL:
            self.scroll(event.y * 40)
            return
        self.btn_back.pg_event(event)
        self.btn_tutorial.pg_event(event)
        self.btn_new.pg_event(event)
        for name_btn, del_btn, meta, y in self.card_btns:
            if self.list_top <= y <= self.list_bottom - self.row_h:
                name_btn.pg_event(event)
                del_btn.pg_event(event)

    def draw(self):
        self.draw_background()
        self.screen.blit(self.header_surf, self.header_pos)
        self.btn_tutorial.draw(self.screen)
        self.btn_new.draw(self.screen)
        self.btn_back.draw(self.screen)

        if not self.worlds:
            msg = self.font_item.render(get_translated_text("Пока нет миров — начните с обучения"),
                                        True, self.sub_color)
            self.screen.blit(msg, (self.rect.centerx - msg.get_width() // 2, self.list_top + 20))
        else:
            from units.Map import WorldStorage
            for name_btn, del_btn, meta, y in self.card_btns:
                if y + self.card_h < self.list_top or y > self.list_bottom:
                    continue
                pg.draw.rect(self.screen, self.card_bg,
                             (name_btn.rect.x - 6, y - 4, self.row_w + 12, self.card_h),
                             border_radius=6)
                name_btn.draw(self.screen)
                del_btn.draw(self.screen)
                sub = f"{WorldStorage.format_last_played(meta.get('last_played'))}  •  " \
                      f"{WorldStorage.format_playtime(meta.get('playtime'))}"
                if meta.get("tutorial"):
                    sub = get_translated_text("обучение") + "  •  " + sub
                self.screen.blit(self.font_sub.render(sub, True, self.sub_color),
                                 (name_btn.rect.x, y + self.row_h - 2))

        hint = self.font_hint.render(get_translated_text("Esc — назад   •   колесо — прокрутка"),
                                     True, self.sub_color)
        self.screen.blit(hint, (self.rect.centerx - hint.get_width() // 2,
                                self.rect.h - int(22 * UI_SCALE)))
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
        self.draw_world_background()
        self.screen.blit(self.surface, self.rect_surface)
        self.btn_relive.draw(self.screen)
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        self.btn_relive.pg_event(event)
        if event.type == pg.KEYDOWN:
            self.scene.relive()

    def relayout(self):
        self.__init__(self.scene)


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
        self.draw_world_background()
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

    def relayout(self):
        self.__init__(self.scene)


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

    def relayout(self):
        # не зовём self.__init__: конструктору нужен player_achievements,
        # который тут не хранится (сам параметр не используется) — вместо
        # этого напрямую пересчитываем то же, что делает __init__.
        self.rect = pg.Rect((0, 0, 370, 400))
        w, h = self.screen.get_size()
        self.rect.center = w // 2, h // 2
        self.surface = pg.Surface(self.rect.size).convert_alpha()
        self.surface.fill((82, 82, 91, 150))
        self._ach_key = None  # форсируем пересборку surface_achievements под новый rect.w

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
        self.draw_world_background()
        self.surface.fill(self.bg)
        title = textfont_btn.render(get_translated_text("Достижения"), True, "#FFFFFF")
        self.surface.blit(title, (10, 10))

        self.surface.blit(self.surface_achievements, (0, 35))

        self.screen.blit(self.surface, self.rect)
        pg.display.flip()


class JournalUI(UI):
    """Журнал: акты сюжета и прочитанные надписи.

    До него `GameMap.read_inscriptions` копил прочитанное вхолостую — поле
    было, сохранялось, а читателя у него не было ни одного. Игрок находил
    плиту, читал строчку, и она уходила в никуда.
    """
    bg = (39, 39, 42)
    font_title = pygame.font.Font(MAIN_FONT_PATH, 28)
    font_act = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 20)
    font_goal = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 16)
    font_note = pygame.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 15)
    done_color = "#84CC16"
    todo_color = "#FDE047"
    text_color = "#E4E4E7"
    dim_color = "#A1A1AA"

    def __init__(self, scene):
        super().__init__(scene)
        self.scroll = 0
        self.relayout()

    def relayout(self):
        w, h = self.screen.get_size()
        self.rect = pg.Rect(0, 0, min(760, w - 40), min(560, h - 40))
        self.rect.center = w // 2, h // 2
        self.surface = pg.Surface(self.rect.size).convert_alpha()

    def _game(self):
        return self.scene.app.game_scene

    def lines(self):
        """Плоский список строк (текст, шрифт, цвет) — так проще прокручивать
        и не надо считать высоту блоков дважды."""
        from units.Story import journal_entries
        acts, notes = journal_entries(self._game())
        out = []
        for title, goal, done in acts:
            mark = "✓" if done else "•"
            out.append((f"{mark} {title}", self.font_act,
                        self.done_color if done else self.todo_color))
            out.append(("   " + goal, self.font_goal, self.dim_color))
            out.append(("", self.font_goal, self.text_color))
        out.append((get_translated_text("Найденные записи"), self.font_act, self.todo_color))
        if not notes:
            out.append((get_translated_text("Пока ничего не прочитано"),
                        self.font_note, self.dim_color))
        for heading, body in notes:
            out.append(("  " + heading, self.font_goal, self.text_color))
            for line in body:
                out.append(("    " + line, self.font_note, self.dim_color))
            out.append(("", self.font_note, self.text_color))
        return out

    def draw(self):
        self.draw_world_background()
        self.surface.fill(self.bg)
        title = self.font_title.render(get_translated_text("Журнал"), True, "#FFFFFF")
        self.surface.blit(title, (16, 12))
        pg.draw.line(self.surface, "#52525B", (16, 50), (self.rect.w - 16, 50), 2)

        y = 60 - self.scroll
        for text, font, color in self.lines():
            if text and -30 < y < self.rect.h:
                self.surface.blit(font.render(text, True, color), (18, y))
            y += font.get_height() + 2
        self._content_height = y + self.scroll

        hint = self.font_note.render(get_translated_text("Esc — закрыть"), True, self.dim_color)
        self.surface.blit(hint, (self.rect.w - hint.get_width() - 14, self.rect.h - 22))
        self.screen.blit(self.surface, self.rect)
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * 40)
            return True
        if event.type == pg.KEYDOWN and event.key in (pg.K_DOWN, pg.K_UP):
            self.scroll = max(0, self.scroll + (40 if event.key == pg.K_DOWN else -40))
            return True


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
        w = min(680, SCREEN_SIZE[0] - 40)
        h = min(600, SCREEN_SIZE[1] - 40)
        self.rect = pg.Rect(0, 0, w, h)
        self.rect.center = SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2

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

    def relayout(self):
        self.__init__(self.scene)
