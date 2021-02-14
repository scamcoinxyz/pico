import json
import argparse
import os.path
from getpass import getpass

from miner import Miner
from core import User, Net, Transaction, Invoice, Payment, Message, Block, Blockchain


class CoreServer:
    def __init__(self):
        self.net = None
        self.usr = None
        self.chain = None

    @staticmethod
    def _init_ser_obj(obj_path, obj_reader, obj_maker):
        obj = None
        if os.path.exists(obj_path):
            with open(obj_path, 'r') as f:
                obj_dict = json.loads(f.read())
                obj = obj_reader(obj_dict)
        else:
            obj = obj_maker()
            with open(obj_path, 'w') as f:
                obj_json = json.dumps(obj.to_dict(), indent=4)
                f.write(obj_json)
        return obj

    def net_init(self, peers_path):
        def maker():
            net = Net()
            net.add_peer('2002:c257:6f39::1', 10000)
            net.add_peer('2002:c257:65d4::1', 10000)
            return net

        reader = lambda d: Net.from_dict(d)
        self.net = CoreServer._init_ser_obj(peers_path, reader, maker)
        self.update_self_peer()

    def usr_init(self, usr_path):
        reader = lambda d: CoreServer.usr_login(d)
        maker = CoreServer.usr_reg
        self.usr = CoreServer._init_ser_obj(usr_path, reader, maker)

    def chain_init(self, chain_path):
        reader = lambda d: Blockchain.from_dict(d)
        maker = lambda: Blockchain('0.1') # FIXME: fetch blockchain from another node
        self.chain = CoreServer._init_ser_obj(chain_path, reader, maker)

    @staticmethod
    def usr_login(usr_dict):
        while True:
            try:
                passwd = getpass('Password: ')
                return User.from_dict(usr_dict, passwd)
            except KeyboardInterrupt:
                exit()
            except:
                print('Invalid password!')

    @staticmethod
    def usr_reg():
        print('No user presented, register new one.')

        while True:
            try:
                passwd0 = getpass('Password: ')
                passwd1 = getpass('Repeat password:')

                if passwd0 == passwd1:
                    return User.create(passwd0)

                print('Passwords mismatch, please, try again.')
            except KeyboardInterrupt:
                exit()

    def make_trans(self, trans):
        ans = input('Do u want to make a transaction? [y/n]: ')
        if ans in ('y', 'Y'):
            trans.sign(self.usr, getpass('Password: '))
            self.net.send({'trans': trans.to_dict()})
            print(trans.to_dict())

    def add_peer_hlr(self, peer_dict):
        ipv6 = peer_dict['ipv6']
        port = peer_dict['port']

        if self.net.update_peer(ipv6, port):
            print(f"Peer {ipv6} {port} added.")

        with open('peers.json', 'w') as f:
            net_json = json.dumps(self.net.to_dict(), indent=4)
            f.write(net_json)

    def add_block_hlr(self, block_dict):
        block = Block.from_dict(block_dict)

        if block.work_check() and self.chain.get_block(block.hash().hexdigest()) is None:
            self.net.send({'block': block.to_dict()})

        if self.chain.add_block(block):
            with open('blockchain.json', 'w') as f:
                chain_json = json.dumps(self.chain.to_dict(), indent=4)
                f.write(chain_json)

    def serve_forever(self):
        while True:
            data = self.net.recv()

            # add peer
            if data.get('peer') is not None:
                self.add_peer_hlr(data['peer'])

            # add block
            if data.get('block') is not None:
                self.add_block_hlr(data['block'])

    def update_self_peer(self):
        self.net.update_peer(self.net.ipv6, 10000)
        self.net.send({'peer': {'ipv6': self.net.ipv6, 'port': 10000}})

        with open('peers.json', 'w') as f:
            net_json = json.dumps(self.net.to_dict(), indent=4)
            f.write(net_json)


class MiningServer(CoreServer):
    def __init__(self):
        super().__init__()
        self.block = None
        self.miner = Miner()

    def make_trans(self, trans):
        super().make_trans(trans)

        if self.block is None:
            self.update_block()

        self.block.add_trans(trans)

    def update_block(self):
        prev = self.chain.last_block()

        if prev is not None:
            h_diff = prev.h_diff + (1 if self.chain.blocks_count() % 10000 == 0 else 0)
            self.block = Block(h_diff, prev.hash().hexdigest(), self.usr.pub)
        else:
            self.block = Block(14, None, self.usr.pub)

    def serve_mining(self):
        self.update_block()

        # mining
        self.miner.set_block(self.block)
        self.miner.work()
        print(f'Block {self.block.hash().hexdigest()[0:12]} solved: reward {self.block.reward()} picocoins.')

        self.chain.add_block(self.block)
        self.net.send({'block': self.block.to_dict()})

    def serve_forever(self):
        self.serve_mining()
        super().serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='python3 pico-cli.py', description='PicoCoin core cli.')
    parser.add_argument('--usr', type=str, default='user.json', help='path to user keys')
    parser.add_argument('--chain', type=str, default='blockchain.json', help='path to blockchain')
    parser.add_argument('--peers', type=str, default='peers.json', help='path to peers')
    parser.add_argument('--mining', action='store_true', help='work as mining server')
    parser.add_argument('--adr',  type=str, default='127.0.0.1', help='server listen address (default: "127.0.0.1")')
    parser.add_argument('--trans', nargs=3, metavar=('to', 'act', 'args'), help='make a transaction')

    args = parser.parse_args()

    # init core server
    serv = CoreServer() if not args.mining else MiningServer()

    serv.net_init(args.peers)
    serv.usr_init(args.usr)
    serv.chain_init(args.chain)

    # make transaction
    if args.trans is not None:
        to = args.trans[0]
        act_args = args.trans[2]
 
        act = {
            'ivc': lambda: Invoice(int(act_args)),
            'pay': lambda: Payment(int(act_args)),
            'msg': lambda: Message(act_args)
        }[args.trans[1]]()

        trans = Transaction(serv.usr.pub, to, act)
        serv.make_trans(trans)

    # serve
    serv.serve_forever()
