from PIL import Image

# from units.biomes import biome_colors

biome_colors = [
    [255, 255, 178],
    [184, 200, 98],
    [188, 161, 53],
    [190, 255, 242],
    [106, 144, 38],
    [33, 77, 41],
    [86, 179, 106],
    [34, 61, 53],
    [35, 114, 94]
]


def replace_color(img, color, new_color):
    color = tuple(color)
    new_color = tuple(new_color)
    w, h = img.size
    for x in range(w):
        for y in range(h):
            if img.getpixel((x, y)) == color:
                img.putpixel((x, y), new_color)


def create_ground():
    path = "../data/sprites/tiles/ground/"
    path_imgs = [path + "ground", path + "ground_L", path + "ground_LR", path + "ground_R"]
    i = 0
    for color in biome_colors:
        for p in path_imgs:
            print(p + ".png")
            img = Image.open(p + ".png")
            replace_color(img, (105, 72, 55), color)
            img.save(f"{p}_{i}.png")
        i += 1


if __name__ == "__main__":
    create_ground()
