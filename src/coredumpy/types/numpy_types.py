# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import base64
import io
import sys

from ..type_support import TypeSupportContainerBase


class NumpyArraySupport(TypeSupportContainerBase):
    @classmethod
    def get_type(cls):
        def lazy():
            if sys.modules.get("numpy"):
                import numpy

                return numpy.ndarray
            return None

        return lazy, "numpy.ndarray"

    @classmethod
    def dump(cls, obj):
        import numpy

        buffer = io.BytesIO()
        numpy.save(buffer, obj, allow_pickle=False)
        return {
            "type": "numpy.ndarray",
            "value": base64.b64encode(buffer.getvalue()).decode(),
        }, None

    @classmethod
    def load(cls, data, objects):
        import numpy

        buffer = io.BytesIO(base64.b64decode(data["value"]))
        return numpy.load(buffer, allow_pickle=False), None

    @classmethod
    def reload(cls, container, data, objects):
        assert False, "numpy.array should never be reloaded"  # pragma: no cover
