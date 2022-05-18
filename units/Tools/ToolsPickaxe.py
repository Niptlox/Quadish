from units.Tools.ToolsSword import *


class ToolPickaxe(ToolSword):
    tool_cls = CLS_WEAPON + CLS_PICKAXE
    strength = 20  # dig
    damage = 8  # punch
    speed = 2
    distance = 1.5 * TSIZE  # punch
    Animation = AnimationSword
    discard_distance = 6  # отбрасывание
    index = 531
    sprite = tile_imgs[index]
    dig_distance = 3 * TSIZE
    dig_distance2 = dig_distance ** 2
    capability = [1, 2, 3, 4, 9, 11, 12, 101, 102, 103, 105, 110, 121, 122, 123, 124, 125, 126, 127, 128, 130]

    def __init__(self, owner):
        super().__init__(owner)
        self.stroke_rect = pg.Rect((0, 0, TSIZE, TSIZE))
        self.stroke = False

    def draw(self, surface, x, y):
        super().draw(surface, x, y)
        if self.stroke:
            pg.draw.rect(surface, "#FDE047", ((self.stroke_rect.x + x, self.stroke_rect.y + y), self.stroke_rect.size),
                         width=2)
            self.stroke = False

    def left_button(self, vector_to_mouse: Vector2):
        # dig tile
        result = False
        vtm = vector_to_mouse
        vp: Vector2 = self.owner.vector  # player
        dist2 = vtm.length_squared()
        if AUTO_BUILD and dist2 > self.dig_distance2:
            vtm.scale_to_length(TSIZE)
            dist2 = TSIZE ** 2
        if dist2 <= self.dig_distance2:
            v_tile = (vtm + vp) // TSIZE
            x, y = int(v_tile.x), int(v_tile.y)
            check = check_dig_tile(self.owner.game_map, x, y, self)
            if check:
                if time() > self.reload_time + self.last_action_time:
                    dig_tile(self.owner.game_map, x, y, self, True)
                    result = True
                    self.owner.choose_active_cell()
                self.stroke_rect.x = x * TSIZE - vp.x
                self.stroke_rect.y = y * TSIZE - vp.y
                self.stroke = True
            else:
                self.stroke = False
                # start punch
        if time() > self.reload_time + self.last_action_time:
            self.action = True
            self.flip = vector_to_mouse.x < 0
            self.animation.start()
            self.last_action_time = time()
        return result


class ToolGoldPickaxe(ToolPickaxe):
    strength = 777  # dig
    damage = 777  # punch
    speed = 7
    distance = 7 * TSIZE  # punch
    discard_distance = 17  # отбрасывание
    index = 532
    sprite = tile_imgs[index]
    dig_distance = 77 * TSIZE
    dig_distance2 = dig_distance ** 2
    capability = None


class ToolWoodPickaxe(ToolPickaxe):
    strength = 10  # dig
    damage = 6  # punch
    speed = 1.5
    distance = 1.5 * TSIZE  # punch
    discard_distance = 4  # отбрасывание
    index = 530
    sprite = tile_imgs[index]
    #  capability = [1, 2, 3, 4, 9, 11, 12, 101, 102, 103, 105, 110, 121, 122, 123, 124, 125, 126, 127, 128, 130]


class ToolCopperPickaxe(ToolPickaxe):
    strength = 20  # dig
    damage = 9  # punch
    speed = 1.7
    distance = 1.5 * TSIZE  # punch
    discard_distance = 4  # отбрасывание
    index = 533
    sprite = tile_imgs[index]
    #  capability = [1, 2, 3, 4, 9, 11, 12, 101, 102, 103, 105, 110, 121, 122, 123, 124, 125, 126, 127, 128, 130]

