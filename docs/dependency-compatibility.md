# Dependency compatibility in 0.4.0

This is a library. It has no Dockerfile, compose configuration, or container
runtime entry point; there is no application image to upgrade. Local
qualification uses disposable official Python containers without publishing
images or changing running services.

Python 3.10 is retained as a compatibility floor. It reached upstream end of
life on 2026-10-01; new applications should use maintained Python 3.11–3.14 for new deployments. Local qualification covers Python 3.10, 3.12 and 3.14. Python 3.15.0
was released on 2026-10-09, but its stable official Docker image was not yet
available during qualification (the official image manifest still lists
3.15.0rc3). No stable 3.15 qualification is claimed.
The former Python 2.7/3.6–3.8 classifiers and tox jobs were not supported by
the existing annotated API, Python standard-library imports and Tornado 6.
The metadata now states the real floor instead of promising those runtimes.

## Selected dependencies

| Surface | Selection | Compatibility decision |
| --- | --- | --- |
| Tornado | >=6.5.10,<7 | Current fixes; aio extra shares the base constraint, replacing impossible Tornado 4.5 resolution. |
| xxhash | >=1.3,<5 | Keep 1–3 and accept 4 after explicit UTF-8 conversion; frozen xxh32 keys, hits and expiration remain unchanged. |
| Redis client | >=5.2.1,<9 | Keep Redis 5 clients and allow 6–8; decoding, SCAN/MGET and WATCH/MULTI behavior is preserved. |
| Pillow image extra | >=12.3,<13 | Current maintained release, replacing 3.4.2; generated JPEG resize/compress and mocked upload/copy controls cover behavior. |
| Maya | >=0.6.1,<0.7 | 0.6.1 remains its latest release; retain natural-language parsing and date semantics instead of replacing its API. |
| pytz | >=2026.5 | Declare the timezone package used directly by Kipp rather than relying on Maya's transitive dependency. |
| Documentation | Sphinx >=8.1,<10; MyST >=4,<6 | Python-specific resolver selects compatible releases; built-in Napoleon replaces the old external extension. |
| Build | setuptools >=84,<85; wheel >=0.48,<0.49 | PEP 517 build isolation; reading the version does not import runtime dependencies or rewrite README. |

Unused ruamel.yaml and zipp requirements are removed; no Kipp code imports
or exposes either package. The sole python-future import was a Python 2
URL import hook, replaced by the Python 3 standard library. Public Kipp
APIs and the PY2/PY3 constants remain available.

## Behavioral controls and acceptance

The real before-change failures are an unsatisfiable `kipp[aio]`
dependency graph and xxhash 4 raising `TypeError` on the old string input.
The existing frozen xxhash 1.4.4 vectors serve as the independent control.
Bounded async controls also reproduce missed worker-thread wakeups, omission
of already-completed futures, and stopping the wrong explicitly supplied
loop. Thread futures are now bridged with asyncio.wrap_future; completion
notifications use IOLoop.add_callback, while results, exceptions and
deduplication remain compatible.
The full offline suite exercises cache, decorators, date parsing, async/HTTP
adapters, utilities, options, mock Redis, SMTP and generated image helpers.
Legacy tests requiring unavailable Utilities/MySQL and the old disabled
image class remain explicitly reported as skips; current image controls run.

Install `kipp[all]` to check that all extras resolve together. For local
qualification, run `pytest -q --import-mode=importlib -o addopts= tests`
against each installed distribution with external networking disabled.
Use `python -m build`, `python -m twine check --strict dist/*` and
`python -m sphinx -b html -W --keep-going docs /tmp/kipp-docs`.
Hosted CI retains formatting and fast unit/metadata contracts only.
Exact sources, resolved versions, test results and artifact hashes are
recorded in the PR body and acceptance receipt. Original 0.3.3 artifacts
are retained and do not qualify the changed 0.4.0 tree.

## Official sources checked 2026-10-11

- [Python support status](https://devguide.python.org/versions/)
- [Python downloads](https://www.python.org/downloads/)
- [Tornado release notes](https://www.tornadoweb.org/en/stable/releases.html)
- [xxhash 4 release changes](https://github.com/ifduyue/python-xxhash/releases/tag/v4.0.0)
- [Redis client releases](https://github.com/redis/redis-py/releases)
- [Pillow releases](https://pillow.readthedocs.io/en/stable/releasenotes/index.html)
- [Maya package release](https://pypi.org/project/maya/)
- [pytz package release](https://pypi.org/project/pytz/)
- [Sphinx Napoleon](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
- [MyST parser](https://myst-parser.readthedocs.io/en/latest/intro.html)
- [PyPA build](https://build.pypa.io/en/stable/)

- [Official Python image manifest](https://github.com/docker-library/official-images/blob/master/library/python)
