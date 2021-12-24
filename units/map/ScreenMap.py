from units.common import *
from units.Tiles import *


class ScreenMap:
    def __init__(self, display, game_map, player):
        self.display = display
        self.game_map = game_map
        self.player = player
        self.true_scroll = [player.rect.x, player.rect.y]
        # ===================================================
        self.static_tiles = {}
        self.dinamic_tiles = []
        self.group_handlers = {}

    def update(self):
        p = self.player
        gm = self.game_map
        self.true_scroll[0] += (p.rect.x - self.true_scroll[0] - WSIZE[0] // 2) / 20
        self.true_scroll[1] += (p.rect.y - self.true_scroll[1] - WSIZE[1] // 2) / 20
        scroll = [int(self.true_scroll[0]), int(self.true_scroll[1])]

        static_tiles = {}
        dinamic_tiles = []
        group_handlers = {}
        scroll_chunk_x = ((scroll[0])//(TILE_SIZE)+ CSIZE-1)//CSIZE-1
        chunk_y = ((scroll[1])//(TILE_SIZE)+ CSIZE-1)//CSIZE-1   

        # SHOW DEBUG GRID CHUNKS ++++
        if show_chunk_grid:
            ch_x = scroll_chunk_x*CSIZE*TILE_SIZE-scroll[0]
            for cx in range(WCSIZE[0]):                                                                
                pygame.draw.line(self.display, CHUNK_BD_COLOR, (ch_x, 0), (ch_x, WSIZE[1]))
                ch_x += CSIZEPX
            ch_y = chunk_y*CSIZE*TILE_SIZE-scroll[1]
            for cy in range(WCSIZE[1]):
                pygame.draw.line(self.display, CHUNK_BD_COLOR, (0, ch_y), (WSIZE[0]-1, ch_y))
                ch_y += CSIZEPX
        #-----------------------------

        # SHOW AND LOAD TILES ++++++++
        for cy in range(WCSIZE[1]):                
            chunk_x = scroll_chunk_x
            for cx in range(WCSIZE[0]):
                chunk_pos = (chunk_x, chunk_y)    
                chunk = gm.chunk(chunk_pos)            
                if chunk is None:
                    # генериует статические и динамичские чанки
                    chunk = gm.generate_chunk(chunk_x, chunk_y) # [static_lst, dinamic_lst]
                if chunk:
                    # if cx  + cy == 0:
                    #     print("chunk_pos", chunk_pos)
                    dinamic_tiles += chunk[1]
                    group_handlers.update(chunk[2])
                    index = 0        
                    tile_y = chunk_y*CSIZE
                    for y in range(CSIZE):
                        tile_x = chunk_x*CSIZE
                        for x in range(CSIZE):
                            tile = chunk[0][index:index+gm.tile_data_size]
                            tile_type = tile[0]
                            if tile_type > 0:
                                # print(tile_xy)
                                if tile_type == 201:
                                    img = tile_imgs[tile_type+1][tile[2]-1]
                                else:
                                    img = tile_imgs[tile_type]                                
                                b_pos = (tile_x*TILE_SIZE-scroll[0], tile_y*TILE_SIZE-scroll[1])
                                self.display.blit(img, b_pos)
                                sol = tile[1]
                                if sol != -1 and sol != TILES_SOLIDITY[tile_type]:
                                    br_i = 2 - int(sol / (TILES_SOLIDITY[tile_type] / 3))
                                    self.display.blit(break_imgs[br_i], b_pos)

                            if tile_type in PHYSBODY_TILES:                                
                                static_tiles[(tile_x, tile_y)] = tile_type
                            index += gm.tile_data_size
                            tile_x += 1
                        tile_y += 1

                chunk_x += 1
            chunk_y += 1

            self.static_tiles = static_tiles
            self.dinamic_tiles = dinamic_tiles
            self.group_handlers = group_handlers