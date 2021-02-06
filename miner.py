import hashlib as hlib
from sympy import factorint
from functools import reduce

from core import Blockchain, Block, h_diff_shift


# fake data
chain = Blockchain('0.1')

block=Block(id=0, h_diff=4, v_diff=5)
block.add_trans('A', 'B', 10)
block.add_trans('B', 'C', 20)

chain.add_block(block)

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
    print(blk)

    for _ in range(block.v_diff):
        num, factors = mine_h(blk, block.h_diff + h_diff_shift)

        if mine_check_h(blk, factors, block.h_diff + h_diff_shift):
            block.add_pow(num, factors)
            blk = block.to_json().encode('ascii')
            print(blk)
    return block.pow


# miner
# res = mine(block)
# print(f'solved: reward {block.reward} pico')

print(chain.to_json_with_hash())
