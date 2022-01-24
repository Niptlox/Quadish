from units.common import *
from pygame.locals import *
from pygame import Vector2
from units import Entitys
import random


class Creature(Entitys.PhiscalObject):
    width, height = TSIZE, TSIZE
    sprite = pg.Surface((width, height))

    def __init__(self, game_map, x, y):
        super().__init__(game_map, x, y, self.width, self.height, use_physics=True, sprite=self.sprite)

    def update(self, tact):
        self.update_physics()

    def jump(self, y):
        self.physical_vector.y -= y


class Slime(Creature):
    width, height = TSIZE//1.3, TSIZE//1.3
    sprite = pg.Surface((width, height))
    sprite.fill("#D9F99D")

    def __init__(self, game_map, x, y):
        super().__init__(game_map, x, y)
        self.move_direction = 0
        self.move_tact = 0

    def update(self, tact):
        self.update_physics()
        if self.collisions["bottom"]:
            self.jump(8)
        self.move_tact -= 1
        if self.move_tact <= 0:
            self.move_tact = random.randint(30, 205)
            self.move_direction = random.randint(-1, 1)
        self.movement_vector.x += self.move_direction * 2
        return True
