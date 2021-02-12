import json
import base58
import socket
import hashlib as hlib

from functools import reduce
from abc import abstractmethod
from datetime import datetime as dt

from Crypto.Cipher import AES
from ecdsa import SigningKey, VerifyingKey, SECP256k1


h_diff_init = 14
block_confirms_count = 1


class JSONHashable:
    @abstractmethod
    def to_json(self, indent=None):
        pass

    @abstractmethod
    def from_json_without_hash(obj_dict, *args, **kwargs):
        pass

    @classmethod
    def from_json(cls, obj_json, *args, **kwargs):
        data = json.loads(obj_json)
        obj = cls.from_json_without_hash(data, *args, **kwargs)

        expected_hash = data['hash']
        if expected_hash != obj.hash().hexdigest():
            raise json.JSONDecodeError('Invalid hash!', obj_json, 0)
        return obj

    def to_json_with_hash(self, indent=None):
        data = json.loads(self.to_json(indent))
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data, indent=indent)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))


class JSONSignable(JSONHashable):
    @abstractmethod
    def to_json_without_sign(self, indent=None):
        pass

    def sign(self, user, password):
        self._sign = user.sign(self.to_json_without_sign().encode(), password)
        return self._sign

    def verify(self):
        msg = self.to_json_without_sign().encode()
        user = User(None, self.from_adr)
        user.verify(msg, self._sign)

    def to_json(self, indent=None):
        data = json.loads(self.to_json_without_sign(indent))
        data['sign'] = self._sign
        return json.dumps(data, indent=indent)


class User(JSONHashable):
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

    @staticmethod
    def create(password):
        priv_raw = SigningKey.generate(curve=SECP256k1)
        pub_raw = priv_raw.get_verifying_key()

        priv = base58.b58encode(priv_raw.to_string()).decode()
        pub = base58.b58encode(pub_raw.to_string()).decode()

        e_priv = User._encrypt_priv(priv, password).decode()

        return User(e_priv, pub)

    def to_json(self, indent=None):
        data = {
            'pub': self.pub,
            'priv': self.priv
        }
        return json.dumps(data, indent=indent)

    @staticmethod
    def from_json_without_hash(usr_dict, password):
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

    def to_json(self, indent=None):
        data = {'ivc': self.amount}
        return json.dumps(data, indent=indent)

    @staticmethod
    def from_json(ivc_json):
        data = json.loads(ivc_json)
        return Invoice(int(data['ivc']))


class Payment:
    def __init__(self, amount):
        self.amount = amount

    def to_json(self, indent=None):
        data = {'pay': self.amount}
        return json.dumps(data, indent=indent)

    @staticmethod
    def from_json(pay_json):
        data = json.loads(pay_json)
        return Payment(int(data['pay']))


class Message:
    def __init__(self, msg):
        self.msg = msg

    def to_json(self, indent=None):
        data = {'msg': self.msg}
        return json.dumps(data, indent=indent)

    @staticmethod
    def from_json(msg_json):
        data = json.loads(msg_json)
        return Message(data['msg'])


class Transaction(JSONSignable):
    def __init__(self, from_adr, to_adr, act):
        self.time = dt.utcnow()
        self.from_adr = from_adr
        self.to_adr = to_adr
        self.act = act
        self._sign = None

    def to_json_without_sign(self, indent=None):
        data = {
            'time': str(self.time),
            'from': self.from_adr,
            'to': self.to_adr,
            'act': json.loads(self.act.to_json())
        }
        return json.dumps(data, indent=indent)

    @staticmethod
    def from_json_without_hash(trans_dict):
        act_str = list(trans_dict['act'].items())[0][0]

        # create transaction
        act = {
            'ivc': Invoice,
            'pay': Payment,
            'msg': Message
        }[act_str].from_json(json.dumps(trans_dict['act']))

        trans = Transaction(trans_dict['from'], trans_dict['to'], act)
        trans.time = trans_dict['time']
        trans._sign = trans_dict['sign']
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
        data = json.loads(self.block.to_json())
        data['pow'] = {
            'solver': self.solver,
            'work': {n: f for n, f in list(self.work.items())[0:i]}
        }
        blk = json.dumps(data).encode('ascii')

        h = hlib.sha3_256(blk).digest()
        num_b = h[0:self.block.h_diff]

        return int.from_bytes(num_b, byteorder='little')

    def work_check_h(self, i):
        num = self.extract(i)
        factors = list(self.work.items())[i][1]

        return True if (num == self._primes_int(factors)) else False

    def work_check(self):
        for i in range(self.block.v_diff):
            if not self.work_check_h(i):
                return False
        return True


class Block(JSONHashable):
    def __init__(self, h_diff, prev_block_hash, solver):
        self.prev = prev_block_hash
        self.time = dt.utcnow()
        self.h_diff = h_diff
        self.v_diff = max(1, 2 ** (13 - 3 * h_diff // 8))
        self.trans = {}

        self.pow = ProofOfWork(self, solver)

    def add_trans(self, trans):
        self.trans[trans.hash().hexdigest()] = trans

    def add_pow(self, num, factors):
        self.pow.add_pow(num, factors)

    def reward(self):
        return 2 ** (8 - 8 * (self.h_diff - h_diff_init) / 50)

    def work_check(self):
        return self.pow.work_check()

    @staticmethod
    def from_json_without_hash(block_dict):
        prev = block_dict['prev']
        time = block_dict['time']
        h_diff = block_dict['h_diff']
        v_diff = block_dict['v_diff']
        solver = block_dict['pow']['solver']

        block = Block(h_diff, prev, solver)
        block.time = time
        block.v_diff = v_diff
        block.trans = {h: Transaction.from_json(json.dumps(t)) for h, t in block_dict['trans'].items()}
        block.pow = ProofOfWork(block, solver)
        block.pow.work = block_dict['pow']['work']

        return block

    def to_json(self, indent=None):
        data = {
            'prev': self.prev,
            'time': str(self.time),
            'h_diff': self.h_diff,
            'v_diff': self.v_diff,
            'trans': {h: json.loads(t.to_json_with_hash(indent)) for h, t in self.trans.items()},
            'pow': {
                'solver': self.pow.solver,
                'work': self.pow.work
            }
        }
        return json.dumps(data, indent=indent)


class Blockchain(JSONHashable):
    def __init__(self, ver):
        self.coin = 'PicoCoin'
        self.ver = ver
        self.blocks = {}

        self.blocks_cache = {}

    def add_block(self, block):
        # reject block if pow fails or block is already in blockchain
        if (not block.work_check()) or (self.blocks.get(block.hash().hexdigest()) is not None):
            return

        if self.blocks_cache.get(block.prev) is None:
            self.blocks_cache[block.prev] = {}

        if self.blocks_cache[block.prev].get(block) is None:
            self.blocks_cache[block.prev][block] = 0

        self.blocks_cache[block.prev][block] += 1

        if self.blocks_cache[block.prev][block] >= block_confirms_count:
            self.blocks[block.hash().hexdigest()] = block

    def last_block(self):
        try:
            tmp = list(self.blocks.items())
            return tmp[len(tmp) - 1][1]
        except IndexError:
            return None

    def blocks_count(self):
        return len(self.blocks.items())

    def to_json(self, indent=None):
        data = {
            'coin': self.coin,
            'ver': self.ver,
            'blocks': {h: json.loads(b.to_json_with_hash(indent)) for h, b in self.blocks.items()},
        }
        return json.dumps(data, indent=indent)

    @staticmethod
    def from_json_without_hash(chain_obj):
        coin = chain_obj['coin']
        ver = chain_obj['ver']

        chain = Blockchain(ver)
        chain.coin = coin
        chain.blocks = {h: Block.from_json(json.dumps(b)) for h, b in chain_obj['blocks'].items()}

        return chain


class Net(JSONHashable):
    def __init__(self):
        self.peers = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', 10000))

    def add_peer(self, ipv6, port):
        data = {
            'ipv6': ipv6,
            'port': port
        }
        self.peers.append(data)

    def send(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            for peer in self.peers:
                sock.sendto(data, (peer['ipv6'], peer['port']))

    def send_trans(self, trans):
        data = {
            'trans': json.loads(trans.to_json_with_hash())
        }
        self.send(json.dumps(data).encode())

    def send_block(self, block):
        data = {
            'block': json.loads(block.to_json_with_hash())
        }
        self.send(json.dumps(data).encode())

    def to_json(self, indent=None):
        data = {
            'peers': self.peers
        }
        return json.dumps(data, indent=indent)

    def from_json_without_hash(obj_dict, *args, **kwargs):
        net = Net()
        net.peers = obj_dict['peers']
        return net

    def __del__(self):
        self.sock.close()
