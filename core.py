import zlib
import json
import base58
import socket
import hashlib as hlib

from typing import Union, Optional, Dict, List
from functools import reduce
from datetime import datetime as dt
from dataclasses import dataclass, asdict, field

from Crypto.Cipher import AES
from sympy.ntheory import isprime
from ecdsa import SigningKey, VerifyingKey, SECP256k1


@dataclass
class DataHashable:
    hash: Optional[str]

    def __post_init__(self):
        self.hash = self.dict_hash()

    def to_dict_without_hash(self):
        return {k: v for k, v in asdict(self).items() if k != 'hash'}

    def to_dict(self):
        self_dict = asdict(self)
        self_dict['hash'] = self.hash
        return self_dict

    def dict_verify(self):
        return self.hash == self.dict_hash()

    def dict_hash(self):
        self_dict = self.to_dict_without_hash()
        self_json = json.dumps(self_dict).encode()
        return hlib.sha3_256(self_json).hexdigest()


@dataclass
class DataSignable(DataHashable):
    sign: Optional[str]

    def to_dict_without_sign(self):
        return {k: v for k, v in asdict(self).items() if k != 'hash' and k != 'sign'}

    def to_dict(self):
        self_dict = asdict(self)
        self_dict['sign'] = self.sign
        self_dict['hash'] = self.hash
        return self_dict

    def dict_verify(self, pub):
        try:
            self_dict = self.to_dict_without_sign()
            User.verify(pub, json.dumps(self_dict).encode(), self.sign)
            return super().dict_verify()
        except Exception:
            return False

    def dict_sign(self, user, password):
        self_dict = self.to_dict_without_sign()
        self.sign = user.sign(json.dumps(self_dict).encode(), password)
        self.hash = self.dict_hash()
        return self.sign


@dataclass
class User(DataHashable):
    priv: str
    pub: str

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

        return User(priv=e_priv, pub=pub, hash=None)

    def check_passwd(self, password):
        self._decrypt_priv(self.priv, password)
        return password

    def sign(self, msg, password):
        h = hlib.sha3_256(msg).digest()

        _priv = self._decrypt_priv(self.priv, password)
        priv = SigningKey.from_string(base58.b58decode(_priv), curve=SECP256k1)

        return base58.b58encode(priv.sign(h)).decode()

    @staticmethod
    def verify(pub, msg, sign):
        h = hlib.sha3_256(msg).digest()

        pub = VerifyingKey.from_string(base58.b58decode(pub), curve=SECP256k1)
        pub.verify(base58.b58decode(sign), h)


@dataclass
class Invoice:
    ivc: int


@dataclass
class Payment:
    pay: int


@dataclass
class Message:
    msg: str


@dataclass
class Reward:
    rew: float
    blk: str


@dataclass
class Transaction(DataSignable):
    time: str = field(init=False)
    from_adr: Union[str, None]
    to_adr: str
    act: Union[Invoice, Payment, Reward, Message]

    def __post_init__(self):
        self.time = str(dt.utcnow())
        super().__post_init__()


@dataclass
class ProofOfWork:
    solver: str
    work: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def __post_init__(self):
        self.block = None

    @staticmethod
    def _primes_int(factors):
        return reduce(lambda prev, factor: prev * (int(factor[0]) ** factor[1]), factors.items(), 1)

    def set_block(self, block):
        self.block = block

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


@dataclass
class Block(DataHashable):
    prev: Union[str, None]
    time: str = field(init=False)
    h_diff: int
    v_diff: int = field(init=False)
    trans: Dict[str, Transaction]
    pow: ProofOfWork

    def __post_init__(self):
        self.time = str(dt.utcnow())
        self.v_diff = self.get_v_diff()
        self.pow.set_block(self)
        super().__post_init__()

    def get_v_diff(self):
        return max(1, 2 ** (13 - 3 * self.h_diff // 8))

    def add_trans(self, trans):
        self.trans[trans.dict_hash()] = trans
        self.hash = self.dict_hash()

    def add_pow(self, num, factors):
        self.pow.add_pow(num, factors)
        self.hash = self.dict_hash()

    def work_check(self):
        return self.pow.work_check()


class BlockCheck:
    OK = None
    PREV_NOT_FOUND = 'previous block not found'
    POW_FAILED = 'proof of work was failed'
    IN_CHAIN = 'already in blockchain'
    INVALID_DIFF = 'invalid block difficulty'
    ALREADY_SOLVED = 'already solved'


class TransCheck:
    OK = None
    IN_CHAIN = 'transaction already in blockchain'
    INSUFF_COINS = 'insufficient coins'
    REWARD_NOT_FOUND = 'reward block not found'


@dataclass
class Blockchain(DataHashable):
    coin: str = field(init=False)
    ver: str
    blocks: Dict[str, Block]

    H_DIFF_INIT = 14
    BLOCK_REQUIRED_CONFIRMS = 6

    def __post_init__(self):
        self.coin = 'PicoCoin'
        self.blocks_cache = {}
        super().__post_init__()

    def check_trans(self, trans):
        # check transaction in blockchain
        if self.get_trans(trans.dict_hash()) is not None:
            return TransCheck.IN_CHAIN

        # check billing balance
        if isinstance(trans.act, Payment) and self.get_bal(trans.from_adr) < trans.act.amount:
            return TransCheck.INSUFF_COINS

        # check reward
        if isinstance(trans.act, Reward):
            prev = self.get_block(trans.act.blk)
            if (prev is None) or (prev.pow.solver != trans.to_adr):
                return TransCheck.REWARD_NOT_FOUND

        return TransCheck.OK

    def new_block(self, solver):
        prev = self.last_block()
        h_diff = self.get_h_diff(prev)
        prev_hash = prev.dict_hash() if prev is not None else None

        return Block(h_diff=h_diff, prev=prev_hash, trans={}, pow=ProofOfWork(solver), hash=None)

    def check_block(self, block):
        # check previous block
        prev = self.get_block(block.prev)
        if block.prev is not None:
            if prev is None:
                return BlockCheck.PREV_NOT_FOUND

        # check block diff
        if (block.h_diff != self.get_h_diff(prev)) or (block.h_diff < Blockchain.H_DIFF_INIT) or (block.v_diff != block.get_v_diff()):
            return BlockCheck.INVALID_DIFF

        # check pow
        if not block.work_check():
            return BlockCheck.POW_FAILED

        # check if block is in blockchain
        if self.blocks.get(block.dict_hash()) is not None:
            return BlockCheck.IN_CHAIN

        # check if block with previous hash is in blockchain
        for _, b in self.blocks.items():
            if b.prev == block.prev:
                return BlockCheck.ALREADY_SOLVED

        # check transactions
        for _, trans in block.trans.items():
            reason = self.check_trans(trans)
            if reason is not TransCheck.OK:
                return reason

        return BlockCheck.OK

    def add_trans(self, block, trans):
        h = trans.dict_hash()

        reason = self.check_trans(trans)
        if reason is not TransCheck.OK:
            print(f'Transaction {h[0:12]} rejected: {str(reason)}.')
            return

        block.add_trans(trans)
        print(f'Transaction {h[0:12]} accepted.')
        return True

    def add_block(self, block):
        h = block.dict_hash()

        if self.blocks_cache.get(block.prev) is None:
            self.blocks_cache[block.prev] = {}

        if self.blocks_cache[block.prev].get(h) is None:
            self.blocks_cache[block.prev][h] = 0

        # reject block if check fails
        reason = self.check_block(block)
        if reason is not BlockCheck.OK:
            print(f'Block {h[0:12]} rejected: {str(reason)}.')
            del self.blocks_cache[block.prev][h]
            return False

        # confirm
        self.blocks_cache[block.prev][h] += 1
        print(f'Block {h[0:12]} confirms: {self.blocks_cache[block.prev][h]}')

        # add block to blockchain if got required confirms
        if self.blocks_cache[block.prev][h] >= Blockchain.BLOCK_REQUIRED_CONFIRMS:
            self.blocks[h] = block
            del self.blocks_cache[block.prev][h]

            print(f'Block {h[0:12]} accepted to blockchain.')
            return True
        return False

    def get_block(self, block_hash):
        return self.blocks.get(block_hash)

    def get_block_confirms(self, block):
        if (block is None) or (self.blocks_cache.get(block.prev) is None):
            return None
        return self.blocks_cache[block.prev].get(block.dict_hash())

    def get_h_diff(self, block_prev):
        if block_prev is None:
            return Blockchain.H_DIFF_INIT
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

    def round(self):
        return self.blocks_count() // 10000

    def reward(self):
        return 2 ** (8 - 8 * self.round() / 50)


@dataclass
class Peer:
    ipv6: str
    port: int


@dataclass
class Net(DataHashable):
    peers: List[Peer] = field(default_factory=list)

    def __post_init__(self):
        self.ipv6 = self.get_ipv6()
        self.sock = socket.create_server(('::0', 10000), family=socket.AF_INET6)
        super().__post_init__()
    
    def add_peer(self, peer):
        self.peers.append(peer)

    def update_peer(self, peer):
        for p in self.peers:
            if p == peer:
                return False

        self.add_peer(peer)
        return True

    def update_peers(self, peers):
        updated = False
        for peer in peers:
            updated = updated or self.update_peer(peer)
        return updated

    def get_ipv6(self):
        # google dns
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as sock:
            sock.connect(("2001:4860:4860::8888", 80))
            return sock.getsockname()[0]

    def send(self, data_dict):
        data_json = json.dumps(data_dict).encode()
        data_comp = zlib.compress(data_json)

        for peer in self.peers:
            if peer.ipv6 == self.ipv6:
                continue
 
            try:
                with socket.create_connection((peer.ipv6, peer.port), timeout=5) as sock:
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

    def __del__(self):
        self.sock.close()
