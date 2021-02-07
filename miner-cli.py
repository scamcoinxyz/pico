import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PicoCoin official miner.')
    parser.add_argument('--mining-adr',  type=str, default='127.0.0.1', help='mining server address (default: "127.0.0.1")')

    args = parser.parse_args()
