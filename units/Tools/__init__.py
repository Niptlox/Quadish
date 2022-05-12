from pprint import pprint

from units.Tools.ToolsPickaxe import *
from units.Tools.ToolsSword import *
from units.Tools.ToolsSummoner import *
from units.Tools.ToolHand import *
from units.Tiles import IDX_TOOLS

# модуль обобщения

class ItemTool(Items):
    class_item = CLS_TOOL
    _Tool = Tool

    def __init__(self, game, pos=(0, 0), _Tool=None, class_item=None):
        if _Tool is not None:
            self._Tool = _Tool
        tool = self._Tool(None)
        if class_item is not None:
            self.class_item = class_item
        super().__init__(game, tool.index, 1, pos)
        self.sprite = tool.sprite
        self.tool = tool

    def set_owner(self, owner):
        self.tool.owner = owner

    def get_vars(self):
        d = super().get_vars()
        d.pop("tool")
        # d["_tool"] = d.pop("tool")
        return d


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


TOOLS_CLASSES = [obj for obj in vars().values() if type(obj) is type and vars(obj).get("index") in IDX_TOOLS]

# items of tools
TOOLS = {Cls_tool.index: lambda game, pos=(0, 0), cls=Cls_tool: ItemTool(game, pos, _Tool=cls,
                                                                         class_item=cls.tool_cls + CLS_TOOL)
         for Cls_tool in TOOLS_CLASSES}
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
pprint(TOOLS)