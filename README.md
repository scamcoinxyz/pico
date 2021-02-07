# PicoCoin
Tiny IOT-oriented CPU cryptocurrency written in [Python3](https://www.python.org/).

Dependencies:
* [ecdsa](https://pypi.org/project/ecdsa/)
* [sympy](https://pypi.org/project/sympy/)


### Features
* Tiny crossplatform blockchain platform with minimum dependencies.
* All data represents in [json](https://en.wikipedia.org/wiki/JSON) format.
* Modern [sha-3](https://en.wikipedia.org/wiki/SHA-3) hashing algorithm and [ECC](https://en.wikipedia.org/wiki/Elliptic-curve_cryptography).
* Hard to parallel mining algorithm (recursive sequence of [integers factorization](https://en.wikipedia.org/wiki/Integer_factorization)). [See `Notes: 1`]
* 2D difficulty. [See `Notes: 2`]
* All miners earn coins. [See `Notes: 3`].
* Oriented to use in weak computing devices like [Orange PI](http://www.orangepi.org/orangepizero/) or [RPI](https://www.raspberrypi.org/).
* Transactions can be used for coins transfer, send messages or some device actions. For example, turn on the smart lamp ([IOT](https://en.wikipedia.org/wiki/Internet_of_things)).

Notes:
1. Cores count has no advantage. Single core compute power is more important.
2. `Horizontal` difficulty for factorization and `vertical` for recurse depth (see `Analysis.Difficulty and total supply`).
3. All miners get a piece of reward for their work, if they done it before the next block will be solved (see `Analysis.Mining reward`).


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

#### Difficulty and total supply

##### Horizontal diffuculty
Horizontal diffuculty (next `h_diff`) represents an integer factorization difficulty.
It shows how much bytes we should take from hash, represented as a little-endian integer number and compute it's factorization.

How does it works?

For example `block base` hash is `443ed6d3c313f1d99fea7bb5d04a92cedf2f570eeb7a0f3c9b4bb86fd88dd5b9` and `h_diff=5`.
Let's take first `h_diff` symbols from hash `443ed` and represent it as little-endian integer number `443ed hex = 15549188 dec`.
Next, compute factorization of this number: `15549188 = 2 ^ 2 * 3887297`.

```
max number = 2 ^ (4 * h_diff)
```

So maximum `h_diff` value may be 64 (hash length).

##### Vertical diffuculty
Vertical diffuculty (next `v_diff`) represents recurse depth.
It shows how much we have to repeat factorization with `h_diff`, based on `block base` and previous factorization result.

How does it works?
Okay, in previous section we compute some factorization.
Let's add the result into the `block base` (now doesn't matter how exactly we do it) and compute hash again.

Now we do same steps as described in `Horizontal diffuculty` and repeat this algorithm `v_diff` times recursively.

For example it may be looks like this `h_diff=5, v_diff=3`:
```
443ed6d3c313f1d99fea7bb5d04a92cedf2f570eeb7a0f3c9b4bb86fd88dd5b9 -> [2 ^ 2 * 3887297]
bc048abbaead40480f5c68cd4b143bea72e4e95d32136616052b080ae89386a3 -> [2 ^ 2 * 3887297, 5 * 953551]
8d5fee663cbe207d597944413e2ece256de9cf4292239303b5d5d72ea6644e8a -> [2 ^ 2 * 3887297, 5 * 953551, 2 ^ 3 * 5 * 359 * 1163]
```

So, list of factorizations `[2 ^ 2 * 3887297, 5 * 953551, 2 ^ 3 * 5 * 359 * 1163]` is a block [POW](https://en.wikipedia.org/wiki/Proof_of_work).

##### Calculation

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
max blocks count: 10000 * 64 = 640000 blocks
```
