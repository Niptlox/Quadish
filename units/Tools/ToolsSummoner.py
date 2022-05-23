from units.Tools.ToolsSword import *


class ToolSummon(ToolSword):
    tool_cls = CLS_WEAPON + CLS_COMMON
    damage = 5
    speed = 5
    distance = 2 * TSIZE
    Animation = AnimationHand
    discard_distance = 5
    index = 610
    sprite = tile_imgs[index]
    creatureCls = SlimeBigBoss

    def right_button_click(self, vector_to_mouse: Vector2):
        if super(ToolSummon, self).right_button_click(vector_to_mouse):
            # кликнул по интеракт объекту
            return
        if self.owner.inventory.get_from_inventory(51, 50) and self.owner.inventory.get_from_inventory(66, 1):
            # на боса - 50 слизи и 1 рубин
            vtm = vector_to_mouse
            vp: Vector2 = self.owner.vector  # player
            vcreture = vtm + vp
            creature = self.creatureCls(self.owner.game, vcreture.xy)
            chunk = vcreture // TSIZE // CHUNK_SIZE
            self.owner.game_map.add_dinamic_obj(*chunk.xy, creature)

    def update(self, vector_to_mouse: Vector2):
        self.vector_to_mouse = vector_to_mouse
        super().update(vector_to_mouse)
