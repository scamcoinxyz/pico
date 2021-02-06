import hashlib as hlib
from sympy import factorint
from functools import reduce

from core import User, Blockchain, Block


# fake data
chain = Blockchain('0.1')

user0 = User()
user0.login(b'+QxFNyz+6pjsy5IGc4l+/Fs3DvR0t1HK77TEp9BQ30k=')

user1 = User()
user1.create('1234')

block=Block(id=0, h_diff=16, v_diff=5)
block.add_trans(user0, user1.get_keys()['pub'], 10)
block.add_trans(user1, user0.get_keys()['pub'], 5)


# utils
def primes_int(factors):
    return reduce(lambda prev, factor: prev * (factor[0] ** factor[1]), factors.items(), 1)


# miner core
def mine_check_h(block, factors, diff):
    hash = hlib.sha3_256(block)
    num = int.from_bytes(hash.digest()[0:diff], byteorder='little')

    if num == primes_int(factors):
        return True
    return False


def mine_h(block, diff):
    hash = hlib.sha3_256(block)
    num = int.from_bytes(hash.digest()[0:diff], byteorder='little')
    factors = factorint(num)

    res = mine_check_h(block, factors, diff)
    if res:
        return (num, factors)
    return (None, -1)


def mine(block):
    blk = block.base_to_json().encode('ascii')

    for i in range(block.v_diff):
        num, factors = mine_h(blk, block.h_diff)

        if mine_check_h(blk, factors, block.h_diff):
            print(f'solved {i}/{block.v_diff}')
            block.add_pow(num, factors)
            blk = block.to_json().encode('ascii')
    return block.pow


# miner
res = mine(block)
chain.add_block(block)
print(f'solved: reward {block.reward} pico')

print(chain.to_json_with_hash())
