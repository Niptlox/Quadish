from PIL import Image

path = "sword_77"
canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))

im: Image.Image = Image.open(path+".png")

x, y = 64, 64 - im.height
canvas.paste(im, (x, y))
i = 0
path = path + "/" + path + "_"
im.save(path+'.png', quality=100)
for g in range(1):
    for r in (40, 18, 0, -18):
        r -= g * 90
        im_rotate = canvas.rotate(r)
        im_rotate.save(path+f'{i}.png', quality=100)
        i += 1

im.close()