from units.common import *

# CREATING TILE IMAGES ========================================

BORDER_COLOR = "#1C1917"
def create_tile_image(color, bd=1, size=TILE_RECT, bd_color=BORDER_COLOR):
    img = pygame.Surface(size)
    img.fill(bd_color)
    pygame.draw.rect(img, color, ((bd, bd), (size[0]-bd*2, size[0]-bd*2)), border_radius=bd*2)
    return img

COLORKEY = (0, 255, 0)
def load_img(path, size=TILE_RECT, colorkey=COLORKEY):
    img = pygame.image.load(path).convert()
    img = pygame.transform.scale(img, size)
    if colorkey:
        img.set_colorkey(colorkey)
    return img

HAND_SIZE = int(TILE_SIZE//2.5) # 40//2.5== 16
HAND_RECT = (HAND_SIZE, HAND_SIZE)
def transform_hand(surf, size=HAND_RECT): 
    if type(surf) is list:
        surf = [pygame.transform.smoothscale(s, size) for s in surf]
    else:
        surf = pygame.transform.smoothscale(surf, size)
    return surf

sky = "#A5F3FC"

player_img = create_tile_image("#E7E5E4", bd=2)

hand_pass_img = pygame.transform.smoothscale(player_img, HAND_RECT)
player_hand_img = hand_pass_img

dirt_img = create_tile_image("#694837")

grass_img = create_tile_image("#16A34A")

stone_img = create_tile_image("#57534E")

blore_img = create_tile_image("#155E75") # blue ore

bush_img = load_img("data/sprites/tiles/bush.png")

smalltree_img = load_img("data/sprites/tiles/small_tree.png")

table_img = load_img("data/sprites/tiles/table.png")
chear_img = load_img("data/sprites/tiles/chear.png")
water_img = load_img("data/sprites/tiles/water.png")

cloud_img = create_tile_image("#CBD5E1")
cloud_imgs = [create_tile_image((203-i,213-i,230-i)) for i in range(0, 130, 30)]

break_1_img = load_img("data/sprites/tiles/break_1.png")
break_1_img.set_alpha(100)
break_2_img = load_img("data/sprites/tiles/break_2.png")
break_2_img.set_alpha(100)
break_3_img = load_img("data/sprites/tiles/break_3.png")
break_3_img.set_alpha(100)
break_imgs = [break_1_img, break_2_img, break_3_img]


dig_rect_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA, 32)
pygame.draw.rect(dig_rect_img, "#FDE047", ((0, 0), (TILE_SIZE-1, TILE_SIZE-1)),width=2, border_radius=-2)
 


group_img = load_img("data/sprites/tiles/group.png")

rain_img = load_img("data/sprites/tiles/rain.png")


tile_imgs = {1: grass_img, 
             2: dirt_img, 
             3: stone_img,
             4: blore_img,
             101: bush_img,
             102: smalltree_img,
             120: water_img,
             121: table_img,
             122: chear_img,
             151: group_img,
             201: cloud_img,
             202: cloud_imgs,             
             }    
count_tiles = len(tile_imgs)

tile_hand_imgs = {k: transform_hand(i) for k, i in tile_imgs.items()}
tile_hand_imgs[102] = load_img("data/sprites/tiles/small_tree_hand.png", HAND_RECT) #тк есть прозрачность
tile_hand_imgs[121] = load_img("data/sprites/tiles/table_hand.png", HAND_RECT) #тк есть прозрачность
tile_hand_imgs[122] = load_img("data/sprites/tiles/chear_hand.png", HAND_RECT) #тк есть прозрачность

# INIT_TILES ====================================================


PHYSBODY_TILES = {1, 2, 3, 4}

STANDING_TILES = {0, 101, 102, 120, 121, 122}
TILES_SOLIDITY = {
    1: 15,
    2: 20,
    3: 35,
    4: 60,
    101: 25,
    102: 25,
    120: 100,
    121: 100,
    122: 100,

}

# INIT PICKAXE ==================================================

PICKAXES_STRENGTH = {
    1: 5,
    77: 777
}
PICKAXES_SPEED = {
    1: 8,
    77: 777
}
PICKAXES_CAPABILITY = {
    1: [1,2,3,101,102],
    77: None
}
