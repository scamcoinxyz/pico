# PicoCoin
Tiny IOT-oriented CPU cryptocurrency written in [Python3](https://www.python.org/).

Features:
* Tiny crossplatform blockchain platform with minimum dependencies.
* All data represents in [json](https://en.wikipedia.org/wiki/JSON) format.
* Modern [sha-3](https://en.wikipedia.org/wiki/SHA-3) hashing algorithm.
* Hard to parallel mining algorithm (recursive sequence of [integers factorization](https://en.wikipedia.org/wiki/Integer_factorization)). [See `Notes: 1`]
* 2D difficulty [See `Notes: 2`].
* Oriented to use in weak computing devices like [Orange PI](http://www.orangepi.org/orangepizero/) or [RPI](https://www.raspberrypi.org/).
* Own virtual machine to do actions with device. For example turn on the smart lamp ([IOT](https://en.wikipedia.org/wiki/Internet_of_things)).

Notes:
1. Cores count has no advantage. Single core compute power is more important.
2. `Horizontal` difficulty for factorization and `vertical` for recurse depth.
