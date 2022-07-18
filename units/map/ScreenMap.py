from time import time

from units.Tiles import *
# rect для отрисовки
from units.map.GameMap import GameMap, grow_tree

srect_d = pg.Rect(-TSIZE, -TSIZE, WSIZE[0] + TSIZE, WSIZE[1] + TSIZE)


class ScreenMap:
    display_rect = srect_d

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

    def teleport_to_player(self):
        self.true_scroll[0] = self.player.rect.x - WSIZE[0] // 2
        self.true_scroll[1] = self.player.rect.y - WSIZE[1] // 2

    def update(self, tact):
        self.tact = tact
        tt = time()
        p = self.player
        self.game_map.saved = False
        # climate = self.game_map.get_tile_climate(p.rect.x // TSIZE, p.rect.y // TSIZE)
        # if climate:
        #     biome_color = biome_colors[climate[0]]
        #     self.display.fill(biome_color)
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
                chunk = self.game_map.chunk(chunk_pos, for_player=True)
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
                    i = 0
                    for y in range(CSIZE):
                        tile_x = chunk_x * CSIZE
                        for x in range(CSIZE):
                            tile = chunk[0][index:index + self.game_map.tile_data_size]
                            tile_type = tile[0]
                            if tile_type > 0:
                                b_pos = [tile_x * TILE_SIZE - scroll[0], tile_y * TILE_SIZE - scroll[1]]
                                sprite_pos = b_pos
                                if srect_d.collidepoint(*b_pos):
                                    # print(tile_xy)
                                    if tile_type in tile_many_imgs:
                                        img = tile_many_imgs[tile_type][tile[2]]
                                    else:
                                        img = tile_imgs[tile_type]
                                    if tile_type == 1:
                                        biome = self.game_map.get_tile_climate(tile_x, tile_y)[0]
                                        if biome in ground_imgs:
                                            img = ground_imgs[biome][0]
                                            if static_tiles.get((tile_x - 1, tile_y), 0) == 0:
                                                img = ground_imgs[biome][1]
                                                if self.game_map.get_static_tile_type(tile_x + 1, tile_y) == 0:
                                                    img = ground_imgs[biome][3]
                                            elif self.game_map.get_static_tile_type(tile_x + 1, tile_y) == 0:
                                                img = ground_imgs[biome][2]
                                        else:
                                            if static_tiles.get((tile_x - 1, tile_y), 0) == 0:
                                                img = ground_L_img
                                                if self.game_map.get_static_tile_type(tile_x + 1, tile_y) == 0:
                                                    img = ground_LR_img
                                            elif self.game_map.get_static_tile_type(tile_x + 1, tile_y) == 0:
                                                img = ground_R_img

                                    elif tile_type == 126:  # шкаф
                                        img = tile_imgs[tile_type].copy()
                                        step = TSIZE // 2
                                        for ity in range(2):
                                            for itx in range(2):
                                                if tile[3]:
                                                    item = tile[3][ity * 2 + itx]
                                                    if item:
                                                        img.blit(
                                                                 pg.transform.scale(tile_hand_imgs[item[0]],
                                                                                    (TSIZE//2-1, TSIZE//2-1)),
                                                                 (itx * step + 1, ity * step + 1))
                                    else:
                                        self.update_tile(chunk, tile, tile_type, index, tile_x, tile_y, tact)

                                    if tile_type in TILE_WITH_LOCAL_POS:
                                        local_pos = tile[3][TILE_LOCAL_POS]
                                        sprite_pos[0] += local_pos[0]
                                        sprite_pos[1] += local_pos[1]
                                    self.display.blit(img, sprite_pos)
                                    sol = tile[1]
                                    if sol != -1 and sol != TILES_SOLIDITY[tile_type]:
                                        br_i = (break_imgs_cnt - 1) - int(
                                            sol * (break_imgs_cnt - 1) / TILES_SOLIDITY[tile_type])
                                        self.display.blit(break_imgs[br_i], b_pos)

                            # else:
                            #     b_pos = (tile_x * TILE_SIZE - scroll[0], tile_y * TILE_SIZE - scroll[1])
                            #     img = biome_tiles[chunk[4][i][0]]
                            #     self.display.blit(img, b_pos)
                            # if tile_type in PHYSBODY_TILES:
                            if tile_type != 0:
                                static_tiles[(tile_x, tile_y)] = tile_type
                            index += self.game_map.tile_data_size
                            tile_x += 1
                            i += 1
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
                self.game_map.del_dinamic_obj(*GameMap.to_chunk_xy(*GameMap.to_tile_xy(*dtile.rect.topleft)), dtile)
                self.dynamic_tiles.pop(i)
                continue
            pos = dtile.rect.x - self.scroll[0], dtile.rect.y - self.scroll[1]
            dtile.draw(self.display, pos)
            i += 1

    def update_tile(self, chunk, tile, tile_type, index, tile_x, tile_y, tact):
        if tile_type == 101:
            if tile[2] < 3:
                if tile[3][TILE_TIMER] < tact:
                    if tile[3][TILE_TIMER] != 0:
                        chunk[0][index + 2] += 1
                    else:
                        chunk[0][index + 3][TILE_TIMER] = tact
                    # tile[3] = tact --> тк срез
                    chunk[0][index + 3][TILE_TIMER] += random.randint(FPS * 60, FPS * 120)

        elif tile_type == 102:
            # дерево
            if tile[2] == 0:
                # посажено дерево
                chunk[0][index + 3][TILE_TIMER] = tact + random.randint(FPS * 240, FPS * 660)
                chunk[0][index + 2] = 1  # растет
            elif tile[2] == 2:
                # вырастить мгновено
                grow_tree((tile_x, tile_y), game_map=self.game_map)
            elif tile[2] == 1:
                # растет дерево
                if tile[3][TILE_TIMER] <= tact:
                    if tile[3][TILE_TIMER] != 0:
                        # проращиваем дерево
                        grow_tree((tile_x, tile_y), game_map=self.game_map)


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
