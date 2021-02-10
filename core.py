import json
import base58
import hashlib as hlib
from functools import reduce
from abc import ABC, abstractmethod
from datetime import datetime as dt

from Crypto.Cipher import AES
from ecdsa import SigningKey, VerifyingKey, SECP256k1


h_diff_init = 14
block_confirms_count = 1


class User:
    def __init__(self):
        self.pub = None
        self.priv = None

    @staticmethod
    def _encrypt_priv(priv, password):
        h = hlib.sha3_256(password.encode())
        cipher = AES.new(h.digest(), AES.MODE_GCM)

        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(priv.to_string())

        return (nonce, ciphertext, tag)

    @staticmethod
    def _decrypt_priv(e_priv, password):
        h = hlib.sha3_256(password.encode())
        cipher = AES.new(h.digest(), AES.MODE_GCM, nonce=e_priv[0])

        priv_raw = cipher.decrypt(e_priv[1])
        cipher.verify(e_priv[2])
    
        return SigningKey.from_string(priv_raw, curve=SECP256k1)

    @staticmethod
    def register(password):
        user = User()

        priv = SigningKey.generate(curve=SECP256k1)

        user.pub = priv.get_verifying_key()
        user.priv = user._encrypt_priv(priv, password)

        return user

    @staticmethod
    def login(e_priv, password):
        user = User()

        e_priv_raw = base58.b58decode(e_priv)
        e_priv = (e_priv_raw[0:16], e_priv_raw[16:48], e_priv_raw[48:64])

        priv = user._decrypt_priv(e_priv, password)

        user.pub = priv.get_verifying_key()
        user.priv = user._encrypt_priv(priv, password)

        return user

    @staticmethod
    def from_json(usr_json, password):
        data = json.loads(usr_json)

        priv_b = base58.b58decode(data['priv'])
        pub_b = base58.b58decode(data['pub'])

        user = User()
        user.priv = (priv_b[0:16], priv_b[16:48], priv_b[48:64])
        user.pub = VerifyingKey.from_string(pub_b, curve=SECP256k1)

        expected_hash = data['hash']
        if expected_hash != user.hash().hexdigest():
            raise json.JSONDecodeError('Invalid hash!', usr_json, 0)
        return user

    def get_pub(self):
        return base58.b58encode(self.pub.to_string()).decode()

    def get_priv(self, password):
        priv = self._decrypt_priv(self.priv, password)
        return base58.b58encode(priv.to_string()).decode()

    def get_priv_ept(self):
        return base58.b58encode(self.priv[0] + self.priv[1] + self.priv[2]).decode()

    def sign(self, msg, password):
        h = hlib.sha3_256(msg).digest()
        priv = self._decrypt_priv(self.priv, password)

        return base58.b58encode(priv.sign(h)).decode()

    def verify(self, msg, sign):
        h = hlib.sha3_256(msg).digest()
        self.pub.verify(base58.b58decode(sign), h)

    @staticmethod
    def verify_with_key(pub_str, msg, sign_str):
        h = hlib.sha3_256(msg).digest()

        pub = base58.b58decode(pub_str)
        sign = base58.b58decode(sign_str)

        pub_obj = VerifyingKey.from_string(pub, curve=SECP256k1)
        pub_obj.verify(sign, h)

    def to_json(self, indent=None):
        data = {
            'pub': self.get_pub(),
            'priv': self.get_priv_ept()
        }
        return json.dumps(data, indent=indent)

    def to_json_with_hash(self, indent=None):
        data = json.loads(self.to_json(indent))
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data, indent=indent)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))


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


class Transaction:
    def __init__(self, from_adr, to_adr, act):
        self.time = dt.utcnow()
        self.from_adr = from_adr
        self.to_adr = to_adr
        self.act = act
        self._sign = None

    def sign(self, user, password):
        self._sign = user.sign(self.to_json().encode(), password)
        return self._sign

    def verify(self):
        msg = self.to_json().encode()
        User.verify_with_key(self.from_adr, msg, self._sign)

    def to_json(self, indent=None):
        data = {
            'time': str(self.time),
            'from': self.from_adr,
            'to': self.to_adr,
            'act': json.loads(self.act.to_json())
        }
        return json.dumps(data, indent=indent)

    @staticmethod
    def from_json(trans_json):
        data = json.loads(trans_json)
        act_str = list(data['act'].items())[0][0]

        # create transaction
        act = {
            'ivc': Invoice,
            'pay': Payment,
            'msg': Message
        }[act_str].from_json(json.dumps(data['act']))

        trans = Transaction(data['from'], data['to'], act)
        trans.time = data['time']
        trans._sign = data['sign']
        trans.verify()

        expected_hash = data['hash']
        if expected_hash != trans.hash().hexdigest():
            raise json.JSONDecodeError('Invalid hash!', trans_json, 0)
        return trans

    def to_json_with_sign(self, indent=None):
        data = json.loads(self.to_json(indent))
        data['sign'] = self._sign
        return json.dumps(data, indent=indent)

    def to_json_with_hash(self, indent=None):
        data = json.loads(self.to_json_with_sign(indent))
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data, indent=indent)

    def hash(self):
        return hlib.sha3_256(self.to_json_with_sign().encode('ascii'))


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

        h = hlib.sha3_256(blk)
        num = int.from_bytes(h.digest()[0:self.block.h_diff], byteorder='little')

        return (num, h)

    def work_check_h(self, i):
        num, _ = self.extract(i)
        factors = list(self.work.items())[i][1]

        if num == self._primes_int(factors):
            return True
        return False

    def work_check(self):
        for i in range(self.block.v_diff):
            if not self.work_check_h(i):
                return False
        return True


class Block:
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
    def from_json(block_json):
        data = json.loads(block_json)

        prev = data['prev']
        time = data['time']
        h_diff = data['h_diff']
        v_diff = data['v_diff']
        solver = data['pow']['solver']

        block = Block(h_diff, prev, solver)
        block.time = time
        block.v_diff = v_diff
        block.trans = {h: Transaction.from_json(json.dumps(t)) for h, t in data['trans'].items()}
        block.pow = ProofOfWork(block, solver)
        block.pow.work = data['pow']['work']

        expected_hash = data['hash']
        if expected_hash != block.hash().hexdigest():
            raise json.JSONDecodeError('Invalid hash!', block_json, 0)
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

    def to_json_with_hash(self, indent=None):
        data = json.loads(self.to_json(indent))
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data, indent=indent)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))


class Blockchain:
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
    def from_json(chain_json):
        data = json.loads(chain_json)

        coin = data['coin']
        ver = data['ver']

        chain = Blockchain(ver)
        chain.coin = coin
        chain.blocks = {h: Block.from_json(json.dumps(b)) for h, b in data['blocks'].items()}

        expected_hash = data['hash']
        if expected_hash != chain.hash().hexdigest():
            raise json.JSONDecodeError('Invalid hash!', chain_json, 0)
        return chain

    def to_json_with_hash(self, indent=None):
        data = json.loads(self.to_json(indent))
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data, indent=indent)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))


class Core:
    def __init__(self):
        pass
