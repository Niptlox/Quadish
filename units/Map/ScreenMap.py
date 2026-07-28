from time import time

from units.Graphics.Texture import get_color_of_gradient
from units.Tiles import *
# rect для отрисовки
from units.biomes import biome_tiles
from units.config import GameSettings
from units.Map.GameMap import GameMap

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
        self.elapsed_time = 0
        self.last_scrollx_div = 4 # последний делитель для scroll x
        self.last_scrolly_div = 4  # последний делитель для scroll y
        # ===================================================
        self.static_tiles = {}
        self.dynamic_tiles = []
        self.group_handlers = {}
        self.visible_chunks = set()

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

        # Ночные звёзды — отдельный слой от космических (self.sky_stars): те
        # живут высоко над атмосферой и с поверхности не видны вовсе. Без них
        # ночь читалась бы не как ночь, а как «экран потемнел».
        self.night_stars = []
        for i in range(max(200, int(area // 900000))):
            self.night_stars.append([
                (self.edges[0] + random.random() * (width + display.get_width())) * PARALLAX,
                random.randint(self.edges[2], self.edges[3]) * PARALLAX,
                random.randint(1, 2)])

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

        # запас для отсечения невидимых облаков/звёзд (максимальный размер картинки)
        self.cloud_margin = max(max(im.get_width() for im in cloud_images),
                                max(im.get_height() for im in cloud_images))
        self.star_margin = max(max(im.get_width() for im in star_images),
                               max(im.get_height() for im in star_images))

    def teleport_to_player(self):
        self.true_scroll[0] = self.player.rect.x - WSIZE[0] // 2
        self.true_scroll[1] = self.player.rect.y - WSIZE[1] // 2

    def world_time(self):
        return getattr(self.game_map, "world_time", 0)

    def sky_light(self):
        """Освещённость неба здесь и сейчас: 1 — день, меньше — ночь.

        Считается от глубины: под землёй смена суток ничего не значит, там
        свой свет, и мигающая с ночью пещера читалась бы как баг."""
        return surface_daylight(self.world_time(), self.player.rect.y // TSIZE)

    def draw_sky(self):
        sky_cosmos = (5, 7, 14, 255)
        sky_atmo = (10, 15, 28, 255)
        sky_center = (165, 243, 252, 255)
        sky_red = (135, 0, 0, 255)
        # Ночное небо не просто «тёмно-голубое»: холодный синий читается как
        # ночь, а затемнённый дневной — как пасмурный день.
        sky_night = (12, 18, 44, 255)
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
        light = self.sky_light()
        if light < 1.0:
            # Ведём цвет к ночному, а не просто умножаем на яркость: умножение
            # даёт «выключенный монитор», а не ночь.
            k = (1.0 - light) / (1.0 - NIGHT_LIGHT)
            color = tuple(int(c + (n - c) * k) for c, n in zip(color[:3], sky_night[:3])) + (255,)
        self.display.fill(color)

    def update(self, tact, elapsed_time):
        self.tact = tact
        self.elapsed_time = elapsed_time
        tt = time()
        p = self.player
        self.game_map.saved = False
        # climate = self.game_map.get_tile_climate(p.rect.x // TSIZE, p.rect.y // TSIZE)
        # if climate:
        #     biome_color = biome_colors[climate[0]]
        #     self.display.fill(biome_color)
        # self.true_scroll[0] += (p.rect.centerx - self.true_scroll[0] - WSIZE[0] // 2) / 20
        # offset_y = (p.rect.centery - self.true_scroll[1] - WSIZE[1] // 2)
        # if abs(offset_y) > TSIZE * 3:
        #     offset_y *= min(abs(offset_y) / (2 * TSIZE), 10)
        # self.true_scroll[1] += float(offset_y / 20)

        scrollx_div = max(10, 30 * 12 / elapsed_time)
        max_divx_delta = 0.3
        if scrollx_div - self.last_scrollx_div > max_divx_delta:
            scrollx_div = self.last_scrollx_div + max_divx_delta
        elif scrollx_div - self.last_scrollx_div < -max_divx_delta:
            scrollx_div = self.last_scrollx_div - max_divx_delta
        # scrollx_avg_div = self.last_scrollx_div + (scrollx_div - self.last_scrollx_div) / 5
        self.true_scroll[0] += (p.rect.x - self.true_scroll[0] - WSIZE[0] // 2) / scrollx_div
        self.last_scrollx_div = scrollx_div


        max_offset_y = 3 * TSIZE
        offset_y = abs(p.rect.y - self.true_scroll[1] - WSIZE[1] // 2)
        # div = max(0.001, 30 * 6 / elapsed_time)
        div = max(3, max(1, 48 / max(1, offset_y ** 0.5)) * 30 / elapsed_time)
        div_offset = 0.2
        if div - self.last_scrolly_div > div_offset:
            div = self.last_scrolly_div + div_offset
        elif div - self.last_scrolly_div < -div_offset:
            div = self.last_scrolly_div - div_offset
        self.last_scrolly_div = div
        # print("DIV", elapsed_time, div, offset_y, offset_y ** 0.5, 64 / max(1, offset_y ** 0.5))
        self.true_scroll[1] += (p.rect.y - self.true_scroll[1] - WSIZE[1] // 2) / div
        offset_y = (p.rect.y - self.true_scroll[1] - WSIZE[1] // 2)
        if offset_y > max_offset_y:
            self.true_scroll[1] += (offset_y - max_offset_y)

        # self.true_scroll[1] = self.player.rect.y - WSIZE[1] // 2
        self.scroll = scroll = [int(self.true_scroll[0]), int(self.true_scroll[1])]
        blit = self.display.blit
        sw, sh = WSIZE
        if GameSettings.stars and self.scroll[1] < TOP_MIDDLE_WORLD * TSIZE:
            m = self.star_margin
            off_x = scroll[0] * PARALLAX_SPACE
            off_y = scroll[1] * PARALLAX_SPACE + (TOP_MIDDLE_WORLD * TSIZE - 7000)
            for star in self.sky_stars:
                x = star[1] - off_x
                if -m < x < sw:
                    y = star[2] - off_y
                    if -m < y < sh:
                        blit(star_images[star[0]], (x, y))
        # Ночные звёзды — до облаков, чтобы облака шли поверх них
        night_light = self.sky_light()
        if GameSettings.stars and night_light < 0.95:
            alpha = int(255 * min(1.0, (1.0 - night_light) / (1.0 - NIGHT_LIGHT)))
            off_x = scroll[0] * PARALLAX
            off_y = scroll[1] * PARALLAX
            surf = self.display
            for sx, sy, size in self.night_stars:
                x = sx - off_x
                if 0 <= x < sw:
                    y = sy - off_y
                    if 0 <= y < sh:
                        pg.draw.rect(surf, (230, 240, 255, alpha), (x, y, size, size))
        if GameSettings.clouds:
            m = self.cloud_margin
            off_x = scroll[0] * PARALLAX
            off_y = scroll[1] * PARALLAX
            right_edge = (self.edges[1] + WSIZE[0]) * PARALLAX
            for cloud in self.clouds:
                cloud[2] += cloud[1]
                if cloud[2] > right_edge:
                    cloud[2] = self.edges[0] * PARALLAX - cloud_images[cloud[0]].get_width()
                x = cloud[2] - off_x
                if -m < x < sw:
                    y = cloud[3] - off_y
                    if -m < y < sh:
                        blit(cloud_images[cloud[0]], (x, y))

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

        # Видимый диапазон тайлов (+1 тайл запаса по краям).
        vis_x0 = scroll[0] // TILE_SIZE - 1
        vis_x1 = (scroll[0] + sw) // TILE_SIZE + 1
        vis_y0 = scroll[1] // TILE_SIZE - 1
        vis_y1 = (scroll[1] + sh) // TILE_SIZE + 1
        # Область коллизий: экран плюс запас. Раньше в static_tiles попадали
        # ВСЕ непустые тайлы всех загруженных чанков — замер показал 3700
        # записей на поверхности и 6500 в пещерах при 960 тайлах на экране,
        # то есть на каждый кадр приходилось несколько тысяч лишних кортежей
        # и вставок в словарь. Существа и предметы дальше запаса не
        # обновляются (см. фильтр dynamic_tiles ниже), значит и коллизии им
        # не нужны.
        col_x0 = vis_x0 - COLLIDE_MARGIN
        col_x1 = vis_x1 + COLLIDE_MARGIN
        col_y0 = vis_y0 - COLLIDE_MARGIN
        col_y1 = vis_y1 + COLLIDE_MARGIN
        tds = self.game_map.tile_data_size
        # Локальные ссылки на всё, к чему обращается внутренний цикл. Он
        # прокручивается ~1000 раз за кадр, и на таком числе итераций поиск
        # глобала/атрибута стоит сравнимо с самой работой.
        get_type = self.game_map.get_static_tile_type
        update_tile = self.update_tile
        t_imgs = tile_imgs
        t_many = tile_many_imgs
        t_hand = tile_hand_imgs
        solidity = TILES_SOLIDITY
        br_imgs = break_imgs
        br_cnt = break_imgs_cnt
        g_imgs = ground_imgs
        local_pos_tiles = TILE_WITH_LOCAL_POS
        b_tiles = biome_tiles
        opaque = OPAQUE_TILES
        needs_tick = NEEDS_TICK
        # Тайлы, годные для склейки в полосу: один фиксированный спрайт,
        # без своей логики, без смещения и без задней панельки под ним.
        strip_ok = STRIP_TILES
        show_biomes = GameSettings.show_biomes   # раньше читалось на каждый тайл
        sx, sy = scroll[0], scroll[1]
        half_tile = TSIZE // 2
        cell_img_size = (half_tile - 1, half_tile - 1)

        # Чанки, обойдённые на этом кадре: GameMap.tick_forced_chunks должен
        # их пропустить, иначе тайлы получат два тика за кадр и растения
        # под прогрузчиком росли бы вдвое быстрее прямо на экране.
        self.visible_chunks.clear()
        for cy in range(WCSIZE[1]):
            chunk_x = scroll_chunk_x
            for cx in range(WCSIZE[0]):
                chunk_pos = (chunk_x, chunk_y)
                self.visible_chunks.add(chunk_pos)
                chunk = self.game_map.chunk(chunk_pos, for_player=True)
                if chunk is None:
                    # генериует статические и динамичские чанки
                    chunk = self.game_map.generate_chunk(chunk_x, chunk_y)  # [static_lst, dynamic_lst]
                if chunk:
                    # Обновляем только то, что рядом с экраном: далёкое
                    # существо всё равно не видно, а платит за него каждый кадр.
                    for obj in chunk[1]:
                        otx, oty = obj.rect.centerx // TILE_SIZE, obj.rect.centery // TILE_SIZE
                        if col_x0 <= otx <= col_x1 and col_y0 <= oty <= col_y1:
                            dynamic_tiles.append(obj)
                    group_handlers.update(chunk[2])
                    chunk_static = chunk[0]
                    chunk_back = chunk[5]
                    index = 0
                    backtile_index = 0
                    tile_y = chunk_y * CSIZE
                    i = 0
                    for y in range(CSIZE):
                        tile_x = chunk_x * CSIZE
                        if not (col_y0 <= tile_y <= col_y1):
                            # строка вне области коллизий: не трогаем вообще
                            index += CSIZE * tds
                            backtile_index += CSIZE
                            i += CSIZE
                            tile_y += 1
                            continue
                        if not (vis_y0 <= tile_y <= vis_y1):
                            # строка за экраном: только коллизии
                            for x in range(CSIZE):
                                if col_x0 <= tile_x <= col_x1:
                                    tile_type = chunk_static[index]
                                    if tile_type != 0:
                                        static_tiles[(tile_x, tile_y)] = tile_type
                                index += tds
                                tile_x += 1
                            backtile_index += CSIZE
                            i += CSIZE
                            tile_y += 1
                            continue
                        # Позицию в пикселях считаем приращением: умножение
                        # и вычитание на каждый тайл — это ~1000 лишних
                        # операций за кадр.
                        py = tile_y * TILE_SIZE - sy
                        px = tile_x * TILE_SIZE - sx
                        # Явный счётчик колонки, а не for: полоса из
                        # одинаковых тайлов съедает несколько колонок за одну
                        # итерацию, а присваивание переменной цикла for на его
                        # ход не влияет — индексы разъезжались бы с колонкой.
                        x = 0
                        while x < CSIZE:
                            tile_type = chunk_static[index]
                            if not (vis_x0 <= tile_x <= vis_x1):
                                # тайл за экраном: только коллизии, и только
                                # если он в области, где что-то шевелится
                                if tile_type != 0 and col_x0 <= tile_x <= col_x1:
                                    static_tiles[(tile_x, tile_y)] = tile_type
                                index += tds
                                backtile_index += 1
                                tile_x += 1
                                px += TILE_SIZE
                                i += 1
                                x += 1
                                continue
                            backtile_type = chunk_back[backtile_index]
                            # Под сплошным блоком задней панельки не видно.
                            # Замер: 100% отрисованных панелек были полностью
                            # скрыты передним тайлом — 44% блитов кадра впустую.
                            if backtile_type != 0 and tile_type not in opaque:
                                blit(t_imgs[backtile_type], (px, py))

                            # Пробег одинаковых простых тайлов рисуем одной
                            # полосой. В сплошной породе это десятки
                            # одинаковых блитов подряд, а пиксели те же —
                            # спрайт один и тот же (см. tile_strip).
                            if tile_type in strip_ok and chunk_static[index + 1] == solidity[tile_type]:
                                run = 1
                                j = index + tds
                                rx = tile_x + 1
                                while (run < STRIP_MAX and rx <= vis_x1 and x + run < CSIZE
                                       and chunk_static[j] == tile_type
                                       and chunk_static[j + 1] == solidity[tile_type]):
                                    run += 1
                                    j += tds
                                    rx += 1
                                for length in STRIP_LENGTHS:
                                    if run >= length:
                                        blit(tile_strip(tile_type, length), (px, py))
                                        for k in range(length):
                                            static_tiles[(tile_x, tile_y)] = tile_type
                                            tile_x += 1
                                            px += TILE_SIZE
                                        index += length * tds
                                        backtile_index += length
                                        i += length
                                        x += length
                                        break
                                else:
                                    length = 0
                                if length:
                                    continue

                            if tile_type > 0:
                                # Поля тайла читаем по индексу, а не срезом:
                                # срез создавал новый список на каждый
                                # видимый тайл. Но читаем их ДО update_tile:
                                # саженец за этот же вызов вырастает в дерево
                                # и переписывает тайл на месте, а решения ниже
                                # относятся к тому тайлу, который мы рисуем.
                                sol = chunk_static[index + 1]
                                state = chunk_static[index + 3]
                                b_pos = (px, py)
                                sprite_pos = b_pos
                                if tile_type in t_many:
                                    img = t_many[tile_type][chunk_static[index + 2]]  # кадр
                                else:
                                    img = t_imgs[tile_type]
                                if tile_type == 1:
                                    biome = chunk[4][i][0]
                                    if biome not in g_imgs:
                                        biome = None
                                    variants = g_imgs[biome]
                                    img = variants[0]
                                    # Правый сосед почти всегда в этом же чанке —
                                    # тогда читаем его прямо из массива, без
                                    # вызова метода с поиском чанка. На дёрне
                                    # это было два таких вызова на тайл.
                                    if x < CSIZE - 1:
                                        right = chunk_static[index + tds]
                                    else:
                                        right = get_type(tile_x + 1, tile_y, default=1,
                                                         create_chunk=False)
                                    if static_tiles.get((tile_x - 1, tile_y), 0) == 0:
                                        img = variants[3] if right == 0 else variants[1]
                                    elif right == 0:
                                        img = variants[2]
                                elif tile_type == 126:  # шкаф
                                    img = t_imgs[tile_type].copy()
                                    for ity in range(2):
                                        for itx in range(2):
                                            if state:
                                                item = state[ity * 2 + itx]
                                                if item:
                                                    img.blit(
                                                        pg.transform.scale(t_hand[item[0]], cell_img_size),
                                                        (itx * half_tile + 1, ity * half_tile + 1))
                                elif tile_type in needs_tick:
                                    # Если передана картинка, то отрисовываем
                                    img = update_tile(chunk, chunk_static[index:index + tds],
                                                      tile_type, index, tile_x, tile_y,
                                                      chunk_x, chunk_y, tact) or img

                                if tile_type in local_pos_tiles:
                                    local_pos = state[TILE_LOCAL_POS]
                                    sprite_pos = (px + local_pos[0], py + local_pos[1])
                                blit(img, sprite_pos)

                                if sol != -1:
                                    full = solidity[tile_type]
                                    if sol != full:
                                        blit(br_imgs[(br_cnt - 1) - int(sol * (br_cnt - 1) / full)], b_pos)

                            elif show_biomes:
                                blit(b_tiles[chunk[4][i][0]], (px, py))
                            if tile_type != 0:
                                static_tiles[(tile_x, tile_y)] = tile_type
                            index += tds
                            backtile_index += 1
                            tile_x += 1
                            px += TILE_SIZE
                            i += 1
                            x += 1
                        tile_y += 1

                chunk_x += 1
            chunk_y += 1

        self.static_tiles = static_tiles
        self.dynamic_tiles = dynamic_tiles
        self.group_handlers = group_handlers
        self.update_dynamic()
        self.update_particles()
        tt = time() - tt

    def update_dynamic(self):
        i = 0
        while i < len(self.dynamic_tiles):
            dtile = self.dynamic_tiles[i]
            dtile.update(self.tact, self.elapsed_time)
            if not dtile.alive:
                self.game_map.del_dinamic_obj(*GameMap.to_chunk_xy(*GameMap.to_tile_xy(*dtile.rect.topleft)), dtile)
                self.dynamic_tiles.pop(i)
                continue
            pos = dtile.rect.x - self.scroll[0], dtile.rect.y - self.scroll[1]
            dtile.draw(self.display, pos)
            i += 1

    def update_particles(self):
        i = 0
        while i < len(self.game_map.particles):
            particle = self.game_map.particles[i]
            particle.update(self.tact, self.elapsed_time)
            if not particle.alive:
                self.game_map.del_particle_of_idx(i)
                continue
            pos = particle.rect.x - self.scroll[0], particle.rect.y - self.scroll[1]
            particle.draw(self.display, pos)
            i += 1

    def update_tile(self, chunk, tile, tile_type, index, tile_x, tile_y, chunk_x, chunk_y, tact):
        if tile_type in CLASS_UPDATING_TILES:
            # tick(1), а не update напрямую: у блока со своим счётчиком
            # steps=1 на экране и steps=N за экраном — так выработка не
            # зависит от того, кто его обслуживает (см. Tile.tick).
            return self.game_map.get_tile_obj(chunk_x, chunk_y, tile[3]).tick(1, self.elapsed_time)
        # Рост растений — общий код с обновлением чанков под прогрузчиком
        # (GameMap.grow_plant_tile). Держать здесь вторую копию значило бы,
        # что на экране и вне его фермы растут по-разному.
        self.game_map.grow_plant_tile(chunk, index, tile, tile_x, tile_y, tact)

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
