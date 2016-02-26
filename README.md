# Bottle Cap

[![Travis CI](https://travis-ci.org/imsofly/bottlecap.svg)](https://travis-ci.org/imsofly/bottlecap)
[![Coverage Status](https://coveralls.io/repos/imsofly/bottlecap/badge.svg?branch=master&service=github)](https://coveralls.io/github/imsofly/bottlecap?branch=master)
[![Python Versions](https://img.shields.io/pypi/pyversions/bottlecap.svg)](https://pypi.python.org/pypi/bottlecap)
[![PyPI](https://img.shields.io/pypi/v/bottlecap.svg)](https://pypi.python.org/pypi/bottlecap)

> **WARNING: This library is still in development, not production ready**


Collection of useful extras for Bottle, including;

* Rich media types handling
* Content Negotiation (done properly)
* Class Based Views
* Management CLI via Click


## Getting started

```
pip install bottlecap
```

## Testing

```
make clean
python setup.py test
python3 setup.py test
tox
```

## Todo

```
XXX: Add support for decorators
XXX: Fix coverage report
XXX: Add tox support
XXX: Add PEP8 checks
XXX: Plugin for extracting IP from HTTP_X_FORWARDED_FOR?
XXX: Plugin for debug toolbar of some sort?
XXX: Plugin for werkzeug.DebuggedApplication?
XXX: Add support for Accept-Language
XXX: Add support for X-Real-Ip and accepted IPs
XXX: Add support for pylint
XXX: Add support for prospector
XXX: Clean up TempFile
XXX: Refactor into groups
XXX: Split media type handling into its own repo?
```