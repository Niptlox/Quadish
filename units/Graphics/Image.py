from units.common import *

BORDER_COLOR = "#1C1917"


def create_tile_image(color, bd=1, size=TILE_RECT, bd_color=BORDER_COLOR):
    size = max(size[0], 1), max(size[1], 1)
    img = pygame.Surface(size).convert()
    img.fill(bd_color)
    pygame.draw.rect(img, color, ((bd, bd), (size[0] - bd * 2, size[0] - bd * 2)), border_radius=bd * 2)
    return img


def create_border(surface, bd=1, size=TILE_RECT, bd_color=BORDER_COLOR):
    pygame.draw.rect(surface, bd_color, ((0, 0), (size[0], size[1])), width=bd)
    return surface


COLORKEY = (0, 255, 0)

SIZE_2X = "2x"


def create_player_sprite(size=None):
    """Процедурный игрок примитивами (лицом вправо): голова, тело, ноги."""
    w, h = size or (TSIZE - 10, TSIZE - 2)
    s = pygame.Surface((w, h)).convert_alpha()
    s.fill((0, 0, 0, 0))
    skin = (242, 205, 165)
    hair = (92, 64, 42)
    shirt = (60, 120, 180)
    pants = (52, 58, 80)
    boots = (40, 40, 46)
    outline = (26, 22, 20)
    head_h = max(6, int(h * 0.36))
    body_h = max(6, int(h * 0.40))
    leg_top = head_h + body_h
    leg_w = max(2, w // 2 - 1)
    # ноги и ботинки
    pygame.draw.rect(s, pants, (1, leg_top, leg_w, h - leg_top - 3))
    pygame.draw.rect(s, pants, (w - 1 - leg_w, leg_top, leg_w, h - leg_top - 3))
    pygame.draw.rect(s, boots, (1, h - 3, leg_w, 3))
    pygame.draw.rect(s, boots, (w - 1 - leg_w, h - 3, leg_w, 3))
    # торс
    pygame.draw.rect(s, shirt, (0, head_h, w, body_h + 1), border_radius=3)
    # голова
    hw = int(w * 0.82)
    hx = (w - hw) // 2
    pygame.draw.rect(s, skin, (hx, 1, hw, head_h + 1), border_radius=4)
    pygame.draw.rect(s, hair, (hx, 1, hw, max(3, head_h // 3)),
                     border_top_left_radius=4, border_top_right_radius=4)
    # глаз (смотрит вправо)
    pygame.draw.rect(s, outline, (hx + int(hw * 0.55), 1 + int(head_h * 0.45), 3, 4))
    pygame.draw.rect(s, outline, (0, 0, w, h), width=1, border_radius=3)
    return s


def create_hand_sprite(diameter=None):
    """Кисть руки — кружок телесного цвета."""
    d = max(6, diameter or HAND_SIZE)
    r = d // 2
    s = pygame.Surface((d, d)).convert_alpha()
    s.fill((0, 0, 0, 0))
    pygame.draw.circle(s, (26, 22, 20), (r, r), r)
    pygame.draw.circle(s, (242, 205, 165), (r, r), r - 1)
    return s


def load_img(path, size=TILE_RECT, colorkey=COLORKEY, alpha=None, scale=1, is_tile=False):
    # виндовые пути с '\' приводим к универсальным '/'
    path = path.replace("\\", "/")
    img = pygame.image.load(path)
    return convert_img(img, size, colorkey, alpha, scale, is_tile)


def convert_img(img, size=TILE_RECT, colorkey=COLORKEY, alpha=None, scale=1, is_tile=False):
    # Конвертация в формат экрана обязательна: без неё каждый blit
    # конвертирует пиксели заново, что роняет FPS в разы.
    if img.get_flags() & pygame.SRCALPHA:
        img = img.convert_alpha()
    else:
        img = img.convert()
    if size == SIZE_2X:
        img = pygame.transform.scale2x(img)
    elif size:
        img = pygame.transform.scale(img, size)
    if img.get_width() > TSIZE and is_tile:
        img = pygame.transform.scale(img, TILE_RECT)
    if colorkey:
        img.set_colorkey(colorkey)
    if scale == 2:
        img = pygame.transform.scale2x(img)
    if alpha:
        img.set_alpha(alpha)
    return img


def load_imgs(path, count, size=TILE_RECT, colorkey=COLORKEY, alpha=None, scale=1, is_tile=False, start_num=0):
    return [load_img(path.format(i), size, colorkey, alpha, scale=scale, is_tile=is_tile) for i in
            range(start_num, start_num + count)]


def load_imgs_of_animation(path, table, count, size=None, colorkey=COLORKEY, alpha=None, scale=1, is_tile=False,
                           convert_alpha=True):
    img = pg.image.load(path)
    img_size = img.get_size()
    wc, hc = img_size[0] // table[0], img_size[1] // table[1]
    images = []
    c = 0
    for y in range(0, img_size[1], hc):
        for x in range(0, img_size[0], wc):
            c_img = img.subsurface((x, y, wc, hc))
            if convert_alpha:
                c_img = c_img.convert()
            images.append(convert_img(c_img, size, colorkey, alpha, scale, is_tile))
            c += 1
            if c >= count:
                break
        if c >= count:
            break
    return images


def load_round_tool_imgs(path, count=4, colorkey=COLORKEY, alpha=None, rotate_imgs=True):
    cell_img = load_img(path.format(""), None, colorkey=colorkey)
    imgs = load_imgs(path, count, None, colorkey, alpha)
    if rotate_imgs:
        imgs = imgs + [pg.transform.rotate(im, -90 * i) for i in range(1, 4) for im in imgs]

    return cell_img, imgs
