# PicoCoin
Tiny IOT-oriented CPU cryptocurrency written in [Python3](https://www.python.org/).

Dependencies:
* [base58](https://pypi.org/project/base58/)
* [pycryptodome](https://pypi.org/project/pycryptodome/)
* [ecdsa](https://pypi.org/project/ecdsa/)
* [sympy](https://pypi.org/project/sympy/)


### Features
* Tiny crossplatform blockchain platform with minimum dependencies.
* All data represents in [json](https://en.wikipedia.org/wiki/JSON) format.
* Modern [sha-3](https://en.wikipedia.org/wiki/SHA-3) hashing algorithm and [ECC](https://en.wikipedia.org/wiki/Elliptic-curve_cryptography).
* Hard to parallel mining algorithm (recursive sequence of [integers factorization](https://en.wikipedia.org/wiki/Integer_factorization)). [See `Notes: 1`]
* 2D difficulty. [See `Notes: 2`].
* All miners earn coins. [See `Notes: 3`].
* Block solver protection. [See `Notes: 4`].
* Oriented to use in weak computing devices like [Orange PI](http://www.orangepi.org/orangepizero/) or [RPI](https://www.raspberrypi.org/).
* Transactions can be used for coins transfer, send messages or some device actions. For example, turn on the smart lamp ([IOT](https://en.wikipedia.org/wiki/Internet_of_things)).

Notes:
1. Cores count has no advantage. Single core compute power is more important.
2. **Horizontal** difficulty for factorization and **vertical** for recurse depth (see `Mining algorithm`).
3. All miners get a piece of reward for their work, if they done it before the next block will be solved (see `Analysis.Mining reward`).
4. Mining algorithm designed in as such way that **proof of work** is related to **block solver**. To cheat it you have to redone all work again (see `Mining algorithm`).


### JSON API

#### User
API:
```
{
    "pub": <public key | str>,
    "priv": <aes-encrypted private key | str>,
    "hash: <json hash without this field | str>
}
```

Example:
```json
{
    "pub": "61hcyvtRQCbqWyGXnPGysEZLsNdDWkCqYhvHMQu5adBkM6Dy74YrLhqhfJ6X4YwJuBgw9EMcSAsR7jaP8NY1xNLa",
    "priv": "5mrjZ3cTgxDUCtXNP3uLW2ZL5LFXEJsASPawX7XWVf9UPvikEYRsF2r7NqDgrU8vVrxw8mhsJKPHjFg6hjHU7urV",
    "hash": "5d4d8c5f404b400193a26d2d749011f60e484fe95238a8bf7ba965c091b7eb68"
}
```

```
# hash
5d4d8c5f404b400193a26d2d749011f60e484fe95238a8bf7ba965c091b7eb68 = sha3-256(
    {
        "pub": "61hcyvtRQCbqWyGXnPGysEZLsNdDWkCqYhvHMQu5adBkM6Dy74YrLhqhfJ6X4YwJuBgw9EMcSAsR7jaP8NY1xNLa",
        "priv": "5mrjZ3cTgxDUCtXNP3uLW2ZL5LFXEJsASPawX7XWVf9UPvikEYRsF2r7NqDgrU8vVrxw8mhsJKPHjFg6hjHU7urV"
    }
)
```

#### Transaction
API:
```
{
    "time": <UTC timestamp: year-month-day hour:minute:second.millis | str>,
    "from": <sender pub key | str>,
    "to": <receiver pub key | str>,
    "act": {
        <
            "ivc": <invoice coins amount | int> |
            "pay": <payment coins amount | int> |
            "msg": <message | str>
        >
    },
    "sign": <sender digital signature of json without this field and "hash" | str>,
    "hash": <json hash without this field | str>
}
```

Example:
```json
{
    "time": "2021-02-10 08:16:38.900597",
    "from": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
    "to": "661hcyvtRQCbqWyGXnPGysEZLsNdDWkCqYhvHMQu5adBkM6Dy74YrLhqhfJ6X4YwJuBgw9EMcSAsR7jaP8NY1xNLa",
    "act": {
        "pay": 10
    },
    "sign": "4ME9bhoHjzMsv1pbwCwtde3w8GPH2kJVFm5r2ww4bTCGBzyc3wGfdHKCctwTsSRrFR1W7ZooLYLEzKgHQh3Pu5B8",
    "hash": "cf9e71ba2962a7125a547b6dba6f7615f18b149df937638690d23b132b97e290"
}
```

```
# sign
4ME9bhoHjzMsv1pbwCwtde3w8GPH2kJVFm5r2ww4bTCGBzyc3wGfdHKCctwTsSRrFR1W7ZooLYLEzKgHQh3Pu5B8 = user("from").sign(
    {
        "time": "2021-02-10 08:16:38.900597",
        "from": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
        "to": "661hcyvtRQCbqWyGXnPGysEZLsNdDWkCqYhvHMQu5adBkM6Dy74YrLhqhfJ6X4YwJuBgw9EMcSAsR7jaP8NY1xNLa",
        "act": {
            "pay": 10
        }
    }
)
```

```
# hash
cf9e71ba2962a7125a547b6dba6f7615f18b149df937638690d23b132b97e290 = sha3-256(
    {
        "time": "2021-02-10 08:16:38.900597",
        "from": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
        "to": "661hcyvtRQCbqWyGXnPGysEZLsNdDWkCqYhvHMQu5adBkM6Dy74YrLhqhfJ6X4YwJuBgw9EMcSAsR7jaP8NY1xNLa",
        "act": {
            "pay": 10
        },
        "sign": "4ME9bhoHjzMsv1pbwCwtde3w8GPH2kJVFm5r2ww4bTCGBzyc3wGfdHKCctwTsSRrFR1W7ZooLYLEzKgHQh3Pu5B8"
    }
)
```

#### Block
API:
```
{
    "prev": <hash of previous block | str>,
    "time": <UTC timestamp: year-month-day hour:minute:second.millis | str>,
    "h_diff": <horizontal difficulty (see Mining algorithm.Horizontal difficulty) | int>,
    "v_diff": <vertical difficulty (see Mining algorithm.Vertical difficulty) | int>,
    "trans": [
        <transaction hash>: <transaction | Transaction>
        ...
    ],
    "pow": {
        "solver": <block solvers pub key | str>,
        "work": {
            <number | str>: {
                <prime factor | str>: <power | int>,
                ...
            },
            ...
        }
    },
    "hash": <json hash without this field | str>
}
```

Example:
```json
{
    "prev": null,
    "time": "2021-02-10 08:38:21.571702",
    "h_diff": 14,
    "v_diff": 2,
    "trans": {
        "90fb9c4688b42fdfb1cef586d1288c213e798861f6634356321bc99378209f53": {
            "time": "2021-02-10 08:38:18.603889",
            "from": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
            "to": "61hcyvtRQCbqWyGXnPGysEZLsNdDWkCqYhvHMQu5adBkM6Dy74YrLhqhfJ6X4YwJuBgw9EMcSAsR7jaP8NY1xNLa",
            "act": {
                "pay": 10
            },
            "sign": "2jFDAeRFQWpGEe1qgjL9boTYimaVJZQtk8kbjdCYTS2McuMxsqM2Hcn5KH3SqUCDawY7FG4GM2Rc5EVoB3kmaSJN",
            "hash": "90fb9c4688b42fdfb1cef586d1288c213e798861f6634356321bc99378209f53"
        }
    },
    "pow": {
        "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
        "work": {
            "3722178976975802242873193524243180": {
                "2": 2,
                "5": 1,
                "43": 1,
                "73": 1,
                "18547961": 1,
                "3196537225922692249021": 1
            },
            "393962739749981897166309425002703": {
                "47": 1,
                "8382185952127274407793817553249": 1
            }
        }
    },
    "hash": "5b72f218eb525702f43221c225cd1331303db12260126718ac551043b3e2f361"
}
```
```
3722178976975802242873193524243180 = 2 ^ 2 * 5 * 43 * 73 * 18547961 * 3196537225922692249021

393962739749981897166309425002703 = 47 * 8382185952127274407793817553249
```

#### Blockchain
API:
```
{
    "coin": <cryptocurrency name | str>,
    "ver": <blockchain version | str>,
    "blocks": {
        <block hash | str>: <block | Block>,
        ...
    },
    "hash": <json hash without this field | str>
}
```

Example:
```json
{
    "coin": "PicoCoin",
    "ver": "0.1",
    "blocks": {
        "5b72f218eb525702f43221c225cd1331303db12260126718ac551043b3e2f361": {
            "prev": null,
            "time": "2021-02-10 08:38:21.571702",
            "h_diff": 14,
            "v_diff": 2,
            "trans": {
                "90fb9c4688b42fdfb1cef586d1288c213e798861f6634356321bc99378209f53": {
                    "time": "2021-02-10 08:38:18.603889",
                    "from": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
                    "to": "61hcyvtRQCbqWyGXnPGysEZLsNdDWkCqYhvHMQu5adBkM6Dy74YrLhqhfJ6X4YwJuBgw9EMcSAsR7jaP8NY1xNLa",
                    "act": {
                        "pay": 10
                    },
                    "sign": "2jFDAeRFQWpGEe1qgjL9boTYimaVJZQtk8kbjdCYTS2McuMxsqM2Hcn5KH3SqUCDawY7FG4GM2Rc5EVoB3kmaSJN",
                    "hash": "90fb9c4688b42fdfb1cef586d1288c213e798861f6634356321bc99378209f53"
                }
            },
            "pow": {
                "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
                "work": {
                    "3722178976975802242873193524243180": {
                        "2": 2,
                        "5": 1,
                        "43": 1,
                        "73": 1,
                        "18547961": 1,
                        "3196537225922692249021": 1
                    },
                    "393962739749981897166309425002703": {
                        "47": 1,
                        "8382185952127274407793817553249": 1
                    }
                }
            },
            "hash": "5b72f218eb525702f43221c225cd1331303db12260126718ac551043b3e2f361"
        }
    },
    "hash": "79deaba94be62d7f34c9d531eaccf9d052731f475c816f5db81debb1296a09a8"
}
```

### Mining algorithm
##### Horizontal difficulty
Horizontal diffuculty (next `h_diff`) represents an integer factorization difficulty.
It shows how much bytes we should take from hash, represented as a little-endian integer number and compute it's factorization.

How does it works?

Let our user public key is: `33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd`

For example, we create block:
```json
{
    "prev": null,
    "time": "2021-02-10 08:58:35.929170",
    "h_diff": 5,
    "v_diff": 3,
    "trans": {},
    "pow": {
        "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
        "work": {}
    },
    "hash": "b679d52413204d71b708b680924401e2a4030faa4c302b2941994e95cdd7e989"
}
```

Let's take first `h_diff` bytes from hash `b679d52413` and represent it as little-endian integer number `b679d52413 hex = 82222348726 dec`.
Next, compute factorization of this number: `82222348726 = 2 * 7 * 257 * 997 * 22921`.

Our first iteration of [POW](https://en.wikipedia.org/wiki/Proof_of_work) is:
```json
"pow": {
    "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
    "work": {
        "82222348726": {
            "2": 1,
            "7": 1,
            "257": 1,
            "997": 1,
            "22921": 1
        }
    }
}
```

##### Vertical difficulty
Vertical diffuculty (next `v_diff`) represents recurse depth.
It shows how much we have to repeat factorization with `h_diff`, based on `block` and previous factorization result.

How does it works?
Okay, in previous section we compute some factorization.
Result block now looks like this:
```json
{
    "prev": null,
    "time": "2021-02-10 08:58:35.929170",
    "h_diff": 5,
    "v_diff": 3,
    "trans": {},
    "pow": {
        "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
        "work": {
            "82222348726": {
                "2": 1,
                "7": 1,
                "257": 1,
                "997": 1,
                "22921": 1
            }
        }
    },
    "hash": "837fb16f29f88700df7e1e985572c43dd72f21df2b087dd786539f35274b8358"
}
```

As you can see, block hash has changed after we added the result of first iteration to block.

Now we do same steps as described in `Horizontal diffuculty` and repeat this algorithm `v_diff` times recursively.

For example it may be looks like this `h_diff=5, v_diff=3`:
```json
# v_diff=1
# b679d52413 hex = 82222348726 dec = 2 * 7 * 257 * 997 * 22921

"pow": {
    "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
    "work": {
        "82222348726": {
            "2": 1,
            "7": 1,
            "257": 1,
            "997": 1,
            "22921": 1
        }
    }
},
"hash": "837fb16f29f88700df7e1e985572c43dd72f21df2b087dd786539f35274b8358"
```

```json
# v_diff = 2
# 837fb16f29 hex = 177967562627 dec = 31 * 5740889117

"pow": {
    "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
    "work": {
        "82222348726": {
            "2": 1,
            "7": 1,
            "257": 1,
            "997": 1,
            "22921": 1
        },
        "177967562627": {
            "31": 1,
            "5740889117": 1
        }
    }
},
"hash": "dc24552d6dabea5af6e55b1ecf3a38bd9b0b74251f247fd7689ac6f5a6bde990"
```

```json
# v_diff = 3
# dc24552d6d hex = 468911989980 dec = 2 ^ 2 * 3 ^ 3 * 5 * 7 * 19 ^ 2 * 343631

"pow": {
    "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
    "work": {
        "82222348726": {
            "2": 1,
            "7": 1,
            "257": 1,
            "997": 1,
            "22921": 1
        },
        "177967562627": {
            "31": 1,
            "5740889117": 1
        },
        "468911989980": {
            "2": 2,
            "3": 3,
            "5": 1,
            "7": 1,
            "19": 2,
            "343631": 1
        }
    }
},
"hash": "ccb2419644437fae9b7737d8dc2492b920ffd1d26fa883c350f38cd5c84ae54b"
```

At least total result block:
```json
{
    "prev": null,
    "time": "2021-02-10 08:58:35.929170",
    "h_diff": 5,
    "v_diff": 3,
    "trans": {},
    "pow": {
        "solver": "33QKSQexZ25RJURDXtJ3NfFfD8XTgn5WPeS1Vim7hd6zcRNHE4ZAqRsDb7Npd36jRMceFkcrcDdTQDxUz6Qh6djd",
        "work": {
            "82222348726": {
                "2": 1,
                "7": 1,
                "257": 1,
                "997": 1,
                "22921": 1
            },
            "177967562627": {
                "31": 1,
                "5740889117": 1
            },
            "468911989980": {
                "2": 2,
                "3": 3,
                "5": 1,
                "7": 1,
                "19": 2,
                "343631": 1
            }
        }
    },
    "hash": "ccb2419644437fae9b7737d8dc2492b920ffd1d26fa883c350f38cd5c84ae54b"
}
```

As you can see, the **proof of work** depends on **block solver** public key. If you change it, you have to recompute all work again.

### Analysis
#### Mining reward
Now network is designed for an average of 1M users and about 100k miners (10% of network).
All miners get a reward for their work, if they done it before the next block will be solved.

First block solver is fully rewarded, all other miners get `reward / 1000000`. If more than 10% of all users will be miners - the piece of reward will decrease proportionally.

Why only 10% and 1 / 1000000?

For example, the reward for block solving is `256` coins.
Horizontal difficulty increase and reward decrease every 10000 blocks (let's call it `round`).

So, total coin emission for round will be `2560000` coins.
Okay, single miner that does not solve block first gets `0.000256` coins per block and totally `2.56` coins per round.

If there are 10% such miners of 1M users, round coin emission will be increased to `256000` coins.

So maximum emission per round will be not changed so much - `2816000` coins.
In other words, it's a mechanism to prevent the inflation.

#### Coin calculation

```
h_diff: 1..64
v_diff: 8192..1

v_diff = max(1, 2 ^ (13 - 3 * h_diff // 8))
```

| h_diff  | v_diff     |
|---------|------------|
| 1 | 8192 |
| 2 | 8192 |
| 3 | 4096 |
| 4 | 4096 |
| 5 | 4096 |
| 6 | 2048 |
| 7 | 2048 |
| 8 | 1024 |
| 9 | 1024 |
| 10 | 1024 |
| 11 | 512 |
| 12 | 512 |
| 13 | 512 |
| 14 | 256 |
| 15 | 256 |
| 16 | 128 |
| 17 | 128 |
| 18 | 128 |
| 19 | 64 |
| 20 | 64 |
| 21 | 64 |
| 22 | 32 |
| 23 | 32 |
| 24 | 16 |
| 25 | 16 |
| 26 | 16 |
| 27 | 8 |
| 28 | 8 |
| 29 | 8 |
| 30 | 4 |
| 31 | 4 |
| 32 | 2 |
| 33 | 2 |
| 34 | 2 |
| 35 | 1 |
| ... | 1 |
| 64 | 1 |

To avoid block size leak, blockchain initial `h_diff=14`.

```
h_diff initial: 14
v_diff initial: 256

h_diff increment: every 10000 blocks

average block solve time: 1..5 min
average h_diff change: 7..35 days

block first solver reward: 2 ^ (8 - 8 * (h_diff - 14) / 50)
other block solvers reward: (first solver reward) / 1000000
```


| h_diff  | reward   |
|---------|----------|
| 14 | 256.0 |
| 15 | 229.12641815756092 |
| 16 | 205.0738886629432 |
| 17 | 183.54627174602584 |
| 18 | 164.27851488805177 |
| 19 | 147.0333894396205 |
| 20 | 131.59856981197652 |
| 21 | 117.78401927998401 |
| 22 | 105.41965021024934 |
| 23 | 94.35322990663052 |
| 24 | 84.44850628946526 |
| 25 | 75.58353033148995 |
| 26 | 67.64915459592835 |
| 27 | 60.54768939043814 |
| 28 | 54.19169999120173 |
| 29 | 48.50293012833273 |
| 30 | 43.41133847832548 |
| 31 | 38.85423630064148 |
| 32 | 34.77551560083386 |
| 33 | 31.124958317193137 |
| 34 | 27.85761802547597 |
| 35 | 24.933266549136004 |
| 36 | 22.315898661606493 |
| 37 | 19.973288782425794 |
| 38 | 17.87659420915552 |
| 39 | 16.0 |
| 40 | 14.320401134847558 |
| 41 | 12.81711804143395 |
| 42 | 11.471641984126615 |
| 43 | 10.267407180503236 |
| 44 | 9.18958683997628 |
| 45 | 8.224910613248532 |
| 46 | 7.3615012049990005 |
| 47 | 6.588728138140584 |
| 48 | 5.897076869164403 |
| 49 | 5.278031643091579 |
| 50 | 4.723970645718122 |
| 51 | 4.228072162245522 |
| 52 | 3.7842305869023836 |
| 53 | 3.386981249450108 |
| 54 | 3.0314331330207955 |
| 55 | 2.7132086548953445 |
| 56 | 2.428389768790094 |
| 57 | 2.1734697250521164 |
| 58 | 1.945309894824571 |
| 59 | 1.741101126592248 |
| 60 | 1.5583291593209994 |
| 61 | 1.3947436663504058 |
| 62 | 1.248330548901612 |
| 63 | 1.11728713807222 |
| 64 | 1.0 |


```
max supply: sum(10000 * 2 ^ (8 - 8 * (i - 14) / 50), i: 14..64) + 10% ~ 26731665 coins
max blocks count: 10000 * (64 - 14) = 500000 blocks
```
