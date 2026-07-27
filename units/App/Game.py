from units import Tiles
from units.App.App import *
from units.Graphics.Cursor import set_cursor, CURSOR_NORMAL
from units.Objects.Player import Player
from units.UI.BlocksUI import BlocksUIManger
from units.UI.UI import GameUI
from units.Map.GameMap import GameMap
from units.Map.ScreenMap import ScreenMap
from units.App.Scenes import TitleScene, WorldsScenePopupMenu, PauseScenePopupMenu, EndSceneUI, \
    AchievementsSceneUI, HelpSceneUI
from units.Map import WorldStorage
from units.Tutorial import TutorialHints

from units.config import GameSettings
from units.sound import sounds_background, get_random_sound_of

set_cursor(CURSOR_NORMAL)
choice_pos1 = None
choice_pos2 = None

AUTOSAVE_PERIOD_TACTS = FPS * 300  # автосохранение раз в ~5 минут


class GameApp(App):
    def __init__(self) -> None:
        self.title_scene = TitleScene(self)
        self.game_scene = GameScene(self)
        self.worlds_scene = WorldsScenePopupMenu(self)
        self.pause_scene = PauseScenePopupMenu(self)
        self.end_scene = EndSceneUI(self)
        self.achievements_scene = AchievementsSceneUI(self)
        self.help_scene = HelpSceneUI(self)
        if GameSettings.debug_open_map:
            super().__init__(self.game_scene)
        else:
            super().__init__(self.title_scene)

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
        self.first_start = False
        self.hided_ui = False
        self.tutorial = TutorialHints(self)
        self.background_sound = get_random_sound_of(sounds_background).play(loops=-1, )
        if GameSettings.debug_open_map:
            worlds = WorldStorage.list_worlds()
            if worlds:
                self.game_map.open_game_map(self, worlds[0]["id"])
        # print(list(self.blocks_ui_manager.blocks_ui.values())[0])

    def reinit_player(self):
        self.player.reinit()
        self.blocks_ui_manager = BlocksUIManger(self.player)

    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # не теряем прогресс при закрытии окна
                if self.game_map.world_id is not None:
                    self.game_map.save_current_game_map()
                self.running = EXIT
            if self.pg_event(event):
                continue
            if self.blocks_ui_manager.pg_event(event):
                continue
            if self.ui.pg_event(event):
                continue
            if event.type == KEYDOWN:
                if event.key == K_F1:
                    self.set_scene(self.app.help_scene)
                elif event.key == K_ESCAPE:
                    self.set_scene(self.app.pause_scene)
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
                    elif not self.blocks_ui_manager.opened:
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
                if event.key == K_s and event.mod & pg.KMOD_CTRL:
                    self.game_map.save_current_game_map()

            elif event.type == EVENT_100_MSEC:
                if show_info_menu:
                    self.ui.redraw_info()

            self.player.pg_event(event)
        if self.first_start:
            self.set_scene(self.app.pause_scene)
            self.first_start = False

    def update(self):
        self.elapsed_time = min(self.elapsed_time, 120)
        self.total_time += self.elapsed_time
        self.screen_map.draw_sky()

        self.screen_map.update(self.tact, self.elapsed_time)
        self.player.update(self.tact, self.elapsed_time)
        if not self.player.alive:
            self.running = False
            self.new_scene = self.app.end_scene

        self.tutorial.draw_world(self.display)  # маркер цели — в мировых координатах
        self.ui.blit_world()  # растянуть мир (self.display) на реальный экран

        if not self.hided_ui:
            self.blocks_ui_manager.draw(self.screen)
            self.player.inventory.ui.draw(self.screen)
            self.ui.draw()
            self.tutorial.draw_hud(self.screen)
        self.ui.flip()
        self.tact += 1
        if self.tact % 30 == 0:
            self.tutorial.update()
        if self.tact % (FPS * 5) == 0:
            self.game_map.unload_far_chunks()
        if self.tact % AUTOSAVE_PERIOD_TACTS == 0 and self.game_map.world_id is not None:
            self.game_map.save_current_game_map()
