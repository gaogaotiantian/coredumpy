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

For `pytest`, you can use `coredumpy` as a plugin

```
# Create a dump in "./dumps" when there's a pytest failure/error
pytest --enable-coredumpy --coredumpy-dir ./dumps
```

For `Exception` and `unittest`, you can use `coredumpy run` command.
A dump will be generated when there's an unhandled exception or a test failure

```
# with no argument coredumpy run will generate the dump in the current dir
coredumpy run my_script.py
coredumpy run my_script.py --directory ./dumps
coredumpy run -m unittest --directory ./dumps
```

Or you can patch explicitly in your code and execute the script/module as usual

```python
import coredumpy
# Create a dump in "./dumps" when there's an unhandled exception
coredumpy.patch_except(directory='./dumps')
# Create a dump in "./dumps" when there's a unittest failure/error
coredumpy.patch_unittest(directory='./dumps')
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
# Set the search depth to 2 to reduce the dump size
coredumpy.dump(depth=2)
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

## Type support

`coredumpy` supports the common built-in types like `float`, `int`, `str`, `list`,
`dict` etc. For all the other types that it can't recognize, it will treat them as
a Python object, which means `coredumpy` will iterate and store all the attributes
of the object.

You can add support for any arbitrary types by creating a class that inherits
`coredumpy.TypeSupportBase`. You need to finish the following class methods in
order to make it work:

```python
@classmethod
def get_type(cls) -> tuple[Union[type, Callable], str]:
    # returns a tuple with two elements:
    # 0. type (or a callable for lazy load) for dump
    #    coredumpy will dispatch the objects with this type to the dump method
    # 1. a type string for load
    #    coredumpy will dispatch the data with this type to the load method

@classmethod
def dump(cls, obj) -> tuple[dict, Optional[list]]:
    # takes the object to be dumped
    # returns a tuple with two elements:
    # 0. a json-serializable dict, which will be stored in the dump file
    # 1. a list that contains the objects needed to be dumped for this object
    #    if none needed (the object is not a container), use None

@classmethod
def load(cls, data: dict, objects: dict) -> tuple[object, Optional[list[str]]]:
    # takes the dict data from `dump` method and a dict of all objects with the ids
    # as keys
    # returns a tuple with two elements:
    # 0. the restored object. If not ready, return coredumpy.NotReady
    # 1. a list of the ids of dependent objects, if not applicable, use None
```

If the type is a container, inherit `coredumpy.TypeSupportContainerBase` and
implement an extra method:

```python
@classmethod
def reload(cls, container, data, objects: dict) -> tuple[object, Optional[list[str]]]:
    # takes the already built container, the other arguments are the same as `load`
    # returns the same as `load`
    # This is helpful to create a placeholder first with `load` so the other objects
    # can reference to it, and build the placeholder later
```

You only need to create the class, it will be automatically registered.

## Startup script

In order to import the type supports and do some customization, `coredumpy` provides
a way to run an arbitrary script after importing `coredumpy`. You can put a
`conf_coredumpy.py` file in your current working directory. If `coredumpy` discovers
it, the script will be executed. You can put anything you need in the script.

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

Copyright 2024-2025 Tian Gao.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/coredumpy/blob/master/LICENSE).
