from sympy.ntheory import factorint


class MinerBackend:
    MINER_BACKEND_SYMPY = 'sympy'

    def __init__(self, backend):
        self.backend = backend

    def factorint(self, num):
        if self.backend == MinerBackend.MINER_BACKEND_SYMPY:
            return factorint(num)
        raise NotImplementedError()


class Miner:
    def __init__(self, backend=MinerBackend.MINER_BACKEND_SYMPY, block=None):
        self.set_block(block)
        self.backend = MinerBackend(backend)

    def set_block(self, block):
        self.block = block

    def work(self):
        for i in range(self.block.v_diff):
            num = self.block.pow.extract(i)
            factors = self.backend.factorint(num)

            self.block.add_pow(num, factors)
            print(f'solved {i + 1}/{self.block.v_diff}')

        return self.block.pow
