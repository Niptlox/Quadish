import pygame as pg


class UI:
    def __init__(self, app) -> None:
        self.app = app
        self.screen = app.screen
        self.display = self.app.display

    def init_ui(self):
        pass

    def draw(self):
        self.screen.blit(self.display, (0, 0))
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        pass
