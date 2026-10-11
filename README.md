# Kipp

| ![kipp](https://s3.laisky.com/uploads/2019/06/nolan-comic-ft.jpg)
| :---------------------------------------------------------------:
|                       Humanistic Utilities

[![versions](https://img.shields.io/badge/version-v0.4.0-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/kipp.svg)](https://badge.fury.io/py/kipp)
[![Commitizen friendly](https://img.shields.io/badge/commitizen-friendly-brightgreen.svg)](http://commitizen.github.io/cz-cli/)

---

[Github](https://github.com/Laisky/kipp/tree/master/kipp)

## Document

TBD

---

## Install

Run:

```sh
$ pip install kipp
```


## Runtime and optional features

Install on Python 3.10 or newer. Use a currently maintained Python release
(Python 3.11–3.14); Python 3.10 remains compatible for existing users but reached
upstream end of life in October 2026. The old Python 2.7/3.6–3.8 metadata
was stale: the existing API already uses modern Python syntax and Tornado 6.

`pip install "kipp[image]"` enables image helpers with Pillow 12;
`pip install "kipp[aio]"` uses the same Tornado 6 dependency as the base library.
`kipp[doc]` uses Sphinx and MyST; `kipp[all]` combines all optional features.
Kipp is a library and has no Docker build or runtime image.

xxhash 1–4 preserve the existing xxh32 cache-key format. Redis clients 5–8
are supported without changing RedisUtils response decoding or transactions.
See [dependency compatibility](docs/dependency-compatibility.md) for release
sources, behavioral controls and local acceptance commands.
