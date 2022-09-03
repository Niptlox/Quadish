from units.Tiles import Pickaxes_capability
from units.Tools.ToolsPickaxe import *


class ToolSpatula(ToolPickaxe):
    tool_cls = CLS_WEAPON + CLS_SPATULA
    strength = 20  # dig
    damage = 8  # punch
    speed = 2
    distance = 1.5 * TSIZE  # punch
    discard_distance = 6  # отбрасывание
    index = 581
    sprite = tile_imgs[index]
    dig_distance = 3 * TSIZE
    dig_distance2 = dig_distance ** 2
    dig_level = 10
    capability = Pickaxes_capability[index]

