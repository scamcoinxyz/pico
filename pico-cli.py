import argparse
import core


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PicoCoin core cli.')
    parser.add_argument('--serv',  type=bool, default=False, help='work as server')
    parser.add_argument('--adr',  type=str, default='127.0.0.1', help='server listen address (default: "127.0.0.1")')

    args = parser.parse_args()
