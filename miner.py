from sympy.ntheory import factorint
from core import Block


class Miner:
    def __init__(self, block):
        self.set_block(block)

    def set_block(self, block):
        self.block = block

    def work(self):
        for i in range(self.block.v_diff):
            num, hash = self.block.pow.extract(i)
            factors = factorint(num)
            self.block.add_pow(num, factors)

            print(f'solved {i + 1}/{self.block.v_diff}')

        return self.block.pow
