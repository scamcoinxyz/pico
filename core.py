import zlib
import json
import base58
import socket
import hashlib as hlib

from queue import Queue
from functools import reduce
from abc import abstractmethod
from sympy.ntheory import isprime
from datetime import datetime as dt

from Crypto.Cipher import AES
from ecdsa import SigningKey, VerifyingKey, SECP256k1


h_diff_init = 14
block_confirms_count = 6


class DictHashable:
    @abstractmethod
    def to_dict_without_hash(self):
        pass

    @staticmethod
    @abstractmethod
    def from_dict_without_hash(obj_dict,*args, **kwargs):
        pass

    @classmethod
    def from_dict(cls, obj_dict, *args, **kwargs):
        obj = cls.from_dict_without_hash(obj_dict, *args, **kwargs)

        expected_hash = obj_dict['hash']
        if expected_hash != obj.hash().hexdigest():
            raise ValueError('Invalid hash!', obj_dict)
        return obj

    def to_dict(self):
        d = self.to_dict_without_hash()
        d['hash'] = self.hash().hexdigest()
        return d

    def hash(self):
        self_json = json.dumps(self.to_dict_without_hash()).encode()
        return hlib.sha3_256(self_json)


class DictSignable(DictHashable):
    def __init__(self, pub):
        self.pub = pub
        self._sign = None

    @abstractmethod
    def to_dict_without_sign(self):
        pass

    def sign(self, user, password):
        msg = json.dumps(self.to_dict_without_sign()).encode()
        self._sign = user.sign(msg, password)
        return self._sign

    def verify(self):
        msg = json.dumps(self.to_dict_without_sign()).encode()
        user = User(None, self.pub)
        user.verify(msg, self._sign)

    def to_dict_without_hash(self):
        d = self.to_dict_without_sign()
        d['sign'] = self._sign
        return d


class User(DictHashable):
    def __init__(self, priv, pub):
        self.priv = priv
        self.pub = pub

    @staticmethod
    def _encrypt_priv(priv, password):
        h = hlib.sha3_256(password.encode())
        cipher = AES.new(h.digest(), AES.MODE_GCM)

        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(base58.b58decode(priv))

        return base58.b58encode(nonce + ciphertext + tag)

    @staticmethod
    def _decrypt_priv(e_priv, password):
        e_priv_raw = base58.b58decode(e_priv)

        h = hlib.sha3_256(password.encode())
        cipher = AES.new(h.digest(), AES.MODE_GCM, nonce=e_priv_raw[0:16])

        priv_raw = cipher.decrypt_and_verify(e_priv_raw[16:48], e_priv_raw[48:64])

        return base58.b58encode(priv_raw).decode()

    def check_passwd(self, password):
        self._decrypt_priv(self.priv, password)
        return password

    @staticmethod
    def create(password):
        priv_raw = SigningKey.generate(curve=SECP256k1)
        pub_raw = priv_raw.get_verifying_key()

        priv = base58.b58encode(priv_raw.to_string()).decode()
        pub = base58.b58encode(pub_raw.to_string()).decode()

        e_priv = User._encrypt_priv(priv, password).decode()

        return User(e_priv, pub)

    def to_dict_without_hash(self):
        data = {
            'pub': self.pub,
            'priv': self.priv
        }
        return data

    @staticmethod
    def from_dict_without_hash(usr_dict, password):
        User._decrypt_priv(usr_dict['priv'], password)
        return User(usr_dict['priv'], usr_dict['pub'])

    def sign(self, msg, password):
        h = hlib.sha3_256(msg).digest()

        _priv = self._decrypt_priv(self.priv, password)
        priv = SigningKey.from_string(base58.b58decode(_priv), curve=SECP256k1)

        return base58.b58encode(priv.sign(h)).decode()

    def verify(self, msg, sign):
        h = hlib.sha3_256(msg).digest()

        pub = VerifyingKey.from_string(base58.b58decode(self.pub), curve=SECP256k1)
        pub.verify(base58.b58decode(sign), h)


class Invoice:
    def __init__(self, amount):
        self.amount = amount

    def to_dict(self):
        return {'ivc': self.amount}

    @staticmethod
    def from_dict(ivc_dict):
        return Invoice(int(ivc_dict['ivc']))


class Payment:
    def __init__(self, amount):
        self.amount = amount

    def to_dict(self):
        return {'pay': self.amount}

    @staticmethod
    def from_dict(pay_dict):
        return Payment(int(pay_dict['pay']))


class Message:
    def __init__(self, msg):
        self.msg = msg

    def to_dict(self, indent=None):
        return {'msg': self.msg}

    @staticmethod
    def from_dict(msg_dict):
        return Message(msg_dict['msg'])


class Reward:
    def __init__(self, amount, block_hash):
        self.amount = amount
        self.block_hash = block_hash

    def to_dict(self):
        return {'rew': self.amount, 'blk': self.block_hash}

    @staticmethod
    def from_dict(rew_dict):
        return Reward(float(rew_dict['rew']), rew_dict['blk'])


class Transaction(DictSignable):
    def __init__(self, from_adr, to_adr, act):
        super().__init__(from_adr)

        self.time = dt.utcnow()
        self.from_adr = from_adr
        self.to_adr = to_adr
        self.act = act

    def to_dict_without_sign(self, indent=None):
        data = {
            'time': str(self.time),
            'from': self.from_adr,
            'to': self.to_adr,
            'act': self.act.to_dict()
        }
        return data

    @staticmethod
    def from_dict_without_hash(trans_dict):
        act_str = list(trans_dict['act'].items())[0][0]

        # create transaction
        act = {
            'ivc': Invoice,
            'pay': Payment,
            'msg': Message,
            'rew': Reward
        }[act_str].from_dict(trans_dict['act'])

        trans = Transaction(trans_dict['from'], trans_dict['to'], act)
        trans.time = trans_dict['time']
        trans._sign = trans_dict['sign']

        if trans.from_adr is not None:
            trans.verify()
        return trans


class ProofOfWork:
    def __init__(self, block, solver):
        self.block = block
        self.solver = solver
        self.work = {}

    @staticmethod
    def _primes_int(factors):
        return reduce(lambda prev, factor: prev * (int(factor[0]) ** factor[1]), factors.items(), 1)

    def add_pow(self, num, factors):
        self.work[num] = factors

    def extract(self, i):
        data = self.block.to_dict_without_hash()
        data['pow'] = {
            'solver': self.solver,
            'work': {n: f for n, f in list(self.work.items())[0:i]}
        }
        blk = json.dumps(data).encode()

        h = hlib.sha3_256(blk).digest()
        num_b = h[0:self.block.h_diff]

        return int.from_bytes(num_b, byteorder='little')

    def work_check_h(self, i):
        num = self.extract(i)
        factors = list(self.work.items())[i][1]

        # check factors are primes
        for v, _ in factors.items():
            if not isprime(int(v)):
                return False

        return True if (num == self._primes_int(factors)) else False

    def work_check(self):
        for i in range(self.block.v_diff):
            if not self.work_check_h(i):
                return False
        return True


class Block(DictHashable):
    def __init__(self, h_diff, prev_block_hash, solver):
        self.prev = prev_block_hash
        self.time = dt.utcnow()
        self.h_diff = h_diff
        self.v_diff = self.get_v_diff()
        self.trans = {}

        self.pow = ProofOfWork(self, solver)

    def get_v_diff(self):
        return max(1, 2 ** (13 - 3 * self.h_diff // 8))

    def add_trans(self, trans):
        self.trans[trans.hash().hexdigest()] = trans

    def add_pow(self, num, factors):
        self.pow.add_pow(num, factors)

    def reward(self):
        return 2 ** (8 - 8 * (self.h_diff - h_diff_init) / 50)

    def work_check(self):
        return self.pow.work_check()

    @staticmethod
    def from_dict_without_hash(block_dict):
        prev = block_dict['prev']
        time = block_dict['time']
        h_diff = block_dict['h_diff']
        v_diff = block_dict['v_diff']
        solver = block_dict['pow']['solver']

        block = Block(h_diff, prev, solver)
        block.time = time
        block.v_diff = v_diff
        block.trans = {h: Transaction.from_dict(t) for h, t in block_dict['trans'].items()}
        block.pow = ProofOfWork(block, solver)
        block.pow.work = block_dict['pow']['work']

        return block

    def to_dict_without_hash(self, indent=None):
        data = {
            'prev': self.prev,
            'time': str(self.time),
            'h_diff': self.h_diff,
            'v_diff': self.v_diff,
            'trans': {h: t.to_dict() for h, t in self.trans.items()},
            'pow': {
                'solver': self.pow.solver,
                'work': self.pow.work
            }
        }
        return data


class Blockchain(DictHashable):
    CHECK_BLOCK_OK = None
    CHECK_BLOCK_PREV_NOT_FOUND = 'previous block not found'
    CHECK_BLOCK_POW_FAILED = 'proof of work was failed'
    CHECK_BLOCK_IN_CHAIN = 'already in blockchain'
    CHECK_BLOCK_TRANS_IN_CHAIN = 'transactions already in blockchain'
    CHECK_BLOCK_INVALID_DIFF = 'invalid block difficulty'
    CHECK_BLOCK_ALREADY_SOLVED = 'already solved'

    CHECK_TRANS_OK = None
    CHECK_TRANS_IN_CHAIN = 'transaction already in blockchain'
    CHECK_TRANS_INSUFF_COINS = 'insufficient coins'
    CHECK_TRANS_REWARD_NOT_FOUND = 'reward block not found'

    def __init__(self, ver):
        self.coin = 'PicoCoin'
        self.ver = ver

        self.blocks = {}
        self.blocks_cache = {}

    def check_trans(self, trans):
        # check transaction in blockchain
        if self.get_trans(trans.hash().hexdigest()) is not None:
            return Blockchain.CHECK_TRANS_IN_CHAIN

        # check billing balance
        if isinstance(trans.act, Payment) and self.get_bal(trans.from_adr) < trans.act.amount:
            return Blockchain.CHECK_TRANS_INSUFF_COINS

        # check reward
        if isinstance(trans.act, Reward):
            block = self.get_block(trans.act.block_hash)
            if (block is None) or (block.pow.solver != trans.to_adr):
                return Blockchain.CHECK_TRANS_REWARD_NOT_FOUND

        return Blockchain.CHECK_TRANS_OK

    def check_block(self, block):
        # check previous block
        prev = self.get_block(block.prev)
        if block.prev is not None:
            if prev is None:
                return Blockchain.CHECK_BLOCK_PREV_NOT_FOUND

        # check if block with previous hash is in blockchain
        for _, b in self.blocks.items():
            if b.prev == block.prev:
                return Blockchain.CHECK_BLOCK_ALREADY_SOLVED

        # check block diff
        if (block.h_diff != self.get_h_diff(prev)) or (block.h_diff < h_diff_init) or (block.v_diff != block.get_v_diff()):
            return Blockchain.CHECK_BLOCK_INVALID_DIFF

        # check pow
        if not block.work_check():
            return Blockchain.CHECK_BLOCK_POW_FAILED

        # check if block is in blockchain
        if self.blocks.get(block.hash().hexdigest()) is not None:
            return Blockchain.CHECK_BLOCK_IN_CHAIN

        # check transactions in blockchain
        for h, _ in block.trans.items():
            if self.get_trans(h) is not None:
                return Blockchain.CHECK_BLOCK_TRANS_IN_CHAIN

        return Blockchain.CHECK_BLOCK_OK

    def add_trans(self, block, trans):
        h = trans.hash().hexdigest()

        reason = self.check_trans(trans)
        if reason is not Blockchain.CHECK_TRANS_OK:
            print(f'Transaction {h[0:12]} rejected: {reason}.')
            return

        block.add_trans(trans)
        print(f'Transaction {h[0:12]} accepted.')
        return True

    def add_block(self, block):
        h = block.hash().hexdigest()

        # reject block if check fails
        reason = self.check_block(block)
        if reason is not Blockchain.CHECK_BLOCK_OK:
            print(f'Block {h[0:12]} rejected: {reason}.')
            return False

        # confirm
        if self.blocks_cache.get(block.prev) is None:
            self.blocks_cache[block.prev] = {}

        if self.blocks_cache[block.prev].get(h) is None:
            self.blocks_cache[block.prev][h] = 0

        self.blocks_cache[block.prev][h] += 1
        print(f'Block {h[0:12]} confirms: {self.blocks_cache[block.prev][h]}')

        # add block to blockchain if got required confirms
        if self.blocks_cache[block.prev][h] >= block_confirms_count:
            self.blocks[h] = block
            del self.blocks_cache[block.prev][h]

            print(f'Block {h[0:12]} accepted to blockchain.')
            return True
        return False

    def get_block(self, block_hash):
        return self.blocks.get(block_hash)

    def get_h_diff(self, block_prev):
        if block_prev is None:
            return h_diff_init
        return block_prev.h_diff + (1 if self.blocks_count() % 10000 == 0 else 0)

    def get_trans(self, trans_hash):
        for _, block in self.blocks.items():
            trans = block.trans.get(trans_hash)
            if trans is not None:
                return trans
        return None

    def get_bal(self, usr_pub):
        bal = 0
        for _, block in self.blocks.items():
            for _, trans in block.trans.items():
                if isinstance(trans.act, Payment):
                    if trans.to_adr == usr_pub:
                        bal += trans.act.amount
                    elif trans.from_adr == usr_pub:
                        bal -= trans.act.amount
                elif isinstance(trans.act, Reward):
                    if trans.to_adr == usr_pub:
                        bal += trans.act.amount
        return bal

    def last_block(self):
        try:
            tmp = list(self.blocks.items())
            return tmp[len(tmp) - 1][1]
        except IndexError:
            return None

    def blocks_count(self):
        return len(self.blocks.items())

    def to_dict_without_hash(self):
        data = {
            'coin': self.coin,
            'ver': self.ver,
            'blocks': {h: b.to_dict() for h, b in self.blocks.items()},
        }
        return data

    @staticmethod
    def from_dict_without_hash(chain_obj):
        coin = chain_obj['coin']
        ver = chain_obj['ver']

        chain = Blockchain(ver)
        chain.coin = coin
        chain.blocks = {h: Block.from_dict(b) for h, b in chain_obj['blocks'].items()}

        return chain


class Net(DictHashable):
    def __init__(self):
        self.peers = []
        self._get_ipv6()
        self.sock = socket.create_server(('::0', 10000), family=socket.AF_INET6)

    def add_peer(self, ipv6, port):
        data = {
            'ipv6': ipv6,
            'port': port
        }
        self.peers.append(data)

    def update_peer(self, ipv6, port):
        for peer in self.peers:
            if peer['ipv6'] == ipv6 and peer['port'] == port:
                return False

        self.add_peer(ipv6, port)
        return True

    def update_peers(self, peers):
        updated = False
        for peer in peers:
            updated = updated or self.update_peer(peer['ipv6'], peer['port'])
        return updated

    def _get_ipv6(self):
        # google dns
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as sock:
            sock.connect(("2001:4860:4860::8888", 80))
            self.ipv6 = sock.getsockname()[0]

    def send(self, data_dict):
        data_json = json.dumps(data_dict).encode()
        data_comp = zlib.compress(data_json)

        for peer in self.peers:
            if peer['ipv6'] == self.ipv6:
                continue
 
            try:
                with socket.create_connection((peer['ipv6'], peer['port']), timeout=5) as sock:
                    sock.sendall(data_comp)
            except Exception:
                continue

    def recv(self):
        sock, _ = self.sock.accept()
        data_comp = b''

        while True:
            tmp = sock.recv(1024)
            if not tmp:
                break
            data_comp += tmp

        data_json = zlib.decompress(data_comp).decode()
        data = json.loads(data_json)
        return data

    def to_dict_without_hash(self):
        return {'peers': self.peers}

    @staticmethod
    def from_dict_without_hash(obj_dict, *args, **kwargs):
        net = Net()
        net.peers = obj_dict['peers']
        return net

    def __del__(self):
        self.sock.close()
