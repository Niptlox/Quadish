from units.Tools.ToolsPickaxe import *


class ToolHand(ToolPickaxe):
    tool_cls = CLS_NONE
    damage = 4  # punch
    strength = 8  # dig
    speed = 1.5  # dig
    speed_set = 8  # set tile
    distance = 1.1 * TSIZE  # punch
    dig_distance = 3 * TSIZE
    set_distance = 4 * TSIZE
    dig_distance2 = dig_distance ** 2
    set_distance2 = set_distance ** 2
    capability = [1, 2, 11, 12, 101, 102, 103, 105, 110, 121, 122, 123, 124, 125, 126, 127, 128, 130]
    Animation = AnimationHand
    discard_distance = 5

    def __init__(self, owner):
        super().__init__(owner)
        self.hand_vector = Vector2(0, 0)
        self.last_action_time_set = 0
        self.reload_time_set = 1 / self.speed_set
        self.stroke_rect = pg.Rect((0, 0, TSIZE, TSIZE))
        self.stroke = False
        self.vector_to_mouse = Vector2(0)

    def draw(self, surface, x, y):
        self.animation.sprite = self.owner.hand_img
        super().draw(surface, x, y)

    def right_button(self, vector_to_mouse: Vector2):
        # set tile
        result = False
        vtm = vector_to_mouse
        vp: Vector2 = self.owner.vector  # player
        dist2 = vtm.length_squared()
        if AUTO_BUILD and dist2 > self.set_distance2:
            vtm.scale_to_length(TSIZE)
            dist2 = TSIZE ** 2
        if dist2 <= self.set_distance2:
            v_tile = (vtm + vp) // TSIZE
            x, y = int(v_tile.x), int(v_tile.y)
            game_map = self.owner.game_map
            check = check_set_tile(game_map, x, y, self.owner.inventory[self.owner.inventory.active_cell])
            if check:
                if time() > self.reload_time_set + self.last_action_time_set:
                    self.last_action_time_set = time()
                    self.animation.start()
                    res = set_tile(self.owner, x, y, self.owner.inventory[self.owner.inventory.active_cell], True)
                    if res == 0:
                        self.owner.inventory[self.owner.inventory.active_cell] = None
                    self.owner.choose_active_cell()
                    result = True
                self.stroke_rect.x = x * TSIZE - vp.x
                self.stroke_rect.y = y * TSIZE - vp.y
                self.stroke = True
            else:
                self.stroke = False

        return result

    def update(self, vector_to_mouse: Vector2):
        self.vector_to_mouse = vector_to_mouse
        super().update(vector_to_mouse)
