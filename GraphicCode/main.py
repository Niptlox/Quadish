from units.App import App, Scene, SceneUI, EXIT
from units.UI.ClassUI import UI
from units.common import *
from units.Image import load_img

# point flags
POINTIN = 2
POINTOUT = 4
POINTINOUT = POINTIN + POINTOUT


class Game(App):
    def __init__(self) -> None:
        self.block_scene = BlockScene(self)
        super().__init__(self.block_scene)


class BlockScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)

        self.ui = UI(self)
        self.ui.init_ui()
        self.tact = 0

        self.components = []
        self.components.append(BlockBegin((20, 20), self))
        self.components.append(BlockOR((15, 220), self))
        self.components.append(BlockEnd((220, 220), self))
        self.components.append(BlockAND((220, 20), self))
        self.mouse_connection = None
        self.get_block = None

    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = EXIT
            if self.ui.pg_event(event):
                continue
            if event.type == pg.KEYDOWN:
                pass
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if not self.get_block:
                        # реверсивно, чтобы те кто отрисовались последними, обробатывались первыми
                        for i in range(len(self.components) - 1, -1, -1):
                            obj = self.components[i]
                            if obj.collide_pos(event.pos):
                                for point in obj.points:
                                    if point.collide_pos(event.pos) and self.mouse_connection != point:
                                        if self.mouse_connection:
                                            if (point.typeP & POINTOUT and self.mouse_connection.typeP & POINTIN) or \
                                                    (point.typeP & POINTIN and self.mouse_connection.typeP & POINTOUT):
                                                self.mouse_connection.add_connection(point)
                                                self.mouse_connection = None
                                        else:
                                            self.mouse_connection = point
                                        break
                                else:
                                    if not self.mouse_connection:
                                        offset = obj.rect.x - event.pos[0], obj.rect.y - event.pos[1]
                                        self.get_block = (obj, offset)
                                        # вставить в конец отрисовки, чтоб был впереди
                                        self.components.pop(i)
                                        self.components.append(obj)
                                        break
                    else:
                        self.get_block = None
                elif event.button == 3:
                    self.mouse_connection = None
                    self.get_block = None
            elif event.type == pg.MOUSEBUTTONUP:
                self.get_block = None
            elif event.type == pg.MOUSEMOTION:
                if self.get_block:
                    self.get_block[0].rect.topleft = (event.pos[0] + self.get_block[1][0],
                                                      event.pos[1] + self.get_block[1][1])

    def update(self):
        for obj in self.components:
            obj.draw(self.display)
        for obj in self.components:
            obj.draw_connections(self.display)
        if self.mouse_connection:
            pg.draw.line(self.display, "#11FF11", self.mouse_connection.pos_on_field(), pg.mouse.get_pos(), width=2)
        self.ui.draw()
        self.display.fill("#000000")

        self.tact += 1


class Field:
    rect = pg.Rect((0, 0), WSIZE)


class Point:
    radius = 4
    size = radius * 2, radius * 2
    sprite = pg.Surface(size)
    sprite.fill("#FFFFFF")
    typeP = POINTINOUT

    def __init__(self, pos, owner):
        self.owner = owner
        self.rect = pg.Rect(pos, self.size)
        self.connections = []

    def draw(self, surface: pg.Surface):
        surface.blit(self.sprite, (self.rect.x + self.owner.rect.x, self.rect.y + self.owner.rect.y))

    def draw_connections(self, surface):
        for con in self.connections:
            pg.draw.line(surface, "#11FF11", self.pos_on_field(), con.pos_on_field(), width=3)

    def add_connection(self, conn):
        self.connections.append(conn)

    def collide_pos(self, pos):
        pos = pos[0] - self.owner.rect.x, pos[1] - self.owner.rect.y
        return self.rect.collidepoint(pos)

    def pos_on_field(self):
        return self.rect.centerx + self.owner.rect.x, self.rect.centery + self.owner.rect.y


class PointIN(Point):
    typeP = POINTIN


class PointOUT(Point):
    typeP = POINTOUT


class Block:
    size = 100, 100
    sprite = pg.Surface(size)
    sprite.fill("#FF00FF")
    pos_points_in = []
    pos_points_out = []

    def __init__(self, pos, scene):
        self.scene = scene
        self.rect = pg.Rect(pos, self.size)
        self.points_in = [PointIN(pos, self) for pos in self.pos_points_in]
        self.points_out = [PointOUT(pos, self) for pos in self.pos_points_out]
        self.points = self.points_in + self.points_out

    def draw(self, surface: pg.Surface):
        surface.blit(self.sprite, self.rect)
        for point in self.points:
            point.draw(surface)

    def draw_connections(self, surface):
        for point in self.points:
            point.draw_connections(surface)

    def collide_pos(self, pos):
        return self.rect.collidepoint(pos)


class BlockBegin(Block):
    pos_points_out = [(46, 28)]
    size = (64, 64)
    sprite = load_img("sprites/BlockBegin1.png", size)


class BlockEnd(Block):
    pos_points_in = [(10, 28)]
    size = (64, 64)
    sprite = load_img("sprites/BlockEnd1.png", size)


class BlockOR(Block):
    pos_points_in = [(12, 12), (12, 44)]
    pos_points_out = [(78, 28)]
    size = (96, 64)
    sprite = load_img("sprites/BlockOR.png", size)


class BlockAND(Block):
    pos_points_in = [(12, 12), (12, 44)]
    pos_points_out = [(78, 28)]
    size = (96, 64)
    sprite = load_img("sprites/BlockAND.png", size)


if __name__ == "__main__":
    game = Game()
    game.main()
