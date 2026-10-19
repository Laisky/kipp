# xxhash compatibility

Kipp uses `xxhash.xxh32(...).hexdigest()` to derive timeout-cache keys.
The previous `xxhash~=1.3` dependency cap prevents installation alongside
modern consumers such as LangSmith 0.8.18, which requires xxhash 3 or newer.

The reviewed constraint permits xxhash 1.x, 2.x and 3.x while keeping an upper
bound before unqualified 4.x. It retains the old lower bound and the existing
xxh32 algorithm; it does not migrate cached data to xxh3.

`tests/test_hash_compatibility.py` stores seven public golden cache keys
captured with the released Kipp 0.3.2 and xxhash 1.4.4. These include empty and
positional arguments, Unicode, bytes, booleans and keyword arguments. The
behavior test checks actual cache hits, distinct arguments and expiration
with a synthetic clock. No Redis, SMTP or other service is contacted.

Qualification must use ordinary supported dependency resolution after the
constraint change, and exercise Python 3.10 and 3.12 with the supported hash
versions. A consumer must not install a new xxhash by ignoring the old Kipp
metadata. Package publication and adoption remain separate from this source
patch.

Official API reference:
[python-xxhash](https://github.com/ifduyue/python-xxhash/blob/master/README.rst).

## Qualification completed

On Python 3.10.14 and 3.12.15, 71 tests from the existing decorator suites and
the new golden-key contracts passed for each of xxhash 1.4.4, 2.0.2 and 3.8.1.
The 2.0.2 wheels were built locally from the official SHA-256-verified source;
the other artifacts were verified official releases. Runs used a bounded
offline container and the shared nonblocking heavy-validation lock.

Normal resolution of Ramjet's complete frozen graph with LangSmith 0.8.18 and
xxhash 3.8.1 reproduced the published Kipp cap failure on both interpreters.
A wheel built from this actual maintainer source with the reviewed cap change
resolved the complete graph normally, preserving other baseline pins and
adding required dependencies. No upstream cap was overridden.

The new single-job CI runs formatting and the two fast deterministic cache
contracts with ordinary `pip install .`; the full compatibility matrix stays
local. Package publication is still required before an official-release-only
consumer can adopt the changed metadata.
