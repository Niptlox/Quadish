from units.common import *


class Tile(SavedObject):
    not_save_vars = {"game", "game_map"} | SavedObject.not_save_vars
    index = 0
    view_interface_on_click = False

    def __init__(self, game, tile_pos):
        self.id = id(self)
        self.game = game
        self.game_map = game.game_map
        self.tx, self.ty = tile_pos
        self.rect = pg.Rect((self.tx * TSIZE, self.ty * TSIZE), (TSIZE, TSIZE))

    # Сколько игровых тактов продвигает текущий вызов update(). На экране
    # всегда 1, за экраном — столько, сколько прошло с прошлого обслуживания
    # (см. GameMap.tick_offscreen). Блоки со своим счётчиком прибавляют
    # именно steps, поэтому за экраном они дают ту же выработку, что и на
    # экране, независимо от расписания.
    steps = 1

    def items_of_break(self):
        return [(self.index, 1)]

    def tick(self, steps=1, elapsed_time=None):
        """Продвинуть тайл на steps тактов — единая точка для экрана и вне его.

        Раньше блоки логистики сверялись с ГЛОБАЛЬНЫМ тактом
        (`game.tact % PERIOD`), а тик за экраном шёл раз в 30 кадров. Из-за
        этого выработка фермы за экраном зависела от НОК двух периодов:
        замер показал, что при периоде тика 31 вместо 30 воронка складывала
        в сундук втрое меньше. Теперь блок считает свои такты сам.
        """
        self.steps = steps
        if elapsed_time is None:
            elapsed_time = steps * (1000 / FPS)
        return self.update(elapsed_time)

    def update(self, elapsed_time):
        pass

    def right_click(self, mouse_local_pos):
        if self.view_interface_on_click:
            self.game.blocks_ui_manager.set_block(self)
