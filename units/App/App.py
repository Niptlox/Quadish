import units.common as common
from units.common import *
from pygame.locals import *

EXIT = 0


class App:
    # @property, а не обычный атрибут: после живого ресайза/переключения
    # полноэкранного режима (units.common.apply_resize) pygame создаёт
    # НОВЫЙ Surface — статический класс-атрибут просто держал бы старую,
    # осиротевшую поверхность вместо актуальной.
    @property
    def screen(self):
        return pygame.display.get_surface() or common.screen_

    @property
    def rect(self):
        return pg.Rect((0, 0), tuple(common.SCREEN_SIZE))

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
        # Единая точка входа для живого ресайза/фуллскрина — сюда попадают
        # события ЛЮБОЙ сцены (SceneMenu/ScenePopupMenu/GameScene и т.д.,
        # все они зовут self.pg_event(event) из своего pg_events()), так
        # что F11 и растягивание окна работают одинаково и в меню, и в паузе,
        # и в игре, без правок в каждой сцене по отдельности.
        if event.type == pygame.VIDEORESIZE:
            if not common.FULLSCREEN:
                common.apply_resize((event.w, event.h))
                self._on_screen_changed()
                return True
        elif event.type == KEYDOWN and event.key == K_F11:
            common.apply_resize(fullscreen=not common.FULLSCREEN)
            self._on_screen_changed()
            return True
        return False

    def _on_screen_changed(self):
        ui = getattr(self, "ui", None)
        relayout = getattr(ui, "relayout", None)
        if relayout is not None:
            relayout()

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
            # if event.type == pygame.KEYDOWN:
            #     print("s", event.key, "'"+event.unicode+"'", event.scancode, chr(event.scancode))
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
