import argparse
import os.path
from getpass import getpass

from miner import Miner
from core import User, Net, Blockchain, Block , Transaction, Invoice, Payment, Message


def get_pass(prompt='Password: '):
    return getpass(prompt)


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
            return User.create(passwd0)

        print('Passwords mismatch, please, try again.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='python3 pico-cli.py', description='PicoCoin core cli.')
    parser.add_argument('--usr', type=str, default='user.json', help='path to user keys')
    parser.add_argument('--chain', type=str, default='blockchain.json', help='path to blockchain')
    parser.add_argument('--peers', type=str, default='peers.json', help='path to peers')
    parser.add_argument('--mining',  type=bool, default=False, help='work as mining server')
    parser.add_argument('--adr',  type=str, default='127.0.0.1', help='server listen address (default: "127.0.0.1")')
    parser.add_argument('--trans', nargs=3, metavar=('to', 'act', 'args'), help='make a transaction')

    args = parser.parse_args()

    # peers
    net = None

    if os.path.exists(args.peers):
        with open(args.peers, 'r') as f:
            net = Net.from_json(f.read())
    else:
        # FIXME: fetch peers from another node
        net = Net()
        with open('peers.json', 'w') as f:
            f.write(net.to_json_with_hash(indent=4))

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
    chain = None

    if os.path.exists(args.chain):
        with open(args.chain, 'r') as f:
            chain = Blockchain.from_json(f.read())
    else:
        # FIXME: fetch blockchain from another node
        chain = Blockchain('0.1')
        with open('blockchain.json', 'w') as f:
            f.write(chain.to_json_with_hash(indent=4))

    # miner
    miner = Miner()

    # transactions
    trans = None
    if args.trans is not None:
        to = args.trans[0]
        act_args = args.trans[2]
 
        act = {
            'ivc': lambda: Invoice(int(act_args)),
            'pay': lambda: Payment(int(act_args)),
            'msg': lambda: Message(act_args)
        }[args.trans[1]]()

        trans = Transaction(user.pub, to, act)

        ans = input('Do u want to make a transaction? [y/n]: ')
        if ans in ('y', 'Y'):
            trans.sign(user, get_pass())
            print(trans.to_json_with_hash())
        else:
            trans = None

    # block
    prev = chain.last_block()
    block = None

    if prev is not None:
        h_diff = prev.h_diff + (1 if chain.blocks_count() % 10000 == 0 else 0)
        block = Block(h_diff, prev.hash().hexdigest(), user.pub)
    else:
        block = Block(14, None, user.pub)

    if trans is not None:
        block.add_trans(trans)
        net.send_trans(trans)

    # mining
    miner.set_block(block)
    miner.work()

    chain.add_block(block)
    net.send_block(block)

    print(f'solved: reward {block.reward()} picocoins.')

    with open('blockchain.json', 'w') as f:
        f.write(chain.to_json_with_hash(indent=4))
