from units.Items import ItemsTile
from units.common import *
from pygame.locals import *
from pygame import Vector2
from units import Entity
import random


class Creature(Entity.PhiscalObject):
    width, height = TSIZE, TSIZE
    sprite = pg.Surface((width, height))
    max_lives = -1
    # Вещи после смерти [(item_cls, (type_obj, cnt)), (item_cls, params), ...]
    drop_items = []

    def __init__(self, game_map, x, y):
        super().__init__(game_map, x, y, self.width, self.height, use_physics=True, sprite=self.sprite)
        self.lives = self.max_lives
        self.lives_surface = pg.Surface((self.rect.w, 6)).convert_alpha()

    def get_vars(self):
        d = super().get_vars()
        return d

    def update(self, tact):
        self.update_physics()

    def jump(self, y):
        self.physical_vector.y -= y

    def draw(self, surface, pos):
        super().draw(surface, pos)
        if self.lives != self.max_lives:
            self.draw_lives(surface, pos)

    def draw_lives(self, surface, pos_obj):
        self.lives_surface.fill(f"#78716CAA")
        w = int((self.rect.w - 2) * (self.lives / self.max_lives))
        pg.draw.rect(self.lives_surface, "#A3E635AA", ((1, 1), (w, 4)))
        surface.blit(self.lives_surface, (pos_obj[0], pos_obj[1] - 10))

    def kill(self):
        super().kill()
        for item_cls, params in self.drop_items:
            item_cls(self.game, *params)
            x, y = self.rect.topleft
            items = item_cls(self.game, *params,
                             pos=(self.rect.x + random.randint(0, TSIZE - HAND_SIZE), self.rect.y))
            self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(x // TSIZE, y // TSIZE), items)


"#D9F99DAA"


def slime_animation(color, size, reduction_step, count_sprites=3):
    sprites = [pg.Surface((size[0], size[1] + i)).convert_alpha() for i in
               range(0, reduction_step * count_sprites, reduction_step)]
    [spr.fill(color + "AA") for spr in sprites]
    return sprites


class Slime(Creature):
    width, height = TSIZE // 1.3, TSIZE // 1.3 - 6
    reduction_step = 3
    count_sprites = 3
    colors = ['#ADFF2F', '#7FFF00', '#7CFC00', '#00FF00', '#32CD32', '#98FB98', '#90EE90', '#00FA9A', '#00FF7F',
              '#3CB371', '#2E8B57', '#228B22', '#008000', '#006400', '#9ACD32', '#6B8E23', '#808000', '#556B2F',
              '#66CDAA', '#8FBC8F', '#20B2AA', '#008B8B', '#008080']
    max_lives = 20
    drop_items = [(ItemsTile, (51, 2))]

    def __init__(self, game_map, x, y):
        super().__init__(game_map, x, y)
        self.move_direction = 0
        self.move_tact = 0
        self.i_sprite = 0
        self.jump_state = -1
        self.color = random.choice(self.colors)
        self.sprites = slime_animation(self.color, self.rect.size, self.reduction_step)
        self.sprite = self.sprites[0]

    def update(self, tact):
        self.update_physics()
        if self.collisions["bottom"]:
            if self.jump_state == 1:
                self.rect.height += self.reduction_step
                self.rect.y -= self.reduction_step
                self.i_sprite += 1
                if self.i_sprite == self.count_sprites - 1:
                    self.jump_state = 0
            elif self.jump_state == -1:
                self.rect.height -= self.reduction_step
                self.rect.y += self.reduction_step
                self.i_sprite -= 1

                if self.i_sprite <= 0:
                    self.jump_state = 1
            elif self.jump_state == 0:
                self.jump(8)
                self.jump_state = -1

        self.sprite = self.sprites[self.i_sprite]
        self.move_tact -= 1
        if self.move_tact <= 0:
            self.move_tact = random.randint(30, 205)
            self.move_direction = random.randint(-1, 1)
        self.movement_vector.x += self.move_direction * 2
        return True
