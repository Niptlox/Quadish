from units.common import *


class Animation:
    def __init__(self, frames, speed=20, looped=False, start_frame=0):
        self.animation = False
        # массив картинок
        self.frames = frames
        self.frame_count = len(self.frames)
        self.frame_index = start_frame
        self.looped = looped
        # кадров в секунду
        self.speed = speed
        # кадров на тик
        self.speed_one_tick = speed / FPS
        self.resize = None

    def draw(self, surface, x, y):
        if self.animation:
            if self.resize:
                surface.blit(pg.transform.scale(self.frames[int(self.frame_index)], self.resize), (x, y))
            else:
                surface.blit(self.frames[int(self.frame_index)], (x, y))

    def set_resize(self, size):
        self.resize = size

    def update(self):
        if self.animation:
            self.frame_index += self.speed_one_tick
            if self.frame_index >= self.frame_count:
                if self.looped:
                    self.frame_index %= self.frame_count
                else:
                    self.stop()

    def start(self):
        self.animation = True

    def pause(self):
        self.animation = False

    def stop(self):
        self.animation = False
        self.frame_index = 0


def get_death_animation(size, color=(185, 28, 28), speed=10, time=1, start_alpha=200):
    count = FPS * time // speed
    arr = []
    for i in range(count):
        surf = pg.Surface(size)
        surf.fill(color)
        surf.set_alpha(start_alpha * i / count)
        arr.append(surf)

    return Animation(arr[::-1], speed=speed, looped=False)
