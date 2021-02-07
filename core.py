import json
import base64
import hashlib as hlib
from functools import reduce
from abc import ABC, abstractmethod
from datetime import datetime as dt

from ecdsa import SigningKey, VerifyingKey, SECP256k1


h_diff_init = 14


class User:
    def __init__(self):
        self.pub = None
        self.priv = None

    @staticmethod
    def create(password):
        user = User()
        user.priv = SigningKey.generate(curve=SECP256k1)
        user.pub = user.priv.get_verifying_key()

        return user

    @staticmethod
    def login(priv_key):
        user = User()
        user.priv = SigningKey.from_string(base64.b64decode(priv_key), curve=SECP256k1)
        user.pub = user.priv.get_verifying_key()

        return user

    def get_keys(self):
        return {'priv': base64.b64encode(self.priv.to_string()).decode(), 'pub': base64.b64encode(self.pub.to_string()).decode()}

    def get_pub(self):
        return base64.b64encode(self.pub.to_string()).decode()
    
    def get_priv(self):
        return base64.b64encode(self.priv.to_string()).decode()

    def sign(self, msg):
        h = hlib.sha3_256(msg).digest()
        return base64.b64encode(self.priv.sign(h)).decode()

    def verify(self, msg, sign):
        h = hlib.sha3_256(msg).digest()
        try:
            self.pub.verify(base64.b64decode(sign), h)
        except:
            return False
        return True


class Transaction(ABC):
    def __init__(self, user, to_adr):
        self.from_adr = user.get_pub()
        self.to_adr = to_adr
        self.sign = user.sign(self.to_json().encode())

    @abstractmethod
    def to_json(self):
        pass

    # @abstractmethod
    # def from_json(self):
    #     pass

    def to_json_with_sign(self):
        data = json.loads(self.to_json())
        data['sign'] = self.sign
        return json.dumps(data)

    def hash(self):
        return hlib.sha3_256(self.to_json_with_sign().encode('ascii'))


class Invoice(Transaction):
    def __init__(self, user, to_adr, amount):
        self.amount = amount
        super().__init__(user, to_adr)

    def to_json(self):
        data = {
            "from": self.from_adr,
            "to": self.to_adr,
            "act": {
                "invoice": self.amount
            },
        }
        return json.dumps(data)


class Payment(Transaction):
    def __init__(self, user, to_adr, amount):
        self.amount = amount
        super().__init__(user, to_adr)

    def to_json(self):
        data = {
            "from": self.from_adr,
            "to": self.to_adr,
            "act": {
                "pay": self.amount
            },
        }
        return json.dumps(data)


class Message(Transaction):
    def __init__(self, user, to_adr, msg):
        self.msg = msg
        super().__init__(user, to_adr)

    def to_json(self):
        data = {
            "from": self.from_adr,
            "to": self.to_adr,
            "act": {
                "msg": self.msg
            },
        }
        return json.dumps(data)

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
    def __init__(self, id, h_diff, v_diff):
        self.id = id
        self.time = dt.utcnow()
        self.trans = []
        self.pow = ProofOfWork(self)

        self.h_diff = h_diff
        self.v_diff = v_diff
        self.reward = 2 ** (8 - 8 * (h_diff - h_diff_init) / 50)

    def add_trans(self, trans):
        self.trans.append(trans)

    def add_pow(self, num, factors):
        self.pow.add_pow(num, factors)

    def work_check(self):
        return self.pow.work_check()

    def base_to_json(self):
        data = {
            "id": self.id,
            "time": str(self.time),
            "h_diff": self.h_diff,
            "v_diff": self.v_diff,
            "trans": [json.loads(t.to_json_with_sign()) for t in self.trans]
        }
        return json.dumps(data)

    def to_json(self):
        data = {
            "base": json.loads(self.base_to_json()),
            "pow": self.pow.pow
        }
        return json.dumps(data)

    def to_json_with_hash(self):
        data = json.loads(self.to_json())
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))


class Blockchain:
    def __init__(self, ver):
        self.coin = "PicoCoin"
        self.ver = ver
        self.blocks = {}

    def add_block(self, block):
        self.blocks[block.hash().hexdigest()] = block

    def to_json(self):
        data = {
            "coin": self.coin,
            "ver": self.ver,
            "blocks": {h: json.loads(b.to_json_with_hash()) for h, b in self.blocks.items()},
        }
        return json.dumps(data)

    # def from_json(self):
    #     with open("data_file.json", "r") as read_file:
    #         data = json.load(read_file)

    def to_json_with_hash(self):
        data = json.loads(self.to_json())
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))


class Core:
    def __init__(self):
        pass
