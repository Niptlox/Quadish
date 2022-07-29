from units.common import *
from units.App import *
from units.Cursor import set_cursor, CURSOR_NORMAL
from units.Player import Player
from units.UI.UI import GameUI, SwitchMapUI, EndUI, PauseUI
from units.config import Window
from units.map.GameMap import GameMap
from units.map.ScreenMap import ScreenMap

import subprocess

set_cursor(CURSOR_NORMAL)
choice_pos1 = None
choice_pos2 = None


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
        subprocess.Popen(('start', CWDIR + '/help.txt'), shell=True)


class GameScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.game_map = GameMap(self, Generate_type)

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
                elif event.key == K_c and pg.key.get_mods() & KMOD_ALT:
                    make_screenshot(self.screen)
                    self.ui.new_sys_message("Скриншот сохранён")
                elif event.key == K_x and pg.key.get_mods() & KMOD_ALT and self.player.creative_mode:
                    self.tact += FPS * 60
                elif event.key == K_z and pg.key.get_mods() & KMOD_ALT and self.player.creative_mode:
                    self.tact += FPS * 60 * 10
                elif event.key == K_g and pg.key.get_mods() & KMOD_CTRL:
                    global choice_pos1, choice_pos2
                    print("Choice of world")
                    if choice_pos1 is None:
                        choice_pos1 = self.player.rect.x // TSIZE + 1, self.player.rect.y // TSIZE + 1
                        print("choice_pos1", choice_pos1)
                        self.ui.new_sys_message(f"Позиция 1: {choice_pos1}")

                    elif choice_pos2 is None:
                        choice_pos2 = self.player.rect.x // TSIZE - 1, self.player.rect.y // TSIZE - 1
                        self.ui.new_sys_message(f"Позиция 2: {choice_pos2}")
                        print("choice_pos2", choice_pos2)
                        print("Creating array choice")
                        out = self.game_map.get_choice_world(choice_pos1, choice_pos2)
                        print(out)
                        self.ui.new_sys_message(f"Структура: {(choice_pos1, out[0])}")
                        choice_pos1 = choice_pos2 = None
                if event.key == K_s and self.ctrl_on:
                    self.game_map.save_current_game_map()

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
        # self.ui.draw_sky()
        self.screen_map.draw_sky()

        self.screen_map.update(self.tact)
        if not self.player.update(self.tact):
            self.running = False
            self.new_scene = self.app.end_scene

        if self.player.chest_ui.opened:
            self.player.chest_ui.draw(self.display)
        else:
            self.player.inventory.ui.draw(self.display)
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

    def save_and_exit(self):
        self.app.game_scene.game_map.save_current_game_map()
        self.exit()

    def editfullscreen(self):
        Window.set_fullscreen(not Window.fullscreen)
        self.app.game_scene.ui.new_sys_message("Перезапустите игру", draw_now=True)
        print("toggle_fullscreen")
        # pygame.display.toggle_fullscreen()
