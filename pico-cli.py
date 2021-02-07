import argparse
import os.path
from getpass import getpass

from miner import Miner
from core import User, Block, Blockchain, Invoice, Payment, Message


def logon(user_json):
    while True:
        password = getpass('Password: ')

        try:
            return User.from_json(user_json, password)
        except:
            print('Invalid password!')


def register():
    print('No user presented, creating new one.')
    password = getpass('Password: ')

    return User.create(password)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PicoCoin core cli.')
    parser.add_argument('--usr', type=str, default='user.json', help='path to user keys')
    parser.add_argument('--serv',  type=bool, default=False, help='work as server')
    parser.add_argument('--adr',  type=str, default='127.0.0.1', help='server listen address (default: "127.0.0.1")')

    args = parser.parse_args()

    # user
    user = None

    if os.path.exists(args.usr):
        with open(args.usr, 'r') as f:
            user = logon(f.read())
    else:
        user = register()
        with open(args.usr, 'w') as f:
            f.write(user.to_json_with_hash(indent=4))

    # blockchain
    chain = Blockchain('0.1')
    miner = Miner()

    # block
    block = Block(0, 14, 256, None, user.get_pub())

    miner.set_block(block)
    miner.work()
    chain.add_block(block)

    print(f'solved: reward {block.reward()} picocoins.')

    # save blockchain to disk
    with open('blockchain.json', 'w') as f:
        f.write(chain.to_json_with_hash(indent=4))
