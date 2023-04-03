from units.common import *
from pygame.locals import *

EXIT = 0


class App:
    screen = screen_
    rect = pg.Rect((0, 0), WSIZE)

    def __init__(self, scene=None):
        self.clock = pg.time.Clock()
        self.running = True
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

    def exit(self):
        self.running = False
        if self.scene:
            self.scene.running = False


class Scene(App):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.new_scene = None
        self.display = display_
        self.elapsed_time = 0

    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT
            self.pg_event(event)

    def pg_event(self, event):
        pass

    def main(self):
        self.running = True
        while self.running:
            self.elapsed_time = self.clock.tick(FPS)
            self.pg_events()
            self.update()
        if self.running is EXIT:
            return EXIT
        return self.new_scene

    def set_scene(self, scene):
        self.running = False
        self.new_scene = scene

    def exit(self):
        self.app.exit()


class SceneMenu(Scene):
    def __init__(self, app, ui_cls) -> None:
        super().__init__(app=app)
        self.ui = ui_cls(self)
        self.back_scene = None

    def set_ui(self, ui):
        if ui is not None:
            print(ui)
            self.ui = ui

    def pg_events(self):

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT
            self.ui.pg_event(event)
            self.pg_event(event)

    def update(self):
        self.ui.draw()


class ScenePopupMenu(SceneMenu):
    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                    self.new_scene = self.back_scene
            self.ui.pg_event(event)
            self.pg_event(event)


def make_screenshot(screen: pg.Surface):
    pg.image.save(screen, CWDIR + "/screenshot.png")
