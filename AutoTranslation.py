from units.Tiles import original_tile_words

if __name__ == '__main__':

    print("tile_words = ")
    print(*list(original_tile_words.values()), sep=";")
    translate_tiles_list = input("translate_tiles = ").split(";")
    print("translate_tiles_json")
    print(str({rus: eng for rus, eng in zip(original_tile_words.values(), translate_tiles_list)}).replace("'", '"'))
