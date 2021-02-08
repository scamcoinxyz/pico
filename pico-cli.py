import argparse
import os.path
from getpass import getpass

from miner import Miner
from core import User, Block, Blockchain, Transaction, Invoice, Payment, Message


def get_pass(prefix='Password: '):
    return getpass(prefix)


def login(user_json):
    while True:
        try:
            passwd = get_pass()
            return User.from_json(user_json, passwd)
        except:
            print('Invalid password!')


def register():
    print('No user presented, register new one.')

    while True:
        passwd0 = get_pass()
        passwd1 = get_pass('Repeat password:')

        if passwd0 == passwd1:
            return User.register(passwd0)

        print('Passwords mismatch, please, try again.')


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
            user = login(f.read())
    else:
        user = register()
        with open(args.usr, 'w') as f:
            f.write(user.to_json_with_hash(indent=4))

    # blockchain
    chain = Blockchain('0.1')
    miner = Miner()

    # transactions
    trans = Transaction(user.get_pub(), user.get_pub(), Message('Loopback'))
    trans.sign(user, '1234')

    # block
    block = Block(14, 256, None, user.get_pub())
    block.add_trans(trans)

    miner.set_block(block)
    miner.work()
    chain.add_block(block)

    print(f'solved: reward {block.reward()} picocoins.')

    # save blockchain to disk
    with open('blockchain.json', 'w') as f:
        f.write(chain.to_json_with_hash(indent=4))
