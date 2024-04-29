# coredumpy

[![build](https://github.com/gaogaotiantian/coredumpy/actions/workflows/build_test.yaml/badge.svg)](https://github.com/gaogaotiantian/coredumpy/actions/workflows/build_test.yaml)  [![coverage](https://img.shields.io/codecov/c/github/gaogaotiantian/coredumpy)](https://codecov.io/gh/gaogaotiantian/coredumpy)  [![pypi](https://img.shields.io/pypi/v/coredumpy.svg)](https://pypi.org/project/coredumpy/)  [![support-version](https://img.shields.io/pypi/pyversions/coredumpy)](https://img.shields.io/pypi/pyversions/coredumpy)  [![sponsor](https://img.shields.io/badge/%E2%9D%A4-Sponsor%20me-%23c96198?style=flat&logo=GitHub)](https://github.com/sponsors/gaogaotiantian)

coredumpy saves your crash site for post-mortem debugging.

## Highlights

* Easy to use
* Native support for unittest, pytest and run-time exceptions
* Portable and safe dump
* Utilizes pdb interface

## Usage

### dump

In most cases, you only need to hook `coredumpy` to some triggers

For `Exception` and `unittest`, patch with a simple line

```python
import coredumpy
# Create a dump in "./dumps" when there's an unhandled exception
coredumpy.patch_except(directory='./dumps')
# Create a dump in "./dumps" when there's a unittest failure/error
coredumpy.patch_unittest(directory='./dumps')
```

For `pytest`, you can use `coredumpy` as a plugin

```
# Create a dump in "./dumps" when there's a pytest failure/error
pytest --enable-coredumpy --coredumpy-dir ./dumps
```

<details>

<summary>
Or you can dump the current frame stack manually
</summary>

```python
import coredumpy

# Without frame argument, top frame will be the caller of coredumpy.dump()
coredumpy.dump()
# Specify a specific frame as the top frame to dump
coredumpy.dump(frame)
# Specify a filename to save the dump, without it a unique name will be generated
coredumpy.dump(path='coredumpy.dump')
# You can use a function for path
coredumpy.dump(path=lambda: f"coredumpy_{time.time()}.dump")
# Specify a directory to keep the dump
coredumpy.dump(directory='./dumps')
# Specify the description of the dump for peek
coredumpy.dump(description="a random dump")
```

</details>

### load

Load your dump with

```
coredumpy load <your_dump_file>
```

A [pdb](https://docs.python.org/3/library/pdb.html) debugger will be brought up
and of course not everything is supported.

### peek

If you only need some very basic information of the dump (to figure out which dump
you actually need), you can use `peek` command.

```
coredumpy peek <your_dump_directory>
coredumpy peek <your_dump_file1> <your_dump_file2>
```

## About the data

Besides a couple of builtin types, coredumpy treats almost every object as an
Python object with attributes, and that's what it records in the dump.

It does not use `pickle` so you don't need to have the same run-time environment
when you load the dump. It's also safer to open an arbitrary dump without the
unsafe pickling process.

That being said, most of the objects will not be "restored" as they were when
being dumped. You are in an observer mode where you can inspect attributes of
all objects. None of the methods of the objects would work, nor would any
dymanic features.

## License

Copyright 2024 Tian Gao.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/coredumpy/blob/master/LICENSE).
