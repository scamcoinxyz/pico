import argparse
from miner import Miner

from core import User, Block, Payment, ProofOfWork


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PicoCoin official miner.')
    parser.add_argument('--mining-adr',  type=str, default='127.0.0.1', help='mining server address (default: "127.0.0.1")')

    args = parser.parse_args()

    # fake data
    user0 = User.create('1234')
    user1 = User.create('1234')

    block = Block(0, 14, 256)
    block.add_trans(Payment(user0, user1.get_pub(), 10))

    miner = Miner(block)
    miner.work()

    print(block.pow.work_check())
    print(block.to_json_with_hash())
    print(f'solved: reward {block.reward} picocoins.')
