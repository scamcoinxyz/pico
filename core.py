import json
import base58
import hashlib as hlib
from functools import reduce
from abc import ABC, abstractmethod
from datetime import datetime as dt

from Crypto.Cipher import AES
from ecdsa import SigningKey, VerifyingKey, SECP256k1


h_diff_init = 14


class User:
    def __init__(self):
        self.pub = None
        self.priv = None

    @staticmethod
    def _encrypt_priv(priv, password):
        hash = hlib.sha3_256(password.encode())
        cipher = AES.new(hash.digest(), AES.MODE_GCM)

        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(priv.to_string())

        return (nonce, ciphertext, tag)

    @staticmethod
    def _decrypt_priv(e_priv, password):
        hash = hlib.sha3_256(password.encode())
        cipher = AES.new(hash.digest(), AES.MODE_GCM, nonce=e_priv[0])

        priv_raw = cipher.decrypt(e_priv[1])
        cipher.verify(e_priv[2])
    
        return SigningKey.from_string(priv_raw, curve=SECP256k1)

    @staticmethod
    def create(password):
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
    def from_json(json_data, password):
        data = json.loads(json_data)

        expected_hash = data['hash']
        del data['hash']

        hash = hlib.sha3_256(json.dumps(data).encode('ascii')).hexdigest()

        if hash != expected_hash:
            raise json.JSONDecodeError('Invalid hash!', json_data, 0)
        return User.login(data['priv'], password)

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
        try:
            self.pub.verify(base58.b58decode(sign), h)
        except:
            return False
        return True

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


class Transaction(ABC):
    def __init__(self, user, to_adr, password):
        self.from_adr = user.get_pub()
        self.to_adr = to_adr
        self.sign = user.sign(self.to_json().encode(), password)

    @abstractmethod
    def to_json(self, indent=None):
        pass

    # @abstractmethod
    # def from_json(self):
    #     pass

    def to_json_with_sign(self, indent=None):
        data = json.loads(self.to_json(indent))
        data['sign'] = self.sign
        return json.dumps(data, indent=indent)

    def to_json_with_hash(self, indent=None):
        data = json.loads(self.to_json_with_sign(indent))
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data, indent=indent)

    def hash(self):
        return hlib.sha3_256(self.to_json_with_sign().encode('ascii'))


class Invoice(Transaction):
    def __init__(self, user, to_adr, amount, password):
        self.amount = amount
        super().__init__(user, to_adr, password)

    def to_json(self, indent=None):
        data = {
            "from": self.from_adr,
            "to": self.to_adr,
            "act": {
                "invoice": self.amount
            },
        }
        return json.dumps(data, indent=indent)


class Payment(Transaction):
    def __init__(self, user, to_adr, amount, password):
        self.amount = amount
        super().__init__(user, to_adr, password)

    def to_json(self, indent=None):
        data = {
            "from": self.from_adr,
            "to": self.to_adr,
            "act": {
                "pay": self.amount
            },
        }
        return json.dumps(data, indent=indent)


class Message(Transaction):
    def __init__(self, user, to_adr, msg, password):
        self.msg = msg
        super().__init__(user, to_adr, password)

    def to_json(self, indent=None):
        data = {
            "from": self.from_adr,
            "to": self.to_adr,
            "act": {
                "msg": self.msg
            },
        }
        return json.dumps(data, indent=indent)


class ProofOfWork:
    def __init__(self, block):
        self.block = block
        self.pow = {}

    @staticmethod
    def _primes_int(factors):
        return reduce(lambda prev, factor: prev * (factor[0] ** factor[1]), factors.items(), 1)

    def add_pow(self, num, factors):
        self.pow[num] = factors

    def extract(self, i):
        data = {
            "base": json.loads(self.block.base_to_json()),
            "pow": {n: f for n, f in list(self.pow.items())[0:i]}
        }
        blk = json.dumps(data).encode('ascii')

        hash = hlib.sha3_256(blk)
        num = int.from_bytes(hash.digest()[0:self.block.h_diff], byteorder='little')

        return (num, hash)

    def work_check_h(self, i):
        num, _ = self.extract(i)
        factors = list(self.pow.items())[i][1]

        if num == self._primes_int(factors):
            return True
        return False

    def work_check(self):
        for i in range(self.block.v_diff):
            if not self.work_check_h(i):
                return False
        return True


class Block:
    def __init__(self, id, h_diff, v_diff, prev_block_hash, solver):
        self.id = id
        self.time = dt.utcnow()
        self.prev = prev_block_hash
        self.h_diff = h_diff
        self.v_diff = v_diff
        self.trans = []

        self.pow = ProofOfWork(self)
        self.solver = solver

    def add_trans(self, trans):
        self.trans.append(trans)

    def add_pow(self, num, factors):
        self.pow.add_pow(num, factors)

    def reward(self):
        return 2 ** (8 - 8 * (self.h_diff - h_diff_init) / 50)

    def work_check(self):
        return self.pow.work_check()

    def base_to_json(self, indent=None):
        data = {
            "id": self.id,
            "time": str(self.time),
            "prev": self.prev,
            "h_diff": self.h_diff,
            "v_diff": self.v_diff,
            "trans": [json.loads(t.to_json_with_hash(indent)) for t in self.trans]
        }
        return json.dumps(data, indent=indent)

    def to_json(self, indent=None):
        data = {
            "base": json.loads(self.base_to_json(indent)),
            "pow": self.pow.pow,
            "solver": self.solver
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
        self.coin = "PicoCoin"
        self.ver = ver
        self.blocks = {}

    def add_block(self, block):
        self.blocks[block.hash().hexdigest()] = block

    def to_json(self, indent=None):
        data = {
            "coin": self.coin,
            "ver": self.ver,
            "blocks": {h: json.loads(b.to_json_with_hash(indent)) for h, b in self.blocks.items()},
        }
        return json.dumps(data, indent=indent)

    # def from_json(self):
    #     with open("data_file.json", "r") as read_file:
    #         data = json.load(read_file)

    def to_json_with_hash(self, indent=None):
        data = json.loads(self.to_json(indent))
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data, indent=indent)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))


class Core:
    def __init__(self):
        pass
