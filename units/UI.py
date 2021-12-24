from units.common import *
from units.Tiles import tile_imgs, sky

# INIT TEXT ==================================================

pygame.font.init()
# textfont = pygame.font.SysFont('Jokerman', 19)
textfont = pygame.font.SysFont("Fenix", 19, )
# textfont = pygame.font.Font('data/fonts/Teletactile.ttf', 10, bold=True)
textfont_info = pygame.font.Font('data/fonts/Teletactile.ttf', 10, )

# texframe = font.render(text, False, text_color)
text_color = "#1C1917"
text_color_dark = "#1C1917"
text_color_light = "#F5F5F4"

# =============================================================

class UI:
    def __init__(self, app) -> None:
        self.app = app
        self.screen = app.screen
        self.display = app.display

    def blit(self):
        self.screen.blit(self.display, (0, 0))
        pg.display.flip()


class GameUI(UI):
    def __init__(self, app) -> None:
        super().__init__(app)

    def init_ui(self):
        self.info_surface = pygame.Surface( (200, 80), pygame.SRCALPHA, 32)
        self.top_surface = pygame.Surface(((TSIZE + 7) * self.app.player.inventory_size, TSIZE + 8), pygame.SRCALPHA, 32)
        self.top_bg_color = (82, 82, 91, 150)
        self.app.player.choose_active_cell()

    def draw_sky(self):
        self.display.fill(sky)


    def draw(self):
        # DRAW DISPLAY GAME TO WINDOW ========================================
        
        self.display.blit(self.top_surface, (0, 0))  
        if show_info_menu:      
            self.display.blit(self.info_surface, (WINDOW_SIZE[0]-200, 0))

        # pygame.transform.scale(display,(WINDOW_SIZE[0]//1.8, WINDOW_SIZE[1]//1.8)), (100, 100)
        self.screen.blit(self.display, (0, 0))
        pygame.display.flip()



    def redraw_info(self):
        true_fps = self.app.clock.get_fps()
        self.info_surface.fill(self.top_bg_color)
        text_fps = textfont_info.render(f" fps: {int(true_fps)}", False, "white")
        text_pos_real = textfont_info.render(f"rpos: {self.app.player.rect.x, self.app.player.rect.y}", False, "white")
        text_pos = textfont_info.render(f" pos: {self.app.player.rect.x//TSIZE, self.app.player.rect.y//TSIZE}", False, "white")
        self.info_surface.blit(text_fps, (8, 5))
        self.info_surface.blit(text_pos_real, (8, 25))
        self.info_surface.blit(text_pos, (8, 45))

    def redraw_top(self):
        self.top_surface.fill(self.top_bg_color)
        x = 0
        i = 0
        for i in range(self.app.player.inventory_size):
            color = "#000000"
            if i == self.app.player.active_cell:
                color = "#FFFFFF"
            pygame.draw.rect(self.top_surface, color, 
                (x, 0, TSIZE + 7, TSIZE + 7), 1)
            cell = self.app.player.inventory[i]
            if cell is not None:
                img = tile_imgs[cell[0]]
                self.top_surface.blit(img, (x+3, 3))
                res = str(cell[1])
                tx, ty = (x+TSIZE+3-7*len(res), TSIZE-8)
                text = textfont.render(res, False, text_color_dark)
                self.top_surface.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, False, text_color_light)
                self.top_surface.blit(text, (tx, ty))
            x += TSIZE + 7
