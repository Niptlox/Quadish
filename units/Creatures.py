import random
from time import time

from units.Animation import get_death_animation
from units.Entity import PhysicalObject
from units.Items import ItemsTile
from units.Particle import TextParticle, DamageParticle
from units.common import *


def checking_abyss(pos, game_map, height_of_abyss=3, convert_to_tile_pos=False):
    """Проверка на пропасть (не считая tile_pos)"""
    if convert_to_tile_pos:
        tx, _ty = pos[0] // TSIZE, (pos[1] - 3) // TSIZE
    else:
        tx, _ty = pos
    for ty in range(_ty + 1, _ty + height_of_abyss + 1):
        if game_map.get_static_tile_type(tx, ty):
            return False
    return True


class Creature(PhysicalObject):
    not_save_vars = PhysicalObject.not_save_vars | {"lives_surface", }
    bio_kingdom = KINGDOM_CREATURAE
    bio_species = "creature"
    bio_subspecies = "ordinary creature"
    class_obj = OBJ_CREATURE
    width, height = TSIZE, TSIZE
    sprite = pg.Surface((width, height))
    max_lives = -1
    # Вещи после смерти [(item_cls, (type_obj, cnt)), (item_cls, params), ...]
    drop_items = []
    enemy = False
    punch_damage = 0
    punch_speed = 1
    punch_discard = 0

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos[0], pos[1], self.width, self.height, use_physics=True, sprite=self.sprite)
        self.lives = self.max_lives
        self.lives_surface = pg.Surface((self.rect.w, 6)).convert_alpha()
        self.punch_reload_time = 1 / self.punch_speed
        self.last_punch_time = 0
        self.death_animation = get_death_animation(self.rect.size)

    def update(self, tact):
        self.update_physics()
        if self.enemy:
            if self.rect.colliderect(self.game.player.rect):
                if time() > self.punch_reload_time + self.last_punch_time:
                    self.last_punch_time = time()
                    self.game.player.damage(self.punch_damage)

    def jump(self, y):
        self.physical_vector.y -= y

    def draw(self, surface, pos):
        super().draw(surface, pos)
        self.death_animation.update()
        self.death_animation.draw(surface, pos)
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
            x, y = self.rect.x + random.randint(0, TSIZE - HAND_SIZE), self.rect.y
            idx, count = params
            items = item_cls(self.game, index=idx, count=count,
                             pos=(x, y))
            self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(x // TSIZE, y // TSIZE), items)

    def damage(self, lives):
        lives = min(lives, self.lives)
        particle = DamageParticle(self.game, (self.rect.centerx, self.rect.top-25), (lives))
        self.game_map.add_particle(particle)
        self.death_animation.start()
        return super(Creature, self).damage(lives)


class MovingCreature(Creature):
    height_of_abyss = 3
    width_of_abyss = 2

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.move_direction = 0
        self.move_tact = 0

    def check_abyss(self):
        x, y = self.rect.bottomleft
        left_abyss = True
        for i in range(self.width_of_abyss):
            left_abyss = left_abyss and checking_abyss((x, y), self.game_map, height_of_abyss=self.height_of_abyss,
                                                       convert_to_tile_pos=True)
            x -= TSIZE
        x, y = self.rect.bottomright
        right_abyss = True
        for i in range(self.width_of_abyss):
            right_abyss = right_abyss and checking_abyss((x, y), self.game_map, height_of_abyss=self.height_of_abyss,
                                                         convert_to_tile_pos=True)
            x += TSIZE
        if left_abyss and right_abyss:
            pass
        elif left_abyss:
            self.move_direction = 1
        elif right_abyss:
            self.move_direction = -1


"#D9F99DAA"


def slime_animation(color, size, reduction_step, count_sprites=3):
    size = max(size[0], 1), max(size[1], 1)

    sprites = [pg.Surface((size[0], size[1] + i)).convert_alpha() for i in
               range(0, reduction_step * count_sprites, reduction_step)]
    [spr.fill(color + "AA") for spr in sprites]
    [pg.draw.rect(spr, color + "EE", ((0, 0), spr.get_size()), width=2) for spr in sprites]

    return sprites


class Slime(MovingCreature):
    not_save_vars = MovingCreature.not_save_vars | {"sprites", "sprite", "lives_surface"}
    width, height = max(1, TSIZE // 1.3), max(1, TSIZE // 1.3 - 6)
    bio_kingdom = KINGDOM_CREATURAE
    bio_species = "slime"
    bio_subspecies = "ordinary slime"
    reduction_step = 3
    count_sprites = 3
    colors = ['#ADFF2F', '#7FFF00', '#7CFC00', '#00FF00', '#32CD32', '#98FB98', '#90EE90', '#00FA9A', '#00FF7F',
              '#3CB371', '#2E8B57', '#228B22', '#008000', '#006400', '#9ACD32', '#6B8E23', '#808000', '#556B2F',
              '#66CDAA', '#8FBC8F', '#20B2AA', '#008B8B', '#008080']
    color_hard = "#E11D48"
    max_lives_hard = 150
    punch_damage_hard = 15
    max_lives = 20
    drop_items = [(ItemsTile, (51, (1, 3)))]
    jump_speed = 8
    move_speed = 2
    height_of_abyss = 4
    width_of_abyss = 1

    enemy = True
    punch_damage = 5
    punch_speed = 1
    punch_discard = 0

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        x, y = pos
        self.i_sprite = 0
        self.jump_state = -1
        self.color = random.choice(self.colors)
        if random.randint(0, 100) < 5:
            # SLIME BOSS
            self.color = self.color_hard
            self.max_lives = self.max_lives_hard
            self.lives = self.max_lives_hard
            self.punch_damage = self.punch_damage_hard
            self.width, self.height = TSIZE * 2, TSIZE * 2 - 8
            self.jump_speed = 12
            self.reduction_step = 6
            self.move_speed = 4
            self.drop_items = [(ItemsTile, (51, (10, 15))), (ItemsTile, (63, (0, 2))), (ItemsTile, (66, (0, 1)))]
            super().__init__(game, (x, y))

        self.sprites = slime_animation(self.color, self.rect.size, self.reduction_step)
        self.sprite = self.sprites[0]

    def set_vars(self, vrs):
        super(Slime, self).set_vars(vrs)
        self.sprites = slime_animation(self.color, (self.width, self.height), self.reduction_step)
        self.sprite = self.sprites[self.i_sprite]
        self.lives_surface = pg.Surface((self.width, 6)).convert_alpha()

    def update(self, tact):
        super().update(tact)
        self.death_animation.set_resize(self.rect.size)
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
                self.jump(self.jump_speed)
                self.jump_state = -1

        self.sprite = self.sprites[self.i_sprite]
        if self.move_tact is not None:
            self.move_tact -= 1
            if self.move_tact <= 0:
                self.move_tact = random.randint(30, 205)
                self.move_direction = random.randint(-1, 1)
        self.check_abyss()
        self.movement_vector.x += self.move_direction * self.move_speed
        return True


class Cow(MovingCreature):
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "cow"
    bio_subspecies = "white cow"
    width, height = int(TSIZE * 1), int(TSIZE * 0.8)
    colors = ["#FFFAFA", "#FAEBD7", "#FDF4E3", "#FAF0E6"]
    max_lives = 20
    drop_items = [(ItemsTile, (52, (1, 2)))]
    move_speed = 2

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.color = random.choice(self.colors)
        self.sprite = pg.Surface((self.rect.w, self.rect.h))
        self.sprite.fill(self.color)
        self.jump_speed = 7

    def update(self, tact):
        self.update_physics()
        # if self.collisions["bottom"]:
        self.check_abyss()
        self.movement_vector.x += self.move_direction * self.move_speed
        if self.collisions["bottom"] and (self.collisions["left"] or self.collisions["right"]):
            self.jump(self.jump_speed)
        self.move_tact -= 1
        if self.move_tact <= 0:
            self.move_tact = random.randint(30, 205)
            self.move_direction = random.randint(-1, 1)
        return True


class Wolf(MovingCreature):
    not_save_vars = MovingCreature.not_save_vars | {"angry_player", "angry"}
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "wolf"
    bio_subspecies = "gray wolf"
    width, height = int(TSIZE * 1), int(TSIZE * 0.9)

    color = "#708090"
    max_lives = 35
    drop_items = [(ItemsTile, (56, (1, 3))), (ItemsTile, (58, (1)))]

    move_speed = 3.5
    jump_speed = 8

    enemy = True
    punch_damage = 8
    punch_speed = 3
    punch_discard = 8

    # агриться ли сейчас на игрока
    angry_rect_size = (int(TSIZE * 19), int(TSIZE * 19))
    move_speed_angry = 6

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = pg.Surface((self.rect.w, self.rect.h))
        self.sprite.fill(self.color)
        self.angry_rect = pg.Rect((0, 0), self.angry_rect_size)
        self.angry = False

        self.angry_player = None

    def update(self, tact):
        super().update(tact)
        self.check_abyss()
        if self.angry:
            self.movement_vector.x += self.move_direction * self.move_speed_angry
        else:
            self.movement_vector.x += self.move_direction * self.move_speed
        if self.collisions["bottom"] and (self.collisions["left"] or self.collisions["right"]):
            self.jump(self.jump_speed)

        if self.angry:
            if self.angry_player.rect.x > self.rect.x:
                self.move_direction = 1
            else:
                self.move_direction = -1

            self.angry_rect.center = self.rect.center
            if not self.angry_rect.colliderect(self.angry_player):
                self.angry = False
                self.angry_player = None
        else:
            self.move_tact -= 1
            if self.move_tact <= 0:
                self.move_tact = random.randint(30, 205)
                self.move_direction = random.randint(-1, 1)

            self.angry_rect.center = self.rect.center
            if self.angry_rect.colliderect(self.game.player.rect):
                self.angry = True
                self.angry_player = self.game.player
                self.move_tact = 0

        return True


class Snake(Wolf):
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "snake"
    bio_subspecies = "green snake"
    width, height = int(TSIZE * 1), int(TSIZE * 0.1)
    color = "#4d7c0f"
    drop_items = [(ItemsTile, (401, (1, 2))), (ItemsTile, (301, (0, 1)))]


class SlimeBigBoss(Slime):
    bio_subspecies = "huge slime"
    colors = ["#ff9d00"]
    max_lives = 250
    lives = 250
    punch_damage = 35
    width, height = TSIZE * 3, TSIZE * 3 - 15
    reduction_step = 12
    jump_speed = 12
    move_speed = 4
    height_of_abyss = 9
    width_of_abyss = 3
    drop_items = [(ItemsTile, (51, (20, 30))), (ItemsTile, (63, (3, 5))), (ItemsTile, (66, (2, 3))),
                  (ItemsTile, (55, (0, 1)))]

    # агриться ли сейчас на игрока
    angry = False
    angry_rect_size = (int(TSIZE * 19), int(TSIZE * 19))
    move_speed_angry = 6
    angry_player = None

    def __init__(self, game, pos=(0, 0)):
        super(SlimeBigBoss, self).__init__(game, pos)
        self.angry_rect = pg.Rect((0, 0), self.angry_rect_size)

    def update(self, tact):
        super(SlimeBigBoss, self).update(tact)
        self.angry_rect.center = self.rect.center

        if self.angry:
            if self.angry_player.rect.x > self.rect.x:
                self.move_direction = 1
            else:
                self.move_direction = -1
            if not self.angry_rect.colliderect(self.angry_player):
                self.angry = False
                self.angry_player = None
                self.move_tact = 0
        else:
            if self.angry_rect.colliderect(self.game.player.rect):
                self.angry = True
                self.angry_player = self.game.player
                self.move_tact = None


CREATURES = [Creature, Slime, Cow, Wolf, SlimeBigBoss, Snake]
