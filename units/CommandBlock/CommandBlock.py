from units.CommandBlock.ProgrammLang import ProgramEnvironment
from units.Graphics.Animation import Animation
from units.Objects.TileClass import Tile
from units.Tiles import commandblock_imgs


class CommandBlock(Tile):

    view_interface_on_click = True
    not_save_vars = Tile.not_save_vars | {"animation", "program_environment"}
    index = 200

    def __init__(self, game, tile_pos):
        super(CommandBlock, self).__init__(game, tile_pos)
        self.animation = Animation(commandblock_imgs, looped=True, ms_per_frame=50, start=True)
        self.program_environment = ProgramEnvironment(self.game, init_vars={})
        self.code = "set_block(0, 0, 1)\nprint(1)"

    def update(self, elapsed_time):
        self.animation.update(elapsed_time)
        return self.animation.get_frame()

    def run_code(self):
        res = self.program_environment.run_code(self.code)
        print("run_code_", res)
        return res

    def set_code(self, code):
        self.code = code



