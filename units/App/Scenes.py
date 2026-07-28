import webbrowser

from units.App.App import *
from units.UI.UI import (WorldListUI, EndUI, PauseUI, AchievementsUI, TitleUI, MainSettingsUI,
                         SoundSettingsUI, HelpUI, ScreenSettingsUI, GraphicsSettingsUI,
                         WorldSettingsUI, ModsSettingsUI)


class TitleScene(SceneMenu):
    def __init__(self, app):
        super(TitleScene, self).__init__(app, TitleUI)
        self.title_ui = self.ui
        # Настройки разбиты на модули: в основном меню только размер меню и
        # режим экрана, остальное — по разделам (см. MainSettingsUI).
        self.settings_ui = MainSettingsUI(self)
        self.sound_settings_ui = SoundSettingsUI(self)
        self.screen_settings_ui = ScreenSettingsUI(self)
        self.graphics_settings_ui = GraphicsSettingsUI(self)
        self.world_settings_ui = WorldSettingsUI(self)
        self.mods_settings_ui = ModsSettingsUI(self)

        self.developers_ui = None

    def new_game(self):
        self.set_scene(self.app.game_scene)
        self.app.game_scene.game_map.new_world()
        # сразу создаём файл мира, чтобы он появился в списке
        self.app.game_scene.game_map.save_current_game_map()

    def create_tutorial_world(self):
        """Открыть мир обучения; если удалён или ещё не создан — создать заново."""
        from units.Map import WorldStorage
        game = self.app.game_scene
        self.set_scene(game)
        existing = WorldStorage.find_tutorial_world()
        if existing:
            if game.game_map.open_game_map(game, existing["id"]):
                return
        game.game_map.new_world(tutorial=True)
        game.game_map.save_current_game_map()

    def open_worlds(self):
        self.set_scene(self.app.worlds_scene)

    def open_developers(self):
        webbrowser.open('https://gamejolt.com/@Niptlox', new=2)

    def main(self):
        # pg.mixer.stop()
        return super(TitleScene, self).main()


class WorldsScenePopupMenu(ScenePopupMenu):
    """Экран «Мои миры»: список сохранённых миров + создание нового."""

    def __init__(self, app: App) -> None:
        self.game = app.game_scene
        super().__init__(app, WorldListUI)
        self.back_scene = app.title_scene

    def play_world(self, world_id):
        res = self.game.game_map.open_game_map(self.game, world_id)
        if res:
            self.set_scene(self.app.game_scene)

    def new_world(self):
        self.set_scene(self.app.game_scene)
        self.game.game_map.new_world()
        self.game.game_map.save_current_game_map()

    def create_tutorial_world(self):
        """Открыть мир обучения; если удалён или не создан — создать заново."""
        from units.Map import WorldStorage
        game = self.game
        self.set_scene(game)
        existing = WorldStorage.find_tutorial_world()
        if existing and game.game_map.open_game_map(game, existing["id"]):
            return
        game.game_map.new_world(tutorial=True)
        game.game_map.save_current_game_map()

    def back(self):
        self.set_scene(self.app.title_scene)

    def main(self):
        self.ui.reload_worlds()
        return super().main()


class EndSceneUI(Scene):
    def __init__(self, app):
        super().__init__(app)
        # ссылка на цену самой игры
        self.game = self.app.game_scene
        self.ui = EndUI(self)
        self.ui.init_ui()

    def relive(self):
        self.running = False
        self.new_scene = self.app.game_scene
        self.game.player.relive()

    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT
            self.ui.pg_event(event)

    def update(self):
        self.ui.draw()


class PauseScenePopupMenu(ScenePopupMenu):
    def __init__(self, app: App) -> None:
        super().__init__(app, PauseUI)
        self.back_scene = self.app.game_scene

    def resume(self):
        self.set_scene(self.app.game_scene)

    def save_world(self):
        self.app.game_scene.game_map.save_current_game_map()
        self.set_scene(self.app.game_scene)

    def tp_to_home(self):
        self.app.game_scene.player.tp_to_home()
        self.set_scene(self.app.game_scene)

    def save_and_exit(self):
        self.app.game_scene.game_map.save_current_game_map()
        self.exit()

    def save_and_to_main_menu(self):
        self.app.game_scene.game_map.save_current_game_map()
        self.set_scene(self.app.title_scene)

    def editfullscreen(self):
        # Живое переключение (как F11) — common.apply_resize сам обновляет
        # Window.fullscreen и пересчитывает SCREEN_SIZE, перезапуск не нужен.
        common.apply_resize(fullscreen=not common.FULLSCREEN)
        self._on_screen_changed()


class AchievementsSceneUI(ScenePopupMenu):
    def __init__(self, app: App) -> None:
        self.game = app.game_scene
        super().__init__(app, lambda app: AchievementsUI(app, self.game.player.achievements))


class HelpSceneUI(ScenePopupMenu):
    def __init__(self, app: App) -> None:
        super().__init__(app, HelpUI)
