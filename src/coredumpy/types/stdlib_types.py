# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import sys

from ..type_support import TypeSupportBase


class DecimalTypeSupport(TypeSupportBase):
    @classmethod
    def get_type(cls):
        def lazy():
            if sys.modules.get("decimal"):
                import decimal
                return decimal.Decimal
            return None
        return lazy, "decimal.Decimal"

    @classmethod
    def dump(cls, obj):
        return {"type": "decimal.Decimal", "value": str(obj)}, None

    @classmethod
    def load(cls, data, objects):
        import decimal
        return decimal.Decimal(data["value"]), None
