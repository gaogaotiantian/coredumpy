# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


class _Unknown:
    def __repr__(self):
        return "<Unknown Object>"


_unknown = _Unknown()


class PyObjectProxy:
    def __init__(self):
        self._coredumpy_attrs = {}
        self._coredumpy_container = None

    def link_container(self, container):
        self._coredumpy_container = container

    def __setattr__(self, key, value):
        if key.startswith("_coredumpy_"):
            self.__dict__[key] = value
        else:
            self._coredumpy_attrs[key] = value

    def __getattr__(self, item):
        if self._coredumpy_container is None:
            raise RuntimeError("Container is not linked")
        if item in self._coredumpy_attrs:
            return self._coredumpy_container._proxies.get(self._coredumpy_attrs[item], _unknown)
        raise AttributeError(f"'{self._coredumpy_type}' object has no attribute '{item}'")

    def __repr__(self):
        return f"<{self._coredumpy_type} object at 0x{int(self._coredumpy_id):x}>"

    def __dir__(self):
        return list(self._coredumpy_attrs.keys())
