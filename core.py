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
        return json.dumps(map)

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
            "trans": []
        }
        return json.dumps(data)

    def to_json(self):
        data = {
            "base": self.base_to_json(),
            "pow": {self.pow}
        }
        return json.dumps(data)

    def to_json_with_hash(self):
        data = {
            "base": self.base_to_json(),
            "pow": {self.pow},
            "hash": self.hash().hexdigest()
        }
        return json.dumps(data)

    def hash(self):
        return hlib.sha3_256(self.to_json())
