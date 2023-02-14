from units.Graphics.Texture import *
from units.sound import sound_click
from units.UI.Translate import get_translated_text, get_translated_lst_text

DARK = "#27272A"
DEF_COLOR_SCHEME_BUT = ((WHITE, GRAY, DARK), (BLACK, BLACK, WHITE))


def openImagesButton(nameImg: str, colorkey=COLORKEY):
    path, extension = os.path.splitext(nameImg)
    imgUp = load_image(path + "_up" + extension, colorkey)
    imgIn = load_image(path + "_in" + extension, colorkey)
    imgDown = load_image(path + "_down" + extension, colorkey)
    return imgUp, imgIn, imgDown


def createImageButton(size, text="", bg=BLACK, font=TEXTFONT_BTN, text_color=WHITE, colorkey=COLORKEY, border=3):
    text = get_translated_text(text)
    surf = get_texture_size(bg, size, colorkey=colorkey)
    if border:
        surf.fill("black")
        pygame.draw.rect(surf, bg, (border, 0, size[0] - border * 2, size[1]))

    textframe = font.render(text, True, text_color)
    textframe_rect = pygame.Rect(((0, 0), textframe.get_size()))
    # print("texframe_rect.center", texframe_rect, size)
    textframe_rect.center = size[0] // 2, size[1] // 2
    surf.blit(textframe, textframe_rect)
    return surf


def createImagesButton(size, text="", color_schema=DEF_COLOR_SCHEME_BUT, font=TEXTFONT_BTN, colorkey=COLORKEY):
    # print("color_schema", [(bg, colort) for bg, colort in zip(color_schema[0], color_schema[1])])
    imgs_but = [createImageButton(size, text, bg, font=font, text_color=colort, colorkey=colorkey)
                for bg, colort in zip(color_schema[0], color_schema[1])]
    return imgs_but


def createVSteckButtons(size, center_x, start_y, step, images_buttons, funcs, screen_position=(0, 0)):
    y = start_y
    x = center_x - size[0] // 2
    step += size[1]
    buts = []
    for images_button, func in zip(images_buttons, funcs):
        but = Button(func, ((x, y), size), *images_button, screenXY=(screen_position[0] + x, screen_position[1] + y))
        y += step
        buts.append(but)
    return buts


def createVSteckTextButtons(size, center_x, start_y, step, text_func_buttons, screen_position=(0, 0),
                            color_schema=DEF_COLOR_SCHEME_BUT, font=TEXTFONT_BTN):
    y = start_y
    x = center_x - size[0] // 2
    step += size[1]
    buts = []
    for _btn in text_func_buttons:
        if isinstance(_btn, TextButton):
            but = _btn
            but.rect = pygame.Rect((x, y), size)
            but.screenRect = pygame.Rect((screen_position[0] + x, screen_position[1] + y), size)
            but.color_schema = color_schema
            but.font = font
            but.redraw_text()
        else:
            text_button, func = _btn
            but = TextButton(func, ((x, y), size), text_button,
                             screenXY=(screen_position[0] + x, screen_position[1] + y),
                             color_schema=color_schema, font=font)
        y += step
        buts.append(but)
    return buts


class Button(pygame.sprite.Sprite):
    # image = load_image("bomb.png")
    # image_boom = load_image("boom.png")

    def __init__(self, func, rect, imgUpB, imgInB=None, imgDownB=None, group=None, screenXY=None, disabled=False):
        """func, rect, imgUpB, imgInB=None, imgDownB=None, group=None, screenXY=None, disabled=False
        вызов func(button) - по пораметру передаёться кнопка"""
        # если рамеры == -1 то берётся размер кнопки
        self.func = func
        if group is not None:
            super().__init__(group)
        else:
            super().__init__()
        self.rect = rect = pygame.Rect(rect)
        xy = self.rect.x, self.rect.y
        if self.rect.w == -1 and self.rect.h == -1:
            size = None
        else:
            size = rect.size
        self.imgUpB = get_texture(imgUpB, colorkey=COLORKEY)
        self.image = self.imgUpB
        imgDownB = self.imgUpB if imgDownB is None else imgDownB
        imgInB = imgDownB if imgInB is None else imgInB
        self.imgDownB = get_texture(imgDownB, colorkey=COLORKEY)
        self.imgInB = get_texture(imgInB, colorkey=COLORKEY)
        self.disabled = disabled
        self.mauseInButton = False
        self.mauseDownButton = False
        if size is None:
            self.rect = self.image.get_rect()
            self.rect.x, self.rect.y = xy
        else:
            self.rect = pygame.Rect(xy, size)
            self.imgUpB = pygame.transform.scale(self.imgUpB, self.rect.size)
            self.imgDownB = pygame.transform.scale(self.imgDownB, self.rect.size)
            self.imgInB = pygame.transform.scale(self.imgInB, self.rect.size)
        if not disabled:
            self.image = self.imgUpB
        else:
            self.image = self.imgDownB
        self.screenRect = self.rect if screenXY is None else pygame.Rect(screenXY, self.rect.size)
        # self.screenXY = screenXY

    def setXY(self, xy):
        x, y = xy
        ax, ay = x - self.rect.x, y - self.rect.y
        self.rect.move_ip(*xy)
        if self.rect is not self.screenRect:
            sx, sy = self.screenRect.x + ax, self.screenRect.y + ay
            self.screenRect.move_ip(sx, sy)

    def pg_event(self, event):
        if self.disabled:
            return
        but = 1
        if event.type == pygame.MOUSEBUTTONUP and event.button == but:
            if self.mauseDownButton:
                self.click()
            self.mauseDownButton = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == but:
            if self.screenRect.collidepoint(event.pos):
                self.mauseInButton = True
                self.mauseDownButton = True
        if event.type == pygame.MOUSEMOTION:
            if self.mauseInButton:
                if not self.screenRect.collidepoint(event.pos):
                    self.mauseInButton = False
                    self.mauseDownButton = False
            else:
                if self.screenRect.collidepoint(event.pos):
                    self.mauseInButton = True
        self.redraw()

    def update(self, *args) -> None:
        if args:
            event = args[0]
            self.pg_event(event)

    def click(self):
        if self.func:
            sound_click.play()
            self.mauseInButton = False
            self.mauseDownButton = False
            self.redraw()
            self.func(self)
        else:
            print("Button down, but function not defined!!!")

    def inButton(self):
        if self.imgInB:
            self.image = self.imgInB

    def redraw(self):
        """update my image (not draw)"""
        if self.disabled:
            self.image = self.imgDownB
        elif self.mauseDownButton:
            self.image = self.imgDownB
        elif self.mauseInButton:
            self.image = self.imgInB
        else:
            self.image = self.imgUpB

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def set_disabled(self, dsb):
        self.disabled = dsb
        self.redraw()


class TextButton(Button):
    def __init__(self, func, rect, text, group=None, screenXY=None, disabled=False, color_schema=DEF_COLOR_SCHEME_BUT,
                 font=TEXTFONT_BTN):
        rect = pygame.Rect(rect)
        tr_text = get_translated_text(text)
        self.text = tr_text
        self.color_schema = color_schema
        self.font = font
        imgUpB, imgInB, imgDownB = createImagesButton(rect.size, tr_text, color_schema=color_schema, font=font)
        super(TextButton, self).__init__(func, rect, imgUpB, imgInB, imgDownB, group=group, screenXY=screenXY,
                                         disabled=disabled)

    def set_text(self, text):
        self.text = get_translated_text(text)
        self.redraw_text()

    def redraw_text(self):
        self.imgUpB, self.imgInB, self.imgDownB = createImagesButton(self.rect.size, self.text,
                                                                     color_schema=self.color_schema,
                                                                     font=self.font)
        self.redraw()


class ChangeTextButton(TextButton):
    def __init__(self, func, rect, text: str, group=None, screenXY=None, disabled=False,
                 states_text_lst=[], start_state_index=0, start_state_text=None,
                 color_schema=DEF_COLOR_SCHEME_BUT, font=TEXTFONT_BTN):
        tr_text = get_translated_text(text)
        self.format_text = tr_text
        self.states_text_lst = get_translated_lst_text(states_text_lst)
        if start_state_text:
            start_state_index = self.states_text_lst.index(start_state_text)
        self.state_index = start_state_index
        tr_text = tr_text.format(self.states_text_lst[start_state_index])
        n_func = lambda btn: self.change_state(btn, func)
        super(ChangeTextButton, self).__init__(n_func, rect, tr_text, group=group, screenXY=screenXY, disabled=disabled,
                                               color_schema=color_schema, font=font)

    def change_state(self, btn, func):
        self.state_index = (self.state_index + 1) % len(self.states_text_lst)
        state = self.states_text_lst[self.state_index]
        self.set_text(self.format_text.format(state))
        func(btn, state)
