from units.common import *

BORDER_COLOR = "#1C1917"


def create_tile_image(color, bd=1, size=TILE_RECT, bd_color=BORDER_COLOR):
    size = max(size[0], 1), max(size[1], 1)
    img = pygame.Surface(size)
    img.fill(bd_color)
    pygame.draw.rect(img, color, ((bd, bd), (size[0] - bd * 2, size[0] - bd * 2)), border_radius=bd * 2)
    return img


def create_border(surface, bd=1, size=TILE_RECT, bd_color=BORDER_COLOR):
    pygame.draw.rect(surface, bd_color, ((0, 0), (size[0], size[1])), width=bd)
    return surface


COLORKEY = (0, 255, 0)

SIZE_2X = "2x"


def load_img(path, size=TILE_RECT, colorkey=COLORKEY, alpha=None, scale=1, is_tile=False):
    print(path)
    img = pygame.image.load(path)
    return convert_img(img, size, colorkey, alpha, scale, is_tile)


def convert_img(img, size=TILE_RECT, colorkey=COLORKEY, alpha=None, scale=1, is_tile=False):
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
        img.convert_alpha()
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
