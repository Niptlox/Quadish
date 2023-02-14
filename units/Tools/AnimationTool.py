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


class AnimationHand(AnimationTool):
    distance_norm = TSIZE * 0.7
    distance_start = TSIZE * 0.6
    max_distance = TSIZE * 1
    speed = 1

    def __init__(self, tool):
        super().__init__(tool)
        self.dist = self.distance_norm
        self.direction = 1

    def start(self):
        super().start()
        self.dist = self.distance_start
        self.direction = 1

    def draw(self, surface, x, y):
        if self.sprite:
            vec: Vector2 = Vector2(self.tool.vector_to_mouse)
            dist = self.distance_start + (self.max_distance - self.distance_start) * self.tool.process_percent
            if vec.x == vec.y == 0:
                vec = Vector2(dist, 0)
            else:
                vec.scale_to_length(dist)
            vec -= Vector2(HAND_SIZE // 2, HAND_SIZE // 2)
            surface.blit(self.sprite, (x + int(vec.x), y + int(vec.y)))

    def update(self):
        pass
        # if self.animation:
        #     self.dist += self.speed * self.direction
        #     if self.dist >= self.max_distance:
        #         self.direction *= -1
        #     elif self.dist <= self.distance_norm:
        #         self.animation = False
        #         self.dist = self.distance_norm


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
    distance_norm = TSIZE * 0.7
    distance_start = TSIZE * 0.6
    max_distance = TSIZE * 1
    speed = 1

    def __init__(self, tool):
        super().__init__(tool)
        self.dist = self.distance_norm
        self.direction = 1

    def start(self):
        super().start()
        self.dist = self.distance_start
        self.direction = 1

    def draw(self, surface, x, y):
        if self.sprite:
            vec: Vector2 = Vector2(self.tool.vector_to_mouse)
            if vec.x == vec.y == 0:
                vec = Vector2(self.dist, 0)
            else:
                vec.scale_to_length(self.dist)
            vec -= Vector2(HAND_SIZE // 2, HAND_SIZE // 2)
            surface.blit(self.sprite, (x + int(vec.x), y + int(vec.y)))

    def update(self):
        if self.animation:
            self.dist += self.speed * self.direction
            if self.dist >= self.max_distance:
                self.direction *= -1
            elif self.dist <= self.distance_norm:
                self.animation = False
                self.dist = self.distance_norm
