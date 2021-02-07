import argparse

from miner import Miner
from core import User, Block, Blockchain, Invoice, Payment, Message


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PicoCoin core cli.')
    parser.add_argument('--serv',  type=bool, default=False, help='work as server')
    parser.add_argument('--adr',  type=str, default='127.0.0.1', help='server listen address (default: "127.0.0.1")')

    args = parser.parse_args()

    # fake data
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

    block = Block(0, 14, 256, None)
    block.add_trans(Payment(user0, user1.get_pub(), 10, 'mypassword'))
    block.add_trans(Message(user1, user0.get_pub(), 'Hello!', '1234'))
    block.add_trans(Invoice(user2, user1.get_pub(), 5, '1234'))

    chain = Blockchain('0.1')
    chain.add_block(block)

    miner = Miner(block)
    miner.work()

    print(block.pow.work_check())
    print(chain.to_json_with_hash())
    print(f'solved: reward {block.reward} picocoins.')
