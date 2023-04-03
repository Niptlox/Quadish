from units import Tiles
from units.App.App import *
from units.Graphics.Cursor import set_cursor, CURSOR_NORMAL
from units.Objects.Player import Player
from units.UI.BlocksUI import BlocksUIManger
from units.UI.UI import GameUI
from units.Map.GameMap import GameMap
from units.Map.ScreenMap import ScreenMap
from units.App.Scenes import TitleScene, OpenMapScenePopupMenu, SaveMapScenePopupMenu, PauseScenePopupMenu, EndSceneUI, \
    AchievementsSceneUI, HelpSceneUI
import subprocess

from units.config import GameSettings
from units.sound import sounds_background, get_random_sound_of

set_cursor(CURSOR_NORMAL)
choice_pos1 = None
choice_pos2 = None


class GameApp(App):
    def __init__(self) -> None:
        self.title_scene = TitleScene(self)
        self.game_scene = GameScene(self)
        self.openm_scene = OpenMapScenePopupMenu(self)
        self.savem_scene = SaveMapScenePopupMenu(self)
        self.pause_scene = PauseScenePopupMenu(self)
        self.end_scene = EndSceneUI(self)
        self.achievements_scene = AchievementsSceneUI(self)
        self.help_scene = HelpSceneUI(self)
        super().__init__(self.title_scene)

    @classmethod
    def open_help(cls):
        path = CWDIR + f"data/translations/help_{GameSettings.language}.md"
        subprocess.Popen(('start', path), shell=True, cwd=CWDIR)


f = open("fff.txt", "w")


class GameScene(Scene):
    _Tiles = Tiles

    def __init__(self, app) -> None:
        super().__init__(app)
        self.game_map = GameMap(self, Generate_type)
        self.ui = GameUI(self)
        self.player = Player(self, *config.GameSettings.start_pos)
        self.screen_map = ScreenMap(self.display, self.game_map, self.player)
        self.screen_map.teleport_to_player()
        self.blocks_ui_manager = BlocksUIManger(self.player)
        self.ui.init_ui()
        self.tact = 0
        self.total_time = 0
        self.ctrl_on = False
        self.first_start = False
        self.hided_ui = False
        self.background_sound = get_random_sound_of(sounds_background).play(loops=-1, )
        print(self, self.player.inventory, file=f)
        # print(list(self.blocks_ui_manager.blocks_ui.values())[0])

    def reinit_player(self):
        self.player.reinit()
        self.blocks_ui_manager = BlocksUIManger(self.player)

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
                if event.key == pg.K_e:
                    # OPEN OR CLOSE  full INVENTORY
                    if self.player.inventory.ui.opened:
                        self.player.inventory.ui.close()
                    elif self.blocks_ui_manager.opened:
                        self.blocks_ui_manager.close()
                    else:
                        self.player.inventory.ui.open()
                    return True

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
            if not self.blocks_ui_manager.pg_event(event):
                self.player.pg_event(event)
        if self.first_start:
            self.set_scene(self.app.pause_scene)
            self.first_start = False

    def update(self):
        # print(self, self.inventory, file=f)

        self.elapsed_time = min(self.elapsed_time, 120)
        self.total_time += self.elapsed_time
        # self.ui.draw_sky()
        self.screen_map.draw_sky()

        self.screen_map.update(self.tact, self.elapsed_time)
        self.player.update(self.tact, self.elapsed_time)
        if not self.player.alive:
            self.running = False
            self.new_scene = self.app.end_scene

        if not self.hided_ui:
            self.blocks_ui_manager.draw(self.display)
            self.player.inventory.ui.draw(self.display)
            self.ui.draw()
        self.ui.flip()
        self.tact += 1
