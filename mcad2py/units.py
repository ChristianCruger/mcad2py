"""The one Pint registry that generated modules and :mod:`mcad2py.const` share.

Pint quantities from two different ``UnitRegistry`` instances cannot be combined
-- ``c * m`` raises if ``c`` was built elsewhere -- so the constants can only be
importable, pre-built values if there is a single registry for them to live in.
Generated modules therefore ``from mcad2py.units import ureg`` rather than
constructing their own. As a bonus, two converted worksheets imported into the
same process can now exchange values.
"""

from __future__ import annotations

import pint

ureg = pint.UnitRegistry()
