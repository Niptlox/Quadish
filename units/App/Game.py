from units import Tiles, mods
from units.Tiles import tile_imgs, ANIMATED_TILES
from units.App.App import *
from units.Graphics.Cursor import set_cursor, CURSOR_NORMAL
from units.Objects.Player import Player
from units.UI.BlocksUI import BlocksUIManger
from units.UI.UI import GameUI
from units.Map.GameMap import GameMap
from units.Map.ScreenMap import ScreenMap
from units.App.Scenes import TitleScene, WorldsScenePopupMenu, PauseScenePopupMenu, EndSceneUI, \
    AchievementsSceneUI, HelpSceneUI, JournalSceneUI
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
        self.journal_scene = JournalSceneUI(self)
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
        # События мира: то, что происходит С игроком (units/Events.py)
        from units.Events import EventDirector
        self.events = EventDirector()
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

                elif event.key == pg.K_j and not pg.key.get_mods():
                    # Журнал сюжета. Без модификаторов: Alt+J это смена режима
                    self.set_scene(self.app.journal_scene)
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

        if ANIMATED_TILES:
            # подменить кадр анимированных тайлов (лава, блоки модов)
            mods.update_tile_animations(tile_imgs, self.tact, ANIMATED_TILES)

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
        # Часы мира идут отдельно от tact: они сохраняются вместе с миром
        self.game_map.world_time = getattr(self.game_map, "world_time", 0) + 1
        if self.tact % 30 == 0:
            self.tutorial.update()
        # Автоматика под прогрузчиком должна работать и когда игрок ушёл:
        # ScreenMap обновляет только видимые тайлы.
        self.game_map.tick_offscreen(self.tact, self.screen_map.visible_chunks)
        # Поток воды: обслуживается порцией клеток за такт (units/Map/WaterFlow.py).
        # Водоём в равновесии не стоит ничего — очередь просто пуста.
        self.game_map.water_flow.tick(self.tact)
        self.events.update(self)
        if self.tact % FPS == 0:
            # Сюжет смотрит в инвентарь и координаты — раз в секунду хватает
            from units.Story import update_story
            closed = update_story(self)
            if closed is not None:
                self.ui.new_sys_message(f"{closed.title}: выполнено")
        if self.tact % (FPS * 5) == 0:
            self.game_map.unload_far_chunks()
        if self.tact % AUTOSAVE_PERIOD_TACTS == 0 and self.game_map.world_id is not None:
            self.game_map.save_current_game_map()
