from time import time

from units.Texture import get_color_of_gradient
from units.Tiles import *
# rect для отрисовки
from units.biomes import biome_colors, biome_tiles
from units.config import GameSettings
from units.map.GameMap import GameMap, grow_tree

srect_d = pg.Rect(-TSIZE, -TSIZE, WSIZE[0] + TSIZE, WSIZE[1] + TSIZE)

PARALLAX = 0.4
PARALLAX_SPACE = 0.04


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

        self.edges = [-20000, 20000, START_ATMO_Y * TSIZE, 20000]
        width = self.edges[1] - self.edges[0]
        height = self.edges[3] - self.edges[2]
        area = width * height

        self.clouds = []
        for i in range(int(area // 1200000)):
            self.clouds.append([random.randint(0, len(cloud_images) - 1), (random.random() * 2 + 1) / 5,
                                (self.edges[0] + random.random() * (width + display.get_width())) * PARALLAX,
                                random.randint(self.edges[2],
                                               self.edges[3] - int(height * 0.3) + display.get_height()) * PARALLAX])
        print("CLOUDS:", area // 1200000)

        self.edges_for_stars = [-20000, 20000, START_SPACE_Y * TSIZE - 15000, TOP_MIDDLE_WORLD * TSIZE]
        width = self.edges_for_stars[1] - self.edges_for_stars[0]
        height = self.edges_for_stars[3] - self.edges_for_stars[2]
        area = width * height
        cnt = int(area // 120000)
        self.sky_stars = []
        for i in range(cnt):
            self.sky_stars.append([random.choices(star_chances[0], star_chances[1], k=1)[0],
                                   (self.edges_for_stars[0] + random.random() * (width + display.get_width())),
                                   random.randint(self.edges_for_stars[2],
                                                  self.edges_for_stars[3] - int(height * 0.3) + display.get_height())])
        print("STARS:", cnt)

    def teleport_to_player(self):
        self.true_scroll[0] = self.player.rect.x - WSIZE[0] // 2
        self.true_scroll[1] = self.player.rect.y - WSIZE[1] // 2

    def draw_sky(self):
        # self.display.blit(self.sky_surface, (0, 0))
        height = TSIZE * 10000
        sky_cosmos = (5, 7, 14, 255)
        sky_atmo = (10, 15, 28, 255)
        sky_center = (165, 243, 252, 255)
        sky_red = (135, 0, 0, 255)
        i = self.player.rect.y
        if i > TSIZE * BOTTOM_MIDDLE_WORLD:
            # ад
            color = get_color_of_gradient((START_HELL_Y - BOTTOM_MIDDLE_WORLD) * TSIZE,
                                          sky_center, sky_red, i - TSIZE * BOTTOM_MIDDLE_WORLD)
        elif i < TSIZE * START_ATMO_Y:
            # космос
            color = get_color_of_gradient(abs(START_SPACE_Y - START_ATMO_Y) * TSIZE,
                                          sky_atmo, sky_cosmos, -i + TSIZE * START_ATMO_Y)
        elif i < TSIZE * TOP_MIDDLE_WORLD:
            # верхняя атмосфера
            color = get_color_of_gradient(abs(START_ATMO_Y - TOP_MIDDLE_WORLD) * TSIZE,
                                          sky_center, sky_atmo, -i + TSIZE * TOP_MIDDLE_WORLD)
            # print("верхняя атмосфера", color)
        else:
            color = sky_center
        # print("COLOR SKY", color)
        self.display.fill(color)

    def update(self, tact):
        self.tact = tact
        tt = time()
        p = self.player
        self.game_map.saved = False
        # climate = self.game_map.get_tile_climate(p.rect.x // TSIZE, p.rect.y // TSIZE)
        # if climate:
        #     biome_color = biome_colors[climate[0]]
        #     self.display.fill(biome_color)
        self.true_scroll[0] += (p.rect.centerx - self.true_scroll[0] - WSIZE[0] // 2) / 20
        offset_y = (p.rect.centery - self.true_scroll[1] - WSIZE[1] // 2)
        if abs(offset_y) > TSIZE * 3:
            offset_y *= min(abs(offset_y) / (2 * TSIZE), 10)
        self.true_scroll[1] += float(offset_y / 20)

        self.true_scroll[0] += (p.rect.x - self.true_scroll[0] - WSIZE[0] // 2) / 15

        offset_y = abs(p.rect.y - self.true_scroll[1] - WSIZE[1] // 2)
        div = max(1, 32 / max(1, offset_y ** 0.5))
        self.true_scroll[1] += (p.rect.y - self.true_scroll[1] - WSIZE[1] // 2) / div

        # self.true_scroll[1] = self.player.rect.y - WSIZE[1] // 2
        self.scroll = scroll = [int(self.true_scroll[0]), int(self.true_scroll[1])]
        if GameSettings.stars and self.scroll[1] < TOP_MIDDLE_WORLD * TSIZE:
            for star in self.sky_stars:
                pos = (star[1] - scroll[0] * PARALLAX_SPACE,
                       star[2] - scroll[1] * PARALLAX_SPACE - (TOP_MIDDLE_WORLD * TSIZE - 7000))
                        # star[2] - scroll[1] * PARALLAX_SPACE - (TOP_MIDDLE_WORLD * TSIZE - 6200))
                self.display.blit(star_images[star[0]], pos)
        if GameSettings.clouds:
            for cloud in self.clouds:
                cloud[2] += cloud[1]
                self.display.blit(cloud_images[cloud[0]],
                                  (cloud[2] - scroll[0] * PARALLAX, cloud[3] - scroll[1] * PARALLAX))
                if cloud[2] > (self.edges[1] + WSIZE[0]) * PARALLAX:
                    cloud[2] = self.edges[0] * PARALLAX - cloud_images[cloud[0]].get_width()

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
                                if srect_d.collidepoint(*b_pos) or 1:
                                    # print(tile_xy)
                                    if tile_type in tile_many_imgs:
                                        img = tile_many_imgs[tile_type][tile[2]]
                                    else:
                                        img = tile_imgs[tile_type]
                                    if tile_type == 1:
                                        biome = self.game_map.get_tile_climate(tile_x, tile_y)[0]
                                        if biome not in ground_imgs:
                                            biome = None
                                        img = ground_imgs[biome][0]
                                        if static_tiles.get((tile_x - 1, tile_y), 0) == 0:
                                            img = ground_imgs[biome][1]
                                            if self.game_map.get_static_tile_type(tile_x + 1, tile_y) == 0:
                                                img = ground_imgs[biome][3]
                                        elif self.game_map.get_static_tile_type(tile_x + 1, tile_y) == 0:
                                            img = ground_imgs[biome][2]
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
                                                                               (TSIZE // 2 - 1, TSIZE // 2 - 1)),
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

                            elif GameSettings.show_biomes:
                                b_pos = (tile_x * TILE_SIZE - scroll[0], tile_y * TILE_SIZE - scroll[1])
                                img = biome_tiles[chunk[4][i][0]]
                                self.display.blit(img, b_pos)
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
