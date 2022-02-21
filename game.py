import units.Game
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    game = units.Game.Game()
    game.main()


if __name__ == "__main__":
    main()
