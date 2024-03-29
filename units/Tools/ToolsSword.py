from units.Tools.Tools import *


class ToolSword(Tool):
    tool_cls = CLS_WEAPON + CLS_SWORD
    damage = 12
    speed = 2
    distance = 1.5 * TSIZE
    Animation = AnimationSword
    discard_distance = 10
    index = 501
    sprite = tile_imgs[index]
    reload_half_time_cof = 0.5

    def __init__(self, owner):
        super().__init__(owner)
        self.reload_half_time = self.reload_time * self.reload_half_time_cof
        self.action_rect = pg.Rect((0, 0, self.distance, self.distance * 2 - 1))
        self.process_percent = 0

    def left_button(self, vector_to_mouse):
        if time() < self.reload_time + self.last_action_time:
            return False
        self.last_action_time = time()
        self.action = True
        self.animation.start()
        return True

    def update(self, vector_to_mouse):
        super().update(vector_to_mouse)
        if self.action:
            self.process_percent = (time() - self.last_action_time) / self.reload_half_time
            if time() >= self.reload_half_time + self.last_action_time:
                self.punch()
        else:
            t = time() - (self.last_action_time + self.reload_half_time)
            self.process_percent = t / (self.reload_time - self.reload_half_time) if t > 0 else 0

    def punch(self):
        # смещение удара в ту сторону куда смотрит мышь
        self.action_rect.centery = self.owner.rect.centery
        if self.flip:
            self.action_rect.right = self.owner.rect.centerx
        else:
            self.action_rect.left = self.owner.rect.centerx
        for tile in self.owner.game.screen_map.dynamic_tiles:
            if tile.class_obj == OBJ_CREATURE:
                if self.action_rect.colliderect(tile):
                    # if obj killed
                    if (not tile.damage(self.damage)) and self.owner.class_obj & OBJ_PLAYER:
                        self.owner.achievements.add_murder(tile)
                    disc_vector = [0, 0]
                    if tile.rect.x != self.owner.rect.x:
                        disc_vector[0] += self.discard_distance * (-1 if self.flip else 1)
                    if tile.rect.y != self.owner.rect.y:
                        disc_vector[1] += self.discard_distance * (
                            1 if tile.rect.centery > self.owner.rect.bottom else -1) // 2
                    tile.discard(disc_vector)
        self.action = False
        # время окончания удара уже подошло


class ToolGoldSword(ToolSword):
    damage = 777
    speed = 7
    distance = 7 * TSIZE
    Animation = AnimationSword
    discard_distance = 10
    index = 502
    sprite = tile_imgs[index]


class ToolPoisonSword(ToolSword):
    damage = 25
    speed = 2.5
    distance = 2 * TSIZE
    Animation = AnimationSword
    discard_distance = 5
    index = 503
    sprite = tile_imgs[index]
