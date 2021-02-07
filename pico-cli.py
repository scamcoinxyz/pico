import argparse

from miner import Miner
from core import User, Block, Blockchain, Invoice, Payment, Message


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PicoCoin core cli.')
    parser.add_argument('--serv',  type=bool, default=False, help='work as server')
    parser.add_argument('--adr',  type=str, default='127.0.0.1', help='server listen address (default: "127.0.0.1")')

    args = parser.parse_args()

    # fake data
    chain = Blockchain('0.1')

    wallet_json = '''
    {
        "pub": "8daPw6CSpAjLs2yABmehHXPN38iNiyQkaSfQ1w2yi9krwAPfNeZctawTvULvTYmxRzwr8bP1o9k2drK9uHLXEBk",
        "priv": "3chwQEMvVGt7MwGt6jv1CmzD8daj66H87ggvUQGLtMuataN6yhdk9zkFZGaetPa9XwMGoUtFFcp4Jc19WApGuFwc",
        "hash": "cb6de6ee1b80e6507d2f467091ba0c7bf988dbfd47152712d7c6d08b72c65369"
    }
    '''

    user0 = User.create('mypassword')
    user1 = User.login('5bkjPDt7qjEzGsP3Z5juroA29k6hd58q7NoqpGAQip88TyAFGJipBjMDHKnhuTiRE1awTuWCiZ4AuH7td6W5xBJM', '1234')
    user2 = User.from_json(wallet_json, '1234')

    miner = Miner()

    # block0
    block0 = Block(0, 14, 256, None)
    block0.add_trans(Payment(user0, user1.get_pub(), 10, 'mypassword'))
    block0.add_trans(Message(user1, user0.get_pub(), 'Hello!', '1234'))
    block0.add_trans(Invoice(user2, user1.get_pub(), 5, '1234'))

    miner.set_block(block0)
    miner.work()
    chain.add_block(block0)

    print(f'solved: reward {block0.reward} picocoins.')

    # block 1
    block1 = Block(1, 14, 256, block0.hash().hexdigest())

    miner.set_block(block1)
    miner.work()
    chain.add_block(block1)

    print(f'solved: reward {block1.reward} picocoins.')

    # save blockchain to disk
    with open('blockchain.json', 'w') as f:
        f.write(chain.to_json_with_hash(indent=4))
 