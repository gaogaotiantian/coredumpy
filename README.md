# coredumpy

coredumpy saves your crash site so you can better debug your python program.

## Highlights

* Easy to use
* Supports pdb interface
* Does not rely on pickle
* Dump file is independent of environment

## Usage

### dump

You can dump any frame (and its parent frames) manually by

```python
from coredumpy import dump

dump("coredumpy_dump", frame)

# without frame argument, it will dump the current frame stack
dump("coredumpy_dump")
```

You can hook the exception so a dump will be automatically created if your program crashes due to an exception

```python
from coredumpy import patch_excepthook
patch_excepthook()
```

### load

Load your dump with

```
coredumpy load <your_dump_file>
```

A [pdb](https://docs.python.org/3/library/pdb.html) debugger will be brought up
and of course not everything is supported.

Objects are not "recreated" in the load process, which makes it safe to even
open an unknown dump (not recommended though). You will be in an "observer"
mode where you can access certain types of value of the variables and attributes,
but none of the user-created objects will have the actual functionality.

## Disclaimer

This library is still in development phase and is not recommended for production use.

## License

Copyright 2024 Tian Gao.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/coredumpy/blob/master/LICENSE).