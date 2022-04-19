import subprocess

from units.App import *
from units.Cursor import set_cursor, CURSOR_NORMAL
from units.Player import Player
from units.UI.UI import GameUI, SwitchMapUI, EndUI, PauseUI
from units.map.GameMap import GameMap
from units.map.ScreenMap import ScreenMap

set_cursor(CURSOR_NORMAL)


class Game(App):
    def __init__(self) -> None:
        self.game_scene = GameScene(self)
        self.openm_scene = OpenMapSceneUI(self)
        self.savem_scene = SaveMapSceneUI(self)
        self.pause_scene = PauseSceneUI(self)
        self.end_scene = EndSceneUI(self)
        super().__init__(self.game_scene)

    @classmethod
    def open_help(cls):
        subprocess.Popen(('start', 'help.txt'), shell=True)


class GameScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.game_map = GameMap(self, generate_type)

        self.ui = GameUI(self)
        self.player = Player(self, 0, 0)
        self.screen_map = ScreenMap(self.display, self.game_map, self.player)
        self.ui.init_ui()
        self.tact = 0
        self.ctrl_on = False
        self.first_start = False

    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT
            if self.ui.pg_event(event):
                continue
            if event.type == KEYDOWN:
                if event.key == K_F1:
                    self.app.open_help()
                    self.set_scene(self.app.pause_scene)
                elif event.key == K_ESCAPE:
                    self.set_scene(self.app.pause_scene)
                elif event.key == K_LCTRL:
                    self.ctrl_on = True
                if event.key == K_s and self.ctrl_on:
                    self.game_map.save_game_map(self, self.game_map.num_save_map)
            elif event.type == KEYUP:
                if event.key == K_LCTRL:
                    self.ctrl_on = False
            elif event.type == EVENT_100_MSEC:
                if show_info_menu:
                    self.ui.redraw_info()
            self.player.pg_event(event)
        if self.first_start:
            self.set_scene(self.app.pause_scene)
            self.first_start = False

    def update(self):
        self.ui.draw_sky()

        self.screen_map.update(self.tact)
        if not self.player.update(self.tact):
            self.running = False
            self.new_scene = self.app.end_scene

        self.ui.draw()
        self.tact += 1


class OpenMapSceneUI(SceneUI):
    def __init__(self, app: Game) -> None:
        self.game = app.game_scene
        super().__init__(app, lambda app: SwitchMapUI(app, "Открыть карту"))

    def open_map(self, num=0):
        self.set_scene(self.app.game_scene)
        return self.game.game_map.open_game_map(self.game, num)

    def main(self):
        ar = self.game.game_map.get_list_num_maps()
        ar = [i not in ar for i in range(self.game.game_map.save_slots)]
        self.ui.set_disabled_btns(ar)
        return super().main()


class SaveMapSceneUI(SceneUI):
    def __init__(self, app: Game) -> None:
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


class PauseSceneUI(SceneUI):
    def __init__(self, app: Game) -> None:
        super().__init__(app, PauseUI)
        self.back_scene = self.app.game_scene

    def tp_to_home(self):
        self.app.game_scene.player.tp_to_home()
        self.set_scene(self.app.game_scene)
