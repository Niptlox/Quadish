import random

trees_pattern = {
    102: [{"chance": 0.5,
           "wood_type": 110, "woods": ((0, 0), (0, -1), (0, -2), (0, -3)),
           "leave_type": 105, "leaves": ((-1, -1), (1, -1), (1, -2), (-1, -2), (1, -3), (-1, -3), (0, -4)),
           },
          {"chance": 0.2,
           "wood_type": 110, "woods": ((0, 0), (0, -1), (0, -2), (0, -3), (0, -4), (0, -5)),
           "leave_type": 105, "leaves": ((-2, -2), (-2, -3), (-2, -4),
                                         (-1, -1), (-1, -2), (-1, -3), (-1, -4), (-1, -5), (-1, -6),
                                         (2, -2), (2, -3), (2, -4),
                                         (1, -1), (1, -2), (1, -3), (1, -4), (1, -5), (1, -6),
                                         (0, -6), (0, -7)),
           },
          ],
    -102: [{"chance": 1,
            "wood_type": 110, "woods": ((0, 0), (0, -1), (0, -2), (0, -3), (0, -4), (0, -5),
                                        (1, 0), (1, -1), (1, -2), (1, -3), (1, -4), (1, -5)
                                        ),
            "leave_type": 105, "leaves": ((-2, -2), (-2, -3), (-2, -4),
                                          (-1, -1), (-1, -2), (-1, -3), (-1, -4), (-1, -5), (-1, -6),
                                          (0, -6), (0, -7),
                                          (1, -6), (1, -7),
                                          (3, -2), (3, -3), (3, -4),
                                          (2, -1), (2, -2), (2, -3), (2, -4), (2, -5), (2, -6)),
            }

           ]
}


def grow_tree(pos, game_map, tile_type=102, rec=0):
    right_ttile = game_map.get_static_tile_type(pos[0] + 1, pos[1])
    if right_ttile == tile_type:
        tile_type *= -1

    idx = random.choices(list(range(len(trees_pattern[tile_type]))),
                         [el["chance"] for el in trees_pattern[tile_type]])[0]
    leaves = trees_pattern[tile_type][idx]["leaves"]
    leave_type = trees_pattern[tile_type][idx]["leave_type"]
    woods = trees_pattern[tile_type][idx]["woods"]
    wood_type = trees_pattern[tile_type][idx]["wood_type"]
    x, y = pos
    for ax, ay in woods:
        game_map.set_static_tile(x + ax, y + ay, game_map.get_tile_ttile(wood_type))
    for ax, ay in leaves:
        if game_map.get_static_tile_type(x + ax, y + ay, default=0) == 0:
            game_map.set_static_tile(x + ax, y + ay, game_map.get_tile_ttile(leave_type))

    if tile_type == -102 and rec < 5:
        print(pos)

        grow_tree((pos[0], pos[1] -6), game_map, tile_type=tile_type, rec=rec+1)
