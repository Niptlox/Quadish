from pygame import Surface
from pygame.constants import MOUSEBUTTONDOWN
from units.Texture import BLACK, WHITE
from units.common import *
from units.Tiles import tile_imgs, sky
from units.UI.Button import Button, createImageButton, createImagesButton, createVSteckButtons


# INIT TEXT ==================================================

pygame.font.init()
# textfont = pygame.font.SysFont('Jokerman', 19)
textfont = pygame.font.SysFont("Fenix", 19, )
# textfont = pygame.font.Font('data/fonts/Teletactile.ttf', 10, bold=True)
textfont_info = pygame.font.Font('data/fonts/Teletactile.ttf', 10, )
textfont_btn = pygame.font.SysFont("Fenix", 35, )

# texframe = font.render(text, False, text_color)
text_color = "#1C1917"
text_color_dark = "#1C1917"
text_color_light = "#F5F5F4"

# =============================================================


class UI:
    def __init__(self, app) -> None:
        self.app = app
        self.screen = app.screen
        self.display = self.app.display

    def init_ui(self):
        pass

    def draw(self):
        self.screen.blit(self.display, (0, 0))
        pg.display.flip()

    def pg_event(self, event: pg.event.Event):
        pass


class GameUI(UI):
    def __init__(self, app) -> None:
        super().__init__(app)

    def init_ui(self):
        super().init_ui()
        self.info_surface = pygame.Surface((200, 80), pygame.SRCALPHA, 32)
        self.top_surface = pygame.Surface(
            ((TSIZE + 7) * self.app.player.inventory_size, TSIZE + 8), pygame.SRCALPHA, 32)
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
        text_fps = textfont_info.render(
            f" fps: {int(true_fps)}", 1, "white")
        text_pos_real = textfont_info.render(
            f"rpos: {self.app.player.rect.x, self.app.player.rect.y}", 1, "white")
        text_pos = textfont_info.render(
            f" pos: {self.app.player.rect.x//TSIZE, self.app.player.rect.y//TSIZE}", 1, "white")
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
                text = textfont.render(res, 1, text_color_dark)
                self.top_surface.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, 1, text_color_light)
                self.top_surface.blit(text, (tx, ty))
            x += TSIZE + 7


class SwitchMapUI(UI):
    bg = BLACK
    def __init__(self, app, title) -> None:
        self.title = title
        super().__init__(app)

    def init_ui(self):
        w, h = 300, 500
        self.rect = pg.Rect(0, 0, w, h)
        self.rect.center = WSIZE[0] // 2, WSIZE[1] // 2
        self.surface = pg.Surface(self.rect.size)
        
        self.title_surf = pg.Surface((w, 40))        
        self.title_surf.blit(textfont_btn.render(self.title, True, WHITE), (10, 10))

        btn_rect = pg.Rect(0, 20 + 35, 200, 35)        
        self.btns_scroll = [(w -btn_rect.w)//2, btn_rect.y]
        self.btns_scroll_step = 20 + btn_rect.height

        n = self.app.game.game_map.save_slots
        imgs = [createImagesButton(btn_rect.size, f"Карта #{i}", font=textfont_btn)
                for i in range(n)]
        self.img_btns = imgs
        funcs = [lambda b, i=i: self.open_map(b, i) for i in range(n)]
        btns = createVSteckButtons(btn_rect.size, btn_rect.centerx, 0, 15, imgs, funcs,
                                    screenOffset=(self.rect.x + self.btns_scroll[0], 
                                    self.rect.y + self.btns_scroll[1]))  # кнопки открывающие карты
        self.btns_rect = pg.Rect(btns[0].rect.x, btns[0].rect.y, btns[-1].rect.right, btns[-1].rect.bottom)
        self.btns_surf = pg.Surface(self.btns_rect.size)        
        self.btns = btns

    def pg_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 5:
                self.btns_scroll[1] -= self.btns_scroll_step
                for btn in self.btns:
                    btn.screenRect.y -= self.btns_scroll_step            
            elif event.button == 4:
                if self.btns_scroll[1] < 0:
                    self.btns_scroll[1] += self.btns_scroll_step
                    for btn in self.btns:
                        btn.screenRect.y += self.btns_scroll_step            
            else:
                if not self.rect.collidepoint(event.pos):
                    return
        for btn in self.btns:
            btn.pg_event(event)

    def draw(self):
        self.surface.fill(self.bg)
        
        for btn in self.btns:
            btn.draw(self.btns_surf)
        self.surface.blit(self.btns_surf, self.btns_scroll)
        self.surface.blit(self.title_surf, (0, 0))
        self.display.blit(self.surface, self.rect)

        self.screen.blit(self.display, (0, 0))
        pygame.display.flip()

    def set_disabled_btns(self, ar):
        for i in range(len(ar)):
            self.btns[i].set_disabled(ar[i])

    def set_check_btns(self, ar):
        check = Surface((10, 10))
        check.fill("#EF4444")
        for i in range(len(ar)):
            if ar[i]:
                img = self.img_btns[i][0].copy()
                img.blit(check, (0, 0))
                self.btns[i].imgUpB = img 
            else:
                self.btns[i].imgUpB = self.img_btns[i][0]

    def open_map(self, but, num):
        res = self.app.open_map(num)
        if not res:
            print("Нету карты")
