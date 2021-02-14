import json
import argparse
import os.path
from getpass import getpass
from threading import Thread, Lock

from miner import Miner
from core import User, Net, Transaction, Invoice, Payment, Message, Block, Blockchain


class CLI:
    def __init__(self):
        self.net = None
        self.usr = None
        self.chain = None

    @staticmethod
    def _dict_to_disk(obj, obj_path):
        with open(obj_path, 'w') as f:
            obj_json = json.dumps(obj.to_dict(), indent=4)
            f.write(obj_json)

    @staticmethod
    def _dict_from_disk(obj_path):
        with open(obj_path, 'r') as f:
            return json.loads(f.read())

    @staticmethod
    def _init_ser_obj(obj_path, obj_reader, obj_maker):
        obj = None
        if os.path.exists(obj_path):
            obj = obj_reader(CLI._dict_from_disk(obj_path))
        else:
            obj = obj_maker()
            CLI._dict_to_disk(obj, obj_path)
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
    def act_with_passwd(act):
        while True:
            try:
                passwd = getpass('Password: ')
                return act(passwd)
            except KeyboardInterrupt:
                exit()
            except:
                print('Invalid password!')

    @staticmethod
    def gen_passwd():
        while True:
            try:
                passwd0 = getpass('Password: ')
                passwd1 = getpass('Repeat password:')

                if passwd0 == passwd1:
                    return passwd0

                print('Passwords mismatch, please, try again.')
            except KeyboardInterrupt:
                exit()

    def passwd(self):
        return CoreServer.act_with_passwd(self.usr.check_passwd)

    @staticmethod
    def usr_login(usr_dict):
        act = lambda passwd: User.from_dict(usr_dict, passwd)
        return CoreServer.act_with_passwd(act)

    @staticmethod
    def usr_reg():
        print('No user presented, register new one.')
        return User.create(CoreServer.gen_passwd())

    def make_trans(self, trans):
        ans = input('Do u want to make a transaction? [y/n]: ')
        if ans in ('y', 'Y'):
            trans.sign(self.usr, self.passwd())
            self.net.send({'trans': trans.to_dict()})
            print(trans.to_dict())

    def update_self_peer(self):
        self.net.update_peer(self.net.ipv6, 10000)
        self.net.send({'peer': {'ipv6': self.net.ipv6, 'port': 10000}})
        self._dict_to_disk(self.net, 'peers.json')

class CoreServer(CLI):
    def __init__(self):
        super().__init__()
        self.mtx = Lock()

    def add_peer_hlr(self, peer_dict):
        ipv6 = peer_dict['ipv6']
        port = peer_dict['port']

        if self.net.update_peer(ipv6, port):
            print(f"Peer {ipv6} {port} added.")
            self._dict_to_disk(self.net, 'peers.json')

    def add_block_hlr(self, block_dict):
        block = Block.from_dict(block_dict)

        if self.chain.check_block(block) is Blockchain.CHECK_BLOCK_OK:
            self.net.send({'block': block.to_dict()})

            if self.chain.add_block(block):
                self._dict_to_disk(self.chain, 'blockchain.json')

    def serve_dispatch(self, data):
        # add peer
        if data.get('peer') is not None:
            self.add_peer_hlr(data['peer'])

        # add block
        if data.get('block') is not None:
            self.add_block_hlr(data['block'])

    def serve_forever(self):
        while True:
            with self.mtx:
                data = self.net.recv()
                self.serve_dispatch(data)


class MiningServer(CoreServer):
    def __init__(self):
        super().__init__()
        self.block = None
        self.miner = Miner()
        self.trans_cache = []

    def make_trans(self, trans):
        super().make_trans(trans)

        if self.block is None:
            self.update_block()

        self.trans_cache.append(trans)

    def update_block(self):
        prev = self.chain.last_block()

        if prev is not None:
            h_diff = prev.h_diff + (1 if self.chain.blocks_count() % 10000 == 0 else 0)
            self.block = Block(h_diff, prev.hash().hexdigest(), self.usr.pub)
        else:
            self.block = Block(14, None, self.usr.pub)

    def add_trans_hlr(self, trans_dict):
        trans = Transaction.from_dict(trans_dict)

        if self.block is None:
            self.update_block()

        print(f'Transaction {trans.hash().hexdigest()[0:12]} accepted.')
        self.trans_cache.append(trans)

    def serve_dispatch(self, data):
        super().serve_dispatch(data)

        # add trans
        if data.get('trans') is not None:
            self.add_trans_hlr(data['trans'])

    def serve_mining(self):
        while True:
            self.update_block()

            with self.mtx:
                for trans in self.trans_cache:
                    self.block.add_trans(trans)
                self.trans_cache.clear()

            # mining
            self.miner.set_block(self.block)
            self.miner.work()
            print(f'Block {self.block.hash().hexdigest()[0:12]} solved: reward {self.block.reward()} picocoins.')

            with self.mtx:
                if self.chain.add_block(self.block):
                    self._dict_to_disk(self.chain, 'blockchain.json')
                self.net.send({'block': self.block.to_dict()})

    def serve_forever(self):
        t = Thread(target=self.serve_mining)

        t.start()
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
