from pygame import Vector2

from units.UI.Button import TextButton
from units.UI.ClassUI import SurfaceUI, MultilineEditText, GroupUI, Text
from units.UI.ColorsUI import *
# cell_size берём через класс, а не значением при импорте: он теперь
# зависит от размера окна и меняется при ресайзе (см. refresh_cell_size)
from units.UI.InventoryUI import InventoryUI, InventoryPlayerUI
from units.UI.ItemInMouse import *
from units.common import *


class BlockUI(SurfaceUI):
    def __init__(self, rect):
        super(BlockUI, self).__init__(rect)
        self.block_obj = None
        self.work_rect = self.rect
        self.opened = False

    def set_block(self, block_obj, ):
        self.block_obj = block_obj
        self.opened = True

    def close(self):
        self.opened = False

    def set_work_rect(self, value):
        pass

    def get_draw_rect(self):
        return self.rect

    def get_onscreen_pos(self):
        return self.rect

    def block_update(self, elapsed_time):
        if self.block_obj:
            self.block_obj.update(elapsed_time)

    def pg_event(self, event: pg.event.Event):
        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            self.close()
            return True

    def check_mouse_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            return True

    def relayout(self):
        """Перецентрировать окно блока под новый размер экрана: rect
        считался один раз при создании по SCREEN_SIZE."""
        self.rect.center = SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2


class BlocksUIManger:
    def __init__(self, player):
        self.player = player
        self.blocks_ui = {i: cls(player) for i, cls in BLOCKS_UI.items()}
        self.opened = False

    def set_block(self, block, view=True):
        self.player.inventory.ui.close()
        self.blocks_ui[block.index].set_block(block)

    def set_player(self, player):
        self.player = player
        [block_ui.set_player(player) for block_ui in self.blocks_ui.values()]

    def pg_event(self, event):
        self.opened = False
        for block_ui in self.blocks_ui.values():
            if block_ui.opened:
                self.opened = block_ui
                return block_ui.pg_event(event)

    def draw(self, display):
        for block_ui in self.blocks_ui.values():
            if block_ui.opened:
                # if block_ui.index in CLASS_UPDATING_TILES_IN_UI:
                #     block_ui.block_update(elapsed_time * 0.5)
                block_ui.draw(display)
                return True

    def close(self) -> bool:
        if self.opened:
            self.opened.close()
            return True
        return False


class CommandBlockUI(BlockUI):
    background = bg_color
    font = pg.font.Font(CWDIR + "data/fonts/bedstead.otf", 14)
    b_font = pg.font.Font(CWDIR + "data/fonts/bedstead.otf", 20)
    index = 200

    def __init__(self, player):
        rect = pg.Rect(0, 0, SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2 + 10)
        rect.center = SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2
        super(CommandBlockUI, self).__init__(rect)
        self.convert_alpha()
        y = rect.h - 80
        self.code_text = MultilineEditText(pg.Rect(10, 10, rect.w - 20, y), "", self.font, "white",
                                           ui_owner=self, on_finish_typing=self.set_code)
        self.result_text = Text(pg.Rect(10, y + 15, rect.w - 20, 23), "", self.font, "white",)
        self.button_run = TextButton(lambda _: self.run_code(), pg.Rect(10, y + 45, 200, 26), "Запустить",
                                     font=self.b_font,
                                     screenXY=Vector2(self.get_onscreen_pos().topleft) + Vector2(10, y + 45))
        self.components_ui = GroupUI([self.code_text, self.button_run, self.result_text])

    def set_block(self, obj):
        super().set_block(obj)
        self.code_text.set_text(obj.code)

    def run_code(self):
        # if self.block_obj:
        self.block_obj.set_code(self.code_text.get_text())
        result = self.block_obj.run_code()
        self.result_text.set_text(str(result))

    def set_code(self, text):
        if self.block_obj:
            self.block_obj.set_code(text)

    def draw(self, surface):
        self.fill(self.background)
        self.components_ui.draw(self)
        surface.blit(self, self.rect)

    def pg_event(self, event: pg.event.Event):
        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            self.close()
            return True
        return self.components_ui.pg_event(event) or self.check_mouse_event(event)


class ChestUI(InventoryUI, BlockUI):
    def __init__(self):
        super(ChestUI, self).__init__(None, Chest_size_table)

    def set_chest_inventory(self, chest_inventory):
        self.inventory = chest_inventory
        self.redraw_table_inventory()

    def set_block(self, block_obj):
        self.set_chest_inventory(block_obj.inventory)


class _ChestUI(BlockUI):
    def __init__(self):
        self.inventory_ui = InventoryUI(None, Chest_size_table, ui_owner=self)
        super(_ChestUI, self).__init__(self.inventory_ui.rect)

    def set_chest_inventory(self, chest_inventory):
        self.inventory_ui.inventory = chest_inventory
        self.inventory_ui.redraw_table_inventory()

    def set_block(self, block_obj):
        super().set_block(block_obj)
        self.set_chest_inventory(block_obj.inventory)

    def pg_event(self, event: pg.event.Event):
        return super().pg_event(event) or self.inventory_ui.pg_event(event) or self.check_mouse_event(event)

    def draw(self, surface):
        return self.inventory_ui.draw(surface)

    def set_work_rect(self, value):
        self.inventory_ui.set_work_rect(value)


class FurnaceUI(BlockUI):
    background = bg_color

    def __init__(self):
        rect = pg.Rect(0, 0, InventoryUI.cell_size * 6, InventoryUI.cell_size * 4)
        super(FurnaceUI, self).__init__(rect)
        self.convert_alpha()
        self.input_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.input_inventory_ui.get_draw_rect().topleft = InventoryUI.cell_size * 0.5, InventoryUI.cell_size * 0.5
        self.fuel_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.fuel_inventory_ui.get_draw_rect().topleft = InventoryUI.cell_size * 0.5, InventoryUI.cell_size * 2.5
        self.result_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.result_inventory_ui.get_draw_rect().topleft = InventoryUI.cell_size * 4.5, InventoryUI.cell_size * 1.5
        self.inventories = self.input_inventory_ui, self.fuel_inventory_ui, self.result_inventory_ui
        self._work_rect = None

    def set_work_rect(self, value):
        for inv in self.inventories:
            inv.work_rect = value

    def draw(self, surface):
        self.fill(self.background)
        for inv in self.inventories:
            inv.draw(self)
        h = int(self.block_obj.progress * (InventoryUI.cell_size - 4))
        if h:
            x, y = self.input_inventory_ui.get_draw_rect().bottomleft
            pg.draw.rect(self, (255, 255, 255, 200), (x + 2, y - h - 2, 5, h))
        surface.blit(self, self.rect)

    def set_block(self, block_obj):
        super(FurnaceUI, self).set_block(block_obj)
        self.input_inventory_ui.inventory = block_obj.input_cell
        self.fuel_inventory_ui.inventory = block_obj.fuel_cell
        self.result_inventory_ui.inventory = block_obj.result_cell

    def pg_event(self, event: pg.event.Event):
        if super().pg_event(event):
            return True
        res = False
        for inv in self.inventories:
            res = inv.pg_event(event) or res
        return res or self.check_mouse_event(event)


# Player inventory with Blocks


class InventoryPlayerWithBlockUI(BlockUI):
    def __init__(self, player, block_ui: BlockUI):
        super(InventoryPlayerWithBlockUI, self).__init__(((0, 0), SCREEN_SIZE))
        self.player_inventory_ui = InventoryPlayerUI(player.inventory)
        self.player_inventory_ui.opened = True
        self.player_inventory_ui.table_inventory.rect.y = 100

        self.block_ui = block_ui
        self.block_ui.get_draw_rect().y = self.player_inventory_ui.table_inventory.rect.bottom + 40
        self.block_ui.get_draw_rect().centerx = self.player_inventory_ui.table_inventory.rect.centerx

        self.work_rect = pg.Rect.union(self.block_ui.work_rect, self.player_inventory_ui.work_rect)
        self.block_ui.set_work_rect(self.work_rect)
        self.player_inventory_ui.set_work_rect(self.work_rect)
        set_obj_mouse(None)
        self.opened = False

    def set_block(self, block_obj, view=True):
        self.block_ui.set_block(block_obj)
        if view:
            self.player_inventory_ui.opened = True
            self.opened = True

    def block_update(self, elapsed_time):
        self.block_ui.block_update(elapsed_time)

    def draw(self, surface):
        self.block_ui.draw(surface)
        self.player_inventory_ui.draw(surface)
        if get_obj_mouse():
            mx, my = pg.mouse.get_pos()
            self.blit(get_obj_mouse().sprite, (mx, my))
        self.opened = self.player_inventory_ui.opened

    def pg_event(self, event: pg.event.Event):
        super().pg_event(event)
        res = self.player_inventory_ui.pg_event(event)
        res = self.block_ui.pg_event(event) or res
        return res

    def set_player(self, player):
        self.player_inventory_ui.inventory = player.inventory

    def relayout(self):
        """Пересобрать раскладку «инвентарь + блок» и общую рабочую область.

        work_rect — объединение двух областей; по нему проверяется, выкинут
        ли предмет мимо интерфейса, поэтому его тоже надо пересчитать,
        иначе после ресайза предметы будут выпадать из рук."""
        self.set_size(tuple(SCREEN_SIZE))
        self.rect.topleft = (0, 0)
        self.player_inventory_ui.relayout()
        self.player_inventory_ui.table_inventory.rect.y = 100
        if hasattr(self.block_ui, "relayout"):
            self.block_ui.relayout()
        self.block_ui.get_draw_rect().y = self.player_inventory_ui.table_inventory.rect.bottom + 40
        self.block_ui.get_draw_rect().centerx = self.player_inventory_ui.table_inventory.rect.centerx
        self.work_rect = pg.Rect.union(self.block_ui.work_rect, self.player_inventory_ui.work_rect)
        self.block_ui.set_work_rect(self.work_rect)
        self.player_inventory_ui.set_work_rect(self.work_rect)

    def close(self):
        self.player_inventory_ui.opened = False
        self.opened = False


class InventoryPlayerChestUI(InventoryPlayerWithBlockUI):
    index = 129

    def __init__(self, player):
        super(InventoryPlayerChestUI, self).__init__(player, ChestUI())


class InventoryPlayerFurnaceUI(InventoryPlayerWithBlockUI):
    index = 131

    def __init__(self, player):
        super(InventoryPlayerFurnaceUI, self).__init__(player, FurnaceUI())


class MusicBlockUI(BlockUI):
    """Одна ячейка — какой предмет положен, такая нота играет (см.
    MusicBlock в units/Objects/TileClasses.py)."""
    background = bg_color

    def __init__(self):
        rect = pg.Rect(0, 0, InventoryUI.cell_size * 2, InventoryUI.cell_size * 2)
        super().__init__(rect)
        self.convert_alpha()
        self.slot_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.slot_ui.get_draw_rect().topleft = InventoryUI.cell_size * 0.5, InventoryUI.cell_size * 0.5

    def set_work_rect(self, value):
        self.slot_ui.work_rect = value

    def draw(self, surface):
        self.fill(self.background)
        self.slot_ui.draw(self)
        surface.blit(self, self.rect)

    def set_block(self, block_obj):
        super().set_block(block_obj)
        self.slot_ui.inventory = block_obj.inventory

    def pg_event(self, event: pg.event.Event):
        if super().pg_event(event):
            return True
        return self.slot_ui.pg_event(event) or self.check_mouse_event(event)


class InventoryPlayerMusicBlockUI(InventoryPlayerWithBlockUI):
    index = 221

    def __init__(self, player):
        super().__init__(player, MusicBlockUI())


class RadioBlockUI(BlockUI):
    """4 ячейки (2x2) — комбинация предметов задаёт "частоту" рации, общая
    UI для Приёмника и Передатчика (units/Objects/TileClasses.py)."""
    background = bg_color

    def __init__(self):
        rect = pg.Rect(0, 0, InventoryUI.cell_size * 3, InventoryUI.cell_size * 3)
        super().__init__(rect)
        self.convert_alpha()
        self.slots_ui = InventoryUI(None, [2, 2], margin_table=0, ui_owner=self)
        self.slots_ui.get_draw_rect().topleft = InventoryUI.cell_size * 0.5, InventoryUI.cell_size * 0.5

    def set_work_rect(self, value):
        self.slots_ui.work_rect = value

    def draw(self, surface):
        self.fill(self.background)
        self.slots_ui.draw(self)
        surface.blit(self, self.rect)

    def set_block(self, block_obj):
        super().set_block(block_obj)
        self.slots_ui.inventory = block_obj.inventory

    def pg_event(self, event: pg.event.Event):
        if super().pg_event(event):
            return True
        return self.slots_ui.pg_event(event) or self.check_mouse_event(event)


class InventoryPlayerReceiverUI(InventoryPlayerWithBlockUI):
    index = 222

    def __init__(self, player):
        super().__init__(player, RadioBlockUI())


class InventoryPlayerTransmitterUI(InventoryPlayerWithBlockUI):
    index = 223

    def __init__(self, player):
        super().__init__(player, RadioBlockUI())


class LoreTabletUI(BlockUI):
    """Чтение плиты с надписью (сюжет, см. docs/STORY.md).

    Текст берётся у самого блока, а не хранится здесь: одна и та же плита
    в разных структурах несёт разные надписи (units/Lore.py)."""
    index = 300
    font_title = pg.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 22)
    font_line = pg.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 17)
    font_hint = pg.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 14)
    panel_bg = (39, 39, 42, 235)
    accent = "#FDE047"
    text_color = "#E7E5E4"
    hint_color = "#A1A1AA"

    def __init__(self, player):
        w = min(560, SCREEN_SIZE[0] - 40)
        h = min(320, SCREEN_SIZE[1] - 40)
        rect = pg.Rect(0, 0, w, h)
        rect.center = SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2
        super().__init__(rect)
        self.convert_alpha()
        self.player = player
        self.title, self.lines = "", []

    def set_player(self, player):
        self.player = player

    def set_block(self, block_obj):
        super().set_block(block_obj)
        self.title, self.lines = block_obj.inscription()

    def draw(self, surface):
        self.fill((0, 0, 0, 0))
        pg.draw.rect(self, self.panel_bg, ((0, 0), self.rect.size), border_radius=12)
        pg.draw.rect(self, (82, 82, 91), ((0, 0), self.rect.size), width=1, border_radius=12)
        t = self.font_title.render(get_translated_text(self.title), True, self.accent)
        self.blit(t, (20, 16))
        pg.draw.line(self, self.accent, (20, 46), (self.rect.w - 20, 46))
        y = 58
        for line in self.lines:
            self.blit(self.font_line.render(get_translated_text(line), True, self.text_color), (20, y))
            y += self.font_line.get_height() + 6
        hint = self.font_hint.render(get_translated_text("Esc — закрыть"), True, self.hint_color)
        self.blit(hint, (20, self.rect.h - hint.get_height() - 12))
        surface.blit(self, self.rect)


class LogisticBlockUI(InventoryUI, BlockUI):
    """Инвентарь блока логистики (воронка/дропер): три ячейки в ряд."""
    def __init__(self):
        super().__init__(None, [3, 1])

    def set_block(self, block_obj):
        self.inventory = block_obj.inventory
        self.redraw_table_inventory()


class InventoryPlayerHopperUI(InventoryPlayerWithBlockUI):
    index = 224

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


class InventoryPlayerDropperUI(InventoryPlayerWithBlockUI):
    index = 226

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


class InventoryPlayerFuelEngineUI(InventoryPlayerWithBlockUI):
    index = 228

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


class InventoryPlayerCreativeEngineUI(InventoryPlayerWithBlockUI):
    index = 229

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


class InventoryPlayerSpaceEngineUI(InventoryPlayerWithBlockUI):
    index = 230

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


class InventoryPlayerHellEngineUI(InventoryPlayerWithBlockUI):
    index = 231

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


class InventoryPlayerPortalUI(InventoryPlayerWithBlockUI):
    """Портал настраивается той же 2x2 «частотой», что и рация: одинаковый
    набор предметов в двух порталах и связывает их."""
    index = 232

    def __init__(self, player):
        super().__init__(player, RadioBlockUI())


class InventoryPlayerGolemNestUI(InventoryPlayerWithBlockUI):
    index = 233

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


class InventoryPlayerDustCollectorUI(InventoryPlayerWithBlockUI):
    index = 235

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


class InventoryPlayerChunkLoaderUI(InventoryPlayerWithBlockUI):
    """У прогрузчика чанка появилось топливо (космическая пыль), значит
    ему нужен и интерфейс — раньше это был блок без содержимого."""
    index = 219

    def __init__(self, player):
        super().__init__(player, LogisticBlockUI())


BLOCKS_UI = {cls.index: cls for cls in
             [InventoryPlayerChestUI, InventoryPlayerFurnaceUI, CommandBlockUI, InventoryPlayerMusicBlockUI,
              InventoryPlayerReceiverUI, InventoryPlayerTransmitterUI, LoreTabletUI,
              InventoryPlayerHopperUI, InventoryPlayerDropperUI,
              InventoryPlayerFuelEngineUI, InventoryPlayerCreativeEngineUI,
              InventoryPlayerSpaceEngineUI, InventoryPlayerHellEngineUI,
              InventoryPlayerPortalUI, InventoryPlayerGolemNestUI,
              InventoryPlayerDustCollectorUI, InventoryPlayerChunkLoaderUI]
             }
BLOCKS_UI_SET = set(BLOCKS_UI)
