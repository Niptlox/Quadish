from pprint import pprint

from units.Items import Items
from units.Tiles import IDX_TOOLS
from units.Tools.ToolHand import *
from units.Tools.ToolsPickaxe import *
from units.Tools.ToolsSummoner import *
from units.Tools.ToolsSword import *
from units.Tools.ToolSpatula import *


# модуль обобщения and items

class ItemTool(Items):
    class_item = CLS_TOOL
    _Tool = Tool
    cell_size = 1

    def __init__(self, game, _Tool_index=0, pos=(0, 0), _Tool=None, class_item=None):
        if _Tool_index is not None:
            self._Tool = TOOLS_CLASSES[_Tool_index]
        elif _Tool is not None:
            self._Tool = _Tool
        tool = self._Tool(None)
        self.class_item += tool.tool_cls
        super().__init__(game, tool.index, pos, 1)
        self.sprite = tool.sprite
        self.tool = tool

    def __copy__(self):
        obj = self.__class__(self.game, self.index, self.rect.topleft)
        return obj

    def set_owner(self, owner):
        self.tool.owner = owner

    def set_vars(self, vrs):
        print(vrs)
        self.tool = vrs.get("_Tool")(None)
        self.sprite = self.tool.sprite
        super().set_vars(vrs)

    def get_vars(self):
        d = super().get_vars()
        d.pop("tool")
        # d["_tool"] = d.pop("tool")
        return d


#
# class ItemSword(ItemTool):
#     class_item = CLS_TOOL + CLS_SWORD
#     _Tool = ToolSword
#
#
# class ItemPickaxe(ItemTool):
#     class_item = CLS_TOOL + CLS_PICKAXE
#     _Tool = ToolPickaxe
#
#
# class ItemSummon(ItemTool):
#     class_item = CLS_TOOL + CLS_COMMON
#     _Tool = ToolSummon
#
#
# class ItemGoldSword(ItemSword):
#     _Tool = ToolGoldSword
#
#
# class ItemGoldPickaxe(ItemPickaxe):
#     _Tool = ToolGoldPickaxe
#
#
# class ItemWoodPickaxe(ItemPickaxe):
#     _Tool = ToolWoodPickaxe
#
#
# class ItemCopperPickaxe(ItemPickaxe):
#     _Tool = ToolCopperPickaxe


TOOLS_CLASSES = {obj.index: obj for obj in vars().values() if type(obj) is type and vars(obj).get("index") in IDX_TOOLS}
TOOLS_CLASSES[0] = Tool
pprint(TOOLS_CLASSES)

# items of tools
TOOLS = {idx: lambda game, idx=idx, pos=(0, 0): ItemTool(game, idx, pos)
         for idx, Cls_tool in TOOLS_CLASSES.items()}
#
# TOOLS = {cls._Tool.index: cls for cls in
#          {
#              ItemSword,
#              ItemGoldSword,
#              ItemPickaxe,
#              ItemGoldPickaxe,
#              ItemWoodPickaxe,
#              ItemCopperPickaxe,
#              ItemSummon
#          }
#          }
