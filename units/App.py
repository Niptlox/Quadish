from units.common import *
from pygame.locals import *
import pygame as pg

EXIT = 0

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

