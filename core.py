import json
import hashlib as hlib
from datetime import datetime as dt


h_diff_shift = 16

class Transaction:
    def __init__(self, from_adr, to_adr, amount):
        self.from_adr = from_adr
        self.to_adr = to_adr
        self.amount = amount

    def to_json(self):
        data = {
            "from": self.from_adr,
            "to": self.to_adr,
            "amnt": self.amount
        }
        return json.dumps(data)

    def hash(self):
        return hlib.sha3_256(self.to_json().encode('ascii'))


class Block:
    def __init__(self, id, h_diff, v_diff):
        self.id = id
        self.time = dt.utcnow()
        self.trans = []
        self.pow = {}
        self.completed = False

        self.h_diff = h_diff
        self.v_diff = v_diff
        self.reward = 100 / (2 ** h_diff)

    def add_trans(self, from_adr, to_adr, amount):
        self.trans.append(Transaction(from_adr, to_adr, amount))

    def add_pow(self, num, factors):
        self.pow[num] = factors

    def base_to_json(self):
        data = {
            "id": self.id,
            "time": str(self.time),
            "h_diff": self.h_diff,
            "v_diff": self.v_diff,
            "trans": [json.loads(t.to_json()) for t in self.trans]
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
