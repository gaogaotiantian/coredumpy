# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import base64
import io
import sys

from ..type_support import TypeSupportContainerBase


class TorchTensorSupport(TypeSupportContainerBase):
    @classmethod
    def get_type(cls):
        def lazy():
            if sys.modules.get("torch"):
                import torch
                return torch.Tensor
            return None
        return lazy, "torch.Tensor"

    @classmethod
    def dump(cls, obj):
        import torch
        buffer = io.BytesIO()
        torch.save(obj, buffer)
        return {"type": "torch.Tensor", "value": base64.b64encode(buffer.getvalue()).decode()}, None

    @classmethod
    def load(cls, data, objects):
        import torch
        buffer = io.BytesIO(base64.b64decode(data["value"]))
        return torch.load(buffer, weights_only=True), None

    @classmethod
    def reload(cls, container, data, objects):
        assert False, "torch.Tensor should never be reloaded"  # pragma: no cover
