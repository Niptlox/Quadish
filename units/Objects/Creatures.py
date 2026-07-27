import random
from time import time

from units.Graphics.Animation import get_death_animation
from units.Objects.Entity import PhysicalObject
from units.Objects.Items import ItemsTile
from units.Graphics.Particle import DamageParticle
# Спрайты животных — пиксель-арт (сетки нарисованы вручную). Раньше они
# рисовались здесь же примитивами с дробными координатами, из-за чего на
# 16-35 пикселях лапы разъезжались, а сочленения висели в воздухе.
from units.Objects.CreatureSprites import (
    create_cow_sprite, create_wolf_sprite, create_snake_sprite, create_imp_sprite,
    create_scorpion_sprite, create_rabbit_sprite, create_deer_sprite, create_fox_sprite,
    create_camel_sprite, create_penguin_sprite, create_boar_sprite, create_crab_sprite,
    create_bat_sprite, create_golem_sprite, create_space_drifter_sprite,
    create_dust_swarm_sprite, create_void_sentinel_sprite)
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
    not_save_vars = PhysicalObject.not_save_vars | {"lives_surface", "angry_player"}
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

    def update(self, tact, elapsed_time):
        self.update_physics(elapsed_time)
        self.death_animation.update(self.game.elapsed_time)
        if self.enemy:
            if self.rect.colliderect(self.game.player.rect):
                if time() > self.punch_reload_time + self.last_punch_time:
                    self.last_punch_time = time()
                    self.game.player.damage(self.punch_damage)

    def jump(self, y):
        self.physical_vector.y -= y

    def draw(self, surface, pos):
        super().draw(surface, pos)

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
        particle = DamageParticle(self.game, (self.rect.centerx, self.rect.top - 25), (lives))
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

    sprites = []
    for i in range(0, reduction_step * count_sprites, reduction_step):
        w, h = size[0], size[1] + i
        spr = pg.Surface((w, h)).convert_alpha()
        spr.fill((0, 0, 0, 0))
        radius = max(2, min(w, h) // 3)
        pg.draw.rect(spr, color + "AA", (0, 0, w, h), border_radius=radius)
        pg.draw.rect(spr, color + "EE", (0, 0, w, h), width=2, border_radius=radius)
        # блик и "глазки" — придают слаймy характер, а не просто закруглённый блок
        eye_y = h // 3
        eye_r = max(1, w // 12)
        pg.draw.circle(spr, "#1C1917", (w // 3, eye_y), eye_r)
        pg.draw.circle(spr, "#1C1917", (w * 2 // 3, eye_y), eye_r)
        highlight = pg.Surface((max(1, w // 3), max(1, h // 4)), pg.SRCALPHA)
        highlight.fill((255, 255, 255, 70))
        spr.blit(highlight, (w // 5, h // 6))
        sprites.append(spr)

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
    drop_items = [(ItemsTile, (51, (1, 2)))]
    jump_speed = 6
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

        self.is_boss = False
        if random.randint(0, 100) < 2:
            self.init_boss()
            self.lives = self.max_lives_hard

        self.sprites = slime_animation(self.color, self.rect.size, self.reduction_step)
        self.sprite = self.sprites[0]

    def init_boss(self):
        # SLIME BOSS
        self.is_boss = True
        self.color = self.color_hard
        self.max_lives = self.max_lives_hard
        self.punch_damage = self.punch_damage_hard
        self.width, self.height = TSIZE * 2, TSIZE * 2 - 8
        self.jump_speed = 10
        self.reduction_step = 6
        self.move_speed = 4
        self.drop_items = [(ItemsTile, (51, (10, 15))), (ItemsTile, (63, (0, 2))), (ItemsTile, (66, (0, 1)))]
        super().__init__(self.game, self.rect.topleft)

    def set_vars(self, vrs):
        super(Slime, self).set_vars(vrs)
        if self.rect.width > self.width:
            self.is_boss = True
        if self.is_boss:
            self.init_boss()
        self.sprites = slime_animation(self.color, self.rect.size, self.reduction_step)
        self.sprite = self.sprites[self.i_sprite]
        self.lives_surface = pg.Surface((self.rect.width, 6)).convert_alpha()

    def update(self, tact, elapsed_time):
        super().update(tact, elapsed_time)
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
        self.sprite = create_cow_sprite(self.color, self.rect.size)
        self.jump_speed = 5

    def update(self, tact, elapsed_time):
        super().update(tact, elapsed_time)
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
    jump_speed = 5

    enemy = True
    punch_damage = 8
    punch_speed = 3
    punch_discard = 8

    # агриться ли сейчас на игрока
    angry_rect_size = (int(TSIZE * 19), int(TSIZE * 19))
    move_speed_angry = 6

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_wolf_sprite(self.color, self.rect.size)
        self.angry_rect = pg.Rect((0, 0), self.angry_rect_size)
        self.angry = False

        self.angry_player = None

    def update(self, tact, elapsed_time):
        super().update(tact, elapsed_time)
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

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_snake_sprite(self.color, self.rect.size)


class Imp(Wolf):
    """Бес — враждебный житель Ада (спавнится глубоко под START_HELL_Y)."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "imp"
    bio_subspecies = "hell imp"
    immune_tiles = frozenset({140})    # лава — его дом, а не опасность
    width, height = int(TSIZE * 0.9), int(TSIZE * 0.9)
    color = "#DC2626"
    max_lives = 45
    drop_items = [(ItemsTile, (402, (1, 3)))]

    move_speed = 4
    jump_speed = 6

    enemy = True
    punch_damage = 12
    punch_speed = 2
    punch_discard = 6

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_imp_sprite(self.color, self.rect.size)


class Scorpion(Wolf):
    """Скорпион — враждебный житель пустыни, мельче и быстрее волка."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "scorpion"
    bio_subspecies = "desert scorpion"
    width, height = int(TSIZE * 0.7), int(TSIZE * 0.5)
    color = "#D4A373"
    max_lives = 18
    drop_items = [(ItemsTile, (403, (1, 2)))]

    move_speed = 5
    jump_speed = 4

    enemy = True
    punch_damage = 4
    punch_speed = 4
    punch_discard = 3

    angry_rect_size = (int(TSIZE * 12), int(TSIZE * 12))
    move_speed_angry = 7

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_scorpion_sprite(self.color, self.rect.size)


class PassiveWanderer(MovingCreature):
    """Общее поведение мирных бродячих животных (как раньше был написан
    только для Cow): гуляют по поверхности, иногда перепрыгивают
    препятствия, не нападают на игрока."""
    jump_speed = 5

    def update(self, tact, elapsed_time):
        super().update(tact, elapsed_time)
        self.check_abyss()
        self.movement_vector.x += self.move_direction * self.move_speed
        if self.collisions["bottom"] and (self.collisions["left"] or self.collisions["right"]):
            self.jump(self.jump_speed)
        self.move_tact -= 1
        if self.move_tact <= 0:
            self.move_tact = random.randint(30, 205)
            self.move_direction = random.randint(-1, 1)
        return True


class Rabbit(PassiveWanderer):
    """Заяц — мелкое мирное животное, водится почти везде."""
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "rabbit"
    bio_subspecies = "wild rabbit"
    width, height = int(TSIZE * 0.5), int(TSIZE * 0.4)
    colors = ["#E7E5E4", "#A8A29E", "#78716C"]
    max_lives = 8
    drop_items = [(ItemsTile, (405, (1, 1))), (ItemsTile, (404, (0, 1)))]
    move_speed = 3

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.color = random.choice(self.colors)
        self.sprite = create_rabbit_sprite(self.color, self.rect.size)


class Deer(PassiveWanderer):
    """Олень — крупное мирное животное лесов и тундры."""
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "deer"
    bio_subspecies = "forest deer"
    width, height = int(TSIZE * 1.1), int(TSIZE * 1.1)
    colors = ["#A16207", "#92400E", "#78350F"]
    max_lives = 25
    drop_items = [(ItemsTile, (405, (2, 3))), (ItemsTile, (404, (1, 2)))]
    move_speed = 3

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.color = random.choice(self.colors)
        self.sprite = create_deer_sprite(self.color, self.rect.size)


class Fox(PassiveWanderer):
    """Лиса — мелкое мирное животное лесов, быстрая."""
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "fox"
    bio_subspecies = "red fox"
    width, height = int(TSIZE * 0.7), int(TSIZE * 0.5)
    colors = ["#EA580C", "#C2410C"]
    max_lives = 12
    drop_items = [(ItemsTile, (404, (1, 2)))]
    move_speed = 3.5

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.color = random.choice(self.colors)
        self.sprite = create_fox_sprite(self.color, self.rect.size)


class Camel(PassiveWanderer):
    """Верблюд — крупное мирное животное пустыни."""
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "camel"
    bio_subspecies = "desert camel"
    width, height = int(TSIZE * 1.2), int(TSIZE * 1.2)
    color = "#D2B48C"
    max_lives = 22
    drop_items = [(ItemsTile, (405, (2, 3))), (ItemsTile, (404, (1, 2)))]
    move_speed = 2.5
    height_of_abyss = 4

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_camel_sprite(self.color, self.rect.size)


class Penguin(PassiveWanderer):
    """Пингвин — мирное животное тундры/тайги."""
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "penguin"
    bio_subspecies = "arctic penguin"
    width, height = int(TSIZE * 0.5), int(TSIZE * 0.7)
    color = "#1E293B"
    max_lives = 10
    drop_items = [(ItemsTile, (405, (1, 2))), (ItemsTile, (404, (0, 1)))]
    move_speed = 1.5

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_penguin_sprite(self.color, self.rect.size)


class Boar(Wolf):
    """Кабан — агрессивный обитатель лесов."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "boar"
    bio_subspecies = "wild boar"
    width, height = int(TSIZE * 0.9), int(TSIZE * 0.7)
    color = "#44403C"
    max_lives = 30
    drop_items = [(ItemsTile, (405, (2, 3)))]

    move_speed = 3
    jump_speed = 5

    enemy = True
    punch_damage = 10
    punch_speed = 2
    punch_discard = 10

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_boar_sprite(self.color, self.rect.size)


class Crab(Wolf):
    """Краб — мелкий враг у воды."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "crab"
    bio_subspecies = "shore crab"
    width, height = int(TSIZE * 0.6), int(TSIZE * 0.4)
    color = "#DC2626"
    max_lives = 12
    drop_items = [(ItemsTile, (403, (1, 2)))]

    move_speed = 3.5
    jump_speed = 3

    enemy = True
    punch_damage = 3
    punch_speed = 3
    punch_discard = 4

    angry_rect_size = (int(TSIZE * 8), int(TSIZE * 8))

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_crab_sprite(self.color, self.rect.size)


class Bat(Wolf):
    """Летучая мышь — мелкий шустрый враг пещер."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "bat"
    bio_subspecies = "cave bat"
    width, height = int(TSIZE * 0.7), int(TSIZE * 0.45)
    color = "#3F3A36"
    max_lives = 10
    drop_items = [(ItemsTile, (404, (0, 1)))]

    move_speed = 5
    jump_speed = 7

    enemy = True
    punch_damage = 3
    punch_speed = 4
    punch_discard = 2

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_bat_sprite(self.color, self.rect.size)


class StoneGolem(Wolf):
    """Каменный голем — тяжёлый неповоротливый враг глубоких пещер."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "golem"
    bio_subspecies = "stone golem"
    width, height = int(TSIZE * 1.6), int(TSIZE * 1.8)
    color = "#78716C"
    max_lives = 120
    drop_items = [(ItemsTile, (3, (5, 10))), (ItemsTile, (64, (0, 2)))]

    move_speed = 1.2
    jump_speed = 5

    enemy = True
    punch_damage = 20
    punch_speed = 1
    punch_discard = 14

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_golem_sprite(self.color, self.rect.size)


class SpaceDrifter(Wolf):
    """Космический дрейфер — враждебный обитатель космической зоны."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "space_drifter"
    bio_subspecies = "space drifter"
    width, height = int(TSIZE * 0.8), int(TSIZE * 0.8)
    color = "#818CF8"
    max_lives = 40
    drop_items = [(ItemsTile, (408, (1, 3)))]

    move_speed = 4
    jump_speed = 8

    enemy = True
    punch_damage = 10
    punch_speed = 2
    punch_discard = 5

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_space_drifter_sprite(self.color, self.rect.size)


class DustSwarm(Wolf):
    """Пылевой рой — слабый и быстрый обитатель астероидов.

    Основной ручной источник космической пыли: дрейфер бьёт больно и
    редок, а рой можно фармить мечом. С него и начинается космос —
    иначе пылеуловитель нечем было бы оплатить.
    """
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "dust_swarm"
    bio_subspecies = "dust swarm"
    width, height = int(TSIZE * 0.7), int(TSIZE * 0.6)
    color = "#7DD3FC"
    max_lives = 18
    drop_items = [(ItemsTile, (408, (1, 2)))]

    move_speed = 5
    jump_speed = 9

    enemy = True
    punch_damage = 4
    punch_speed = 3
    punch_discard = 3

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_dust_swarm_sprite(self.color, self.rect.size)


class VoidSentinel(Wolf):
    """Пустотный страж — тяжёлый враг глубокого космоса.

    Космический аналог каменного голема: медленный, много бьёт и много
    отдаёт. Держит верхний край сложности, чтобы космос не оказался
    безопаснее пещер только потому, что он новый.
    """
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "void_sentinel"
    bio_subspecies = "void sentinel"
    width, height = int(TSIZE * 1.4), int(TSIZE * 1.7)
    color = "#312E81"
    max_lives = 150
    drop_items = [(ItemsTile, (408, (2, 5))), (ItemsTile, (65, (1, 2))), (ItemsTile, (66, (0, 1)))]

    move_speed = 1.4
    jump_speed = 5

    enemy = True
    punch_damage = 22
    punch_speed = 1
    punch_discard = 15

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_void_sentinel_sprite(self.color, self.rect.size)


class SlimeBigBoss(Slime):
    not_save_vars = Slime.not_save_vars | {"angry", "angry_player"}
    bio_subspecies = "huge slime"
    colors = ["#ff9d00"]
    max_lives = 250
    lives = 250
    punch_damage = 35
    width, height = TSIZE * 3, TSIZE * 3 - 15
    reduction_step = 12
    jump_speed = 10
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

    def update(self, tact, elapsed_time):
        super(SlimeBigBoss, self).update(tact, elapsed_time)
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


CREATURES = [Creature, Slime, Cow, Wolf, SlimeBigBoss, Snake, Imp, Scorpion,
            Rabbit, Deer, Fox, Camel, Penguin, Boar, Crab, Bat, StoneGolem, SpaceDrifter,
            DustSwarm, VoidSentinel]
CREATURES_D = {cls.__name__: cls for cls in CREATURES}


# MODS ==================================================================
def _build_mod_creatures():
    """Собрать классы существ из модов на базе ванильных.

    Классы кладутся и в globals() модуля: сохранение мира пиклит сам класс
    существа (`type(obj)`), а pickle сериализует классы по ссылке
    «модуль + имя» — динамический класс, которого нет в атрибутах модуля,
    просто не восстановился бы при загрузке.
    """
    from units import mods

    built = []
    for spec in mods.mod_creatures():
        base = globals().get(spec["base"])
        if base is None:      # список баз закрыт в mods.py, но подстрахуемся
            continue
        w, h = spec["size"]
        attrs = {
            "__doc__": f"Существо из мода: {spec['name']}",
            "bio_species": spec["id_name"].lower(),
            "bio_subspecies": spec["name"],
            "width": w, "height": h,
            # Wolf-подобные берут строку self.color, Slime-подобные тянут
            # random.choice(self.colors) — задаём оба варианта
            "color": spec["color"],
            "colors": [spec["color"]],
            "max_lives": spec["lives"],
            "enemy": spec["enemy"],
            "punch_damage": spec["damage"],
            "move_speed": spec["speed"],
            "drop_items": [(ItemsTile, (idx, cnt)) for idx, cnt, _ch in spec["drops"]],
            "mod_creature": True,
        }
        cls = type(spec["id_name"], (base,), attrs)
        globals()[spec["id_name"]] = cls
        CREATURES.append(cls)
        CREATURES_D[cls.__name__] = cls
        built.append((cls, spec))
    return built


# [(класс, описание)] — GameMap.random_creature_selection берёт отсюда
# кандидатов на спавн вместе с их зоной/биомами/весом
MOD_CREATURES = _build_mod_creatures()
