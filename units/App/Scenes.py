import webbrowser

from units.App.App import *
from units.UI.UI import SwitchMapUI, EndUI, PauseUI, AchievementsUI, TitleUI, MainSettingsUI, SoundSettingsUI
from units.config import Window


class TitleScene(SceneMenu):
    def __init__(self, app):
        super(TitleScene, self).__init__(app, TitleUI)
        self.title_ui = self.ui
        self.settings_ui = MainSettingsUI(self)
        self.sound_settings_ui = SoundSettingsUI(self)

        self.developers_ui = None

    def new_game(self):
        self.set_scene(self.app.game_scene)
        self.app.game_scene.game_map.new_world()

    def open_developers(self):
        webbrowser.open('https://gamejolt.com/@Niptlox', new=2)

    def main(self):
        # pg.mixer.stop()
        return super(TitleScene, self).main()


class OpenMapScenePopupMenu(ScenePopupMenu):
    def __init__(self, app: App) -> None:
        self.game = app.game_scene
        super().__init__(app, lambda _app: SwitchMapUI(_app, "Открыть карту"))

    def open_map(self, num=0):
        self.set_scene(self.app.game_scene)
        return self.game.game_map.open_game_map(self.game, num)

    def main(self):
        ar = self.game.game_map.get_list_num_maps()
        ar = [i not in ar for i in range(self.game.game_map.save_slots)]
        self.ui.set_disabled_btns(ar)
        return super().main()


class SaveMapScenePopupMenu(ScenePopupMenu):
    def __init__(self, app: App) -> None:
        self.game = app.game_scene
        super().__init__(app, lambda app: SwitchMapUI(app, "Сохранить карту"))

    def open_map(self, num=0):
        self.set_scene(None)
        return self.game.game_map.save_game_map(self.game, num)

    def main(self):
        ar = self.game.game_map.get_list_num_maps()
        ar = [i in ar for i in range(self.game.game_map.save_slots)]
        self.ui.set_check_btns(ar)
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

    def tp_to_home(self):
        self.app.game_scene.player.tp_to_home()
        self.set_scene(self.app.game_scene)

    def save_and_exit(self):
        self.app.game_scene.game_map.save_current_game_map()
        self.exit()

    def save_and_to_main_menu(self):
        self.app.game_scene.game_map.save_current_game_map()
        self.set_scene(self.app.title_scene)

    def new_world(self):
        self.app.game_scene.game_map.new_world()
        self.set_scene(self.app.game_scene)

    def editfullscreen(self):
        Window.set_fullscreen(not Window.fullscreen)
        self.app.game_scene.ui.new_sys_message("Перезапустите игру", draw_now=True)
        print("toggle_fullscreen")
        # pygame.display.toggle_fullscreen()


class AchievementsSceneUI(ScenePopupMenu):
    def __init__(self, app: App) -> None:
        self.game = app.game_scene
        super().__init__(app, lambda app: AchievementsUI(app, self.game.player.achievements))
