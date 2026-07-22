import math
from time import time

from pygame import Vector2

from units.Tiles import tile_many_imgs
from units.common import *


class AnimationTool:
    def __init__(self, tool):
        self.tool = tool
        self.animation = False
        self.sprite = tool.sprite

    def draw(self, surface, x, y):
        if self.animation:
            surface.blit(self.sprite, (x, y))

    def update(self):
        pass

    def start(self):
        self.animation = True

    def end(self):
        self.animation = False


class AnimationSword(AnimationTool):
    def __init__(self, tool):
        super().__init__(tool)
        self.rotate = 0
        self.rotate_speed = 8 * max(2, tool.speed)
        self.rotate_end = 180
        self.set_sprite(tool.sprite)

    def start(self):
        super().start()
        self.rotate = -50
        self.flip = self.tool.flip

    def set_sprite(self, sprite: pg.Surface):
        w, h = sprite.get_size()

        surf = pg.Surface((w * 2, h * 2)).convert_alpha()
        surf.fill((0, 0, 0, 0))
        surf.blit(sprite, (w, 0))
        self.sprite = pygame.transform.scale(surf, (w * 3, h * 3))

    def draw(self, surface, x, y):
        if self.animation:
            imgs = tile_many_imgs[self.tool.index]
            img = imgs[int(self.rotate / 360 * len(imgs))]
            new_xy = x - img.get_width() // 2, y - img.get_height() // 2
            img = pygame.transform.flip(img, self.flip, False)
            surface.blit(img, new_xy)

    def update(self):
        if self.animation:
            self.rotate = (self.rotate + self.rotate_speed)
            if self.rotate > self.rotate_end:
                self.end()


class AnimationHand(AnimationTool):
    """Рука: всегда видна в покое, при действии плавно взмахивает к цели.

    Взмах привязан ко времени (не к кадрам) и идёт по синусу 0→1→0, поэтому
    он мягкий и совпадает с моментом действия (start())."""
    rest_dist = TSIZE * 0.45
    reach_dist = TSIZE * 0.95
    duration = 0.16  # секунд на взмах

    def __init__(self, tool):
        super().__init__(tool)
        self.start_time = -10

    def start(self):
        super().start()
        self.start_time = time()

    def draw(self, surface, x, y):
        if not self.sprite:
            return
        t = (time() - self.start_time) / self.duration
        if self.animation and 0.0 <= t <= 1.0:
            ease = math.sin(math.pi * t)  # плавно вперёд и назад
        else:
            self.animation = False
            ease = 0.0
        dist = self.rest_dist + (self.reach_dist - self.rest_dist) * ease
        vec: Vector2 = Vector2(self.tool.vector_to_mouse)
        if vec.x == vec.y == 0:
            vec = Vector2(dist * (-1 if self.tool.flip else 1), 0)
        else:
            vec.scale_to_length(dist)
        vec -= Vector2(self.sprite.get_width() // 2, self.sprite.get_height() // 2)
        surface.blit(self.sprite, (x + int(vec.x), y + int(vec.y)))

    def update(self):
        pass
