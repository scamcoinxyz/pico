import json
import base64
import hashlib as hlib
from abc import ABC, abstractmethod
from datetime import datetime as dt

from ecdsa import SigningKey, VerifyingKey, SECP256k1

class User:
    def __init__(self):
        self.pub = None
        self.priv = None

    def create(self, password):
        self.priv = SigningKey.generate(curve=SECP256k1)
        self.pub = self.priv.get_verifying_key()

    def login(self, priv_key):
        self.priv = SigningKey.from_string(base64.b64decode(priv_key), curve=SECP256k1)
        self.pub = self.priv.get_verifying_key()

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

class Block:
    def __init__(self, id, h_diff, v_diff):
        self.id = id
        self.time = dt.utcnow()
        self.trans = []
        self.pow = {}
        self.completed = False

        self.h_diff = h_diff
        self.v_diff = v_diff
        self.reward = 250 / (2 ** h_diff)

    def add_trans(self, trans):
        self.trans.append(trans)

    def add_pow(self, num, factors):
        self.pow[num] = factors

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
            "pow": self.pow
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

    def to_json_with_hash(self):
        data = json.loads(self.to_json())
        data['hash'] = self.hash().hexdigest()
        return json.dumps(data)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))
