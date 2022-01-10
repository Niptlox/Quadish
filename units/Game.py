from time import sleep

from pygame import image
from units.common import *
from pygame.locals import *

from units.map.GameMap import GameMap
from units.map.ScreenMap import ScreenMap
from units.UI.UI import GameUI, SwitchMapUI
from units.Player import Player
from units.Cursor import set_cursor, CURSOR_NORMAL

EXIT = 0
set_cursor(CURSOR_NORMAL)

class App:
    screen = screen_
    def __init__(self, scene=None):
        self.clock = pg.time.Clock()
        self.running= True        
        self.scene = scene  # Тек сцена
        self.last_scene = self.scene  # Прошлая сцена
        
    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT

    def main(self):        
        self.running = True        
        while self.running:            
            self.pg_events()
            self.update()
            self.clock.tick(FPS)        

    def update(self):
        if self.scene is not None:            
            scene = self.scene.main()
            if scene is None: 
                scene = self.last_scene
            elif scene is EXIT:
                self.running = EXIT
            self.last_scene = self.scene
            self.scene = scene


class Scene(App):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.new_scene = None
        self.display = display_

    def main(self):
        self.running = True
        while self.running:            
            self.clock.tick(FPS)   
            self.pg_events()
            self.update()            
        if self.running is EXIT:
            return EXIT     
        return self.new_scene


class SceneUI(Scene):
    def __init__(self, app, UI) -> None:
        super().__init__(app=app)
        self.ui = UI(self)
        self.ui.init_ui()

    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                    self.new_scene = None
            self.ui.pg_event(event)

    def update(self):
        self.ui.draw()


class Game(App):
    def __init__(self) -> None:
        self.game_scene = GameScene(self)
        self.openm_scene = OpenMapSceneUI(self)
        self.savem_scene = SaveMapSceneUI(self)
        super().__init__(self.game_scene)


class GameScene(Scene):        
    def __init__(self, app) -> None:
        super().__init__(app)
        self.game_map = GameMap(generate_type)
        
        self.ui = GameUI(self)
        self.player = Player(self, self.game_map, 0, 0)        
        self.screen_map = ScreenMap(self.display, self.game_map, self.player)        
        self.ui.init_ui()


    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT
            if event.type == KEYDOWN:
                if event.key == K_u:
                    self.pause = not self.pause
                elif event.key == K_o:
                    # self.game_map.load_game_map(self.player.active_cell)
                    self.new_scene = self.app.openm_scene
                    self.running = False
                elif event.key == K_p:
                    #self.game_map.save_game_map(self.player.active_cell) 
                    self.running = False
                    self.new_scene = self.app.savem_scene
            elif event.type == EVENT_100_MSEC:
                if show_info_menu:
                    self.ui.redraw_info()
            self.player.pg_event(event)            

    def update(self):
        self.ui.draw_sky()

        self.screen_map.update()
        self.player.update()

        self.ui.draw()



class OpenMapSceneUI(SceneUI):
    def __init__(self, app: Game) -> None:
        self.game = app.game_scene
        super().__init__(app, lambda app: SwitchMapUI(app, "Загрузить карту"))

    def open_map(self, num=0):
        self.running = False # -> выход из процесса этой сцены
        self.new_scene = None # -> переход на прошлую сцену
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
        self.running = False # -> выход из процесса этой сцены
        self.new_scene = None # -> переход на прошлую сцену
        return self.game.game_map.save_game_map(self.game, num)

