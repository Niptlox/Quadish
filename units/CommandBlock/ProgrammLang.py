from units import Tiles
from units.Objects.Player import Player
from units.Objects import Creatures
from units.common import TSIZE


class ProgramEnvironment:
    def __init__(self, game, init_vars=None):
        from units.Map.GameMap import GameMap

        self.game = game
        self.game_map: GameMap = game.game_map
        self.player: Player = game.player
        self.__functions = {self.set_block, self.get_block, self.set_block,
                            self.get_player, self.get_player_pos, self.set_player_pos,
                            self.debug, self.summon}
        self.functions = {f.__name__: f for f in self.__functions}
        self.constants = {"ALL_BLOCKS": Tiles.all_tiles, "ALL_CREATURES": set(Creatures.CREATURES_D.values())}
        if init_vars:
            self.environment = dict(init_vars)
        else:
            self.environment = {}
        self.environment.update(self.functions)
        self.environment.update(self.constants)
        self.result = ""

    def run_code(self, code):
        print("run_code", code)
        self.result = ""
        try:
            exec(code, self.environment)
            return self.result
        except Exception as exc:
            print("Run exc", exc)
            return str(exc)

    def debug(self, st):
        self.result = st

    def get_player(self):
        return self.player

    def set_player_pos(self, x, y):
        self.player.tp_to((x * TSIZE, y * TSIZE))

    def get_player_pos(self):
        return self.player.rect.x / TSIZE, self.player.rect.y / TSIZE

    def get_block(self, x, y):
        block_id = self.game_map.get_static_tile(x, y)
        return block_id

    def set_block(self, x, y, block_id: int):
        print("set_block", x, y, block_id)
        if block_id in Tiles.all_tiles:
            self.game_map.set_static_tile(x, y, block_id, create_chunk=True)
        else:
            return self.exception(f"Использован не существующий блок ({block_id})")

    def summon(self, x, y, creature_id):
        if creature_id in Creatures.CREATURES_D:
            obj: Creatures.Creature = Creatures.CREATURES_D[creature_id](self.game, pos=(x * TSIZE, y * TSIZE))
            return self.game_map.add_dinamic_obj(obj.chunk_pos[0], obj.chunk_pos[1], obj)
        else:
            return self.exception(f"Использовано не существующее существо ({creature_id})")

    def exception(self, st):
        assert Exception(st)
