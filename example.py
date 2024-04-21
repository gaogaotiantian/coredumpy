from coredumpy import patch_excepthook

patch_excepthook()


def g(arg):
    return 1 / arg

def f():
    arg = 0
    g(arg)

f()