from pygame import surface
from units.common import *
from units.Tiles import *
from time import time

# rect для отрисовки
from units.map.GameMap import GameMap

srect_d = pg.Rect(-TSIZE, -TSIZE, WSIZE[0] + TSIZE, WSIZE[1] + TSIZE)


class ScreenMap:
    def __init__(self, display, game_map, player):
        self.display = display
        self.game_map: GameMap = game_map
        self.player = player
        self.true_scroll = [player.rect.x, player.rect.y]
        self.scroll = [0, 0]
        self.tact = 0
        # ===================================================
        self.static_tiles = {}
        self.dynamic_tiles = []
        self.group_handlers = {}

    def update(self, tact):
        self.tact = tact
        tt = time()
        p = self.player
        self.true_scroll[0] += (p.rect.x - self.true_scroll[0] - WSIZE[0] // 2) / 20
        offset_y = (p.rect.y - self.true_scroll[1] - WSIZE[1] // 2)
        if abs(offset_y) > TSIZE * 3:
            offset_y *= min(abs(offset_y) / (2 * TSIZE), 10)
        self.true_scroll[1] += float(offset_y / 20)

        self.scroll = scroll = [int(self.true_scroll[0]), int(self.true_scroll[1])]

        static_tiles = {}
        dynamic_tiles = []
        group_handlers = {}
        scroll_chunk_x = ((scroll[0]) // (TILE_SIZE) + CSIZE - 1) // CSIZE - 1
        chunk_y = ((scroll[1]) // (TILE_SIZE) + CSIZE - 1) // CSIZE - 1

        # SHOW DEBUG GRID CHUNKS ++++
        if show_chunk_grid:
            ch_x = scroll_chunk_x * CSIZE * TILE_SIZE - scroll[0]
            for cx in range(WCSIZE[0]):
                pygame.draw.line(self.display, CHUNK_BD_COLOR, (ch_x, 0), (ch_x, WSIZE[1]))
                ch_x += CSIZEPX
            ch_y = chunk_y * CSIZE * TILE_SIZE - scroll[1]
            for cy in range(WCSIZE[1]):
                pygame.draw.line(self.display, CHUNK_BD_COLOR, (0, ch_y), (WSIZE[0] - 1, ch_y))
                ch_y += CSIZEPX
        # -----------------------------

        # SHOW AND LOAD TILES ++++++++
        for cy in range(WCSIZE[1]):
            chunk_x = scroll_chunk_x
            for cx in range(WCSIZE[0]):
                chunk_pos = (chunk_x, chunk_y)
                chunk = self.game_map.chunk(chunk_pos)
                if chunk is None:
                    # генериует статические и динамичские чанки
                    chunk = self.game_map.generate_chunk(chunk_x, chunk_y)  # [static_lst, dynamic_lst]
                if chunk:
                    # if cx  + cy == 0:
                    #     print("chunk_pos", chunk_pos)
                    dynamic_tiles += chunk[1]
                    group_handlers.update(chunk[2])
                    index = 0
                    tile_y = chunk_y * CSIZE
                    for y in range(CSIZE):
                        tile_x = chunk_x * CSIZE
                        for x in range(CSIZE):
                            tile = chunk[0][index:index + self.game_map.tile_data_size]
                            if not tile:
                                continue
                            tile_type = tile[0]
                            if tile_type > 0:
                                b_pos = (tile_x * TILE_SIZE - scroll[0], tile_y * TILE_SIZE - scroll[1])
                                if srect_d.collidepoint(*b_pos):
                                    # print(tile_xy)
                                    if tile_type == 203:
                                        img = tile_imgs[tile_type + 1][tile[2] - 1]
                                    else:
                                        img = tile_imgs[tile_type]

                                    self.display.blit(img, b_pos)
                                    sol = tile[1]
                                    if sol != -1 and sol != TILES_SOLIDITY[tile_type]:
                                        br_i = 2 - int(sol / (TILES_SOLIDITY[tile_type] / 3))
                                        self.display.blit(break_imgs[br_i], b_pos)

                            # if tile_type in PHYSBODY_TILES:
                            static_tiles[(tile_x, tile_y)] = tile_type
                            index += self.game_map.tile_data_size
                            tile_x += 1
                        tile_y += 1

                chunk_x += 1
            chunk_y += 1

        self.static_tiles = static_tiles
        self.dynamic_tiles = dynamic_tiles
        self.group_handlers = group_handlers
        self.update_dynamic()
        tt = time() - tt

    def update_dynamic(self):
        i = 0
        while i < len(self.dynamic_tiles):
            dtile = self.dynamic_tiles[i]
            dtile.update(self.tact)
            if not dtile.alive:
                self.dynamic_tiles.pop(i)
                self.game_map.del_dinamic_obj(*GameMap.to_chunk_xy(*GameMap.to_tile_xy(*dtile.rect.topleft)), dtile)
                continue
            pos = dtile.rect.x - self.scroll[0], dtile.rect.y - self.scroll[1]
            dtile.draw(self.display, pos)
            i += 1



'''
    def chunk_thread(self, idx=0):
        """idx - индекс потока"""
        while True:
            if self.chunks_for_processing[idx]:
                self.chunks_result[idx] = self.chunk_processing(self.chunks_for_processing[idx])

    def chunk_processing(self, chunk_x, chunk_y):
        static_tiles = {}
        dynamic_tiles = []
        group_handlers = {}

        chunk_pos = (chunk_x, chunk_y)
        chunk = self.game_map.chunk(chunk_pos)
        if chunk is None:
            # генериует статические и динамичские чанки
            chunk = self.game_map.generate_chunk(chunk_x, chunk_y)  # [static_lst, dynamic_lst]
        if chunk:
            # if cx  + cy == 0:
            #     print("chunk_pos", chunk_pos)
            dynamic_tiles += chunk[1]
            group_handlers.update(chunk[2])
            index = 0
            tile_y = chunk_y * CSIZE
            for y in range(CSIZE):
                tile_x = chunk_x * CSIZE
                for x in range(CSIZE):
                    tile = chunk[0][index:index + self.game_map.tile_data_size]
                    tile_type = tile[0]
                    if tile_type > 0:
                        b_pos = (tile_x * TILE_SIZE - self.scroll[0], tile_y * TILE_SIZE - self.scroll[1])
                        if srect_d.collidepoint(*b_pos):
                            # print(tile_xy)
                            if tile_type == 201:
                                img = tile_imgs[tile_type + 1][tile[2] - 1]
                            else:
                                img = tile_imgs[tile_type]

                            self.display.blit(img, b_pos)
                            sol = tile[1]
                            if sol != -1 and sol != TILES_SOLIDITY[tile_type]:
                                br_i = 2 - int(sol / (TILES_SOLIDITY[tile_type] / 3))
                                self.display.blit(break_imgs[br_i], b_pos)

                    if tile_type in PHYSBODY_TILES:
                        static_tiles[(tile_x, tile_y)] = tile_type
                    index += self.game_map.tile_data_size
                    tile_x += 1
                tile_y += 1

'''