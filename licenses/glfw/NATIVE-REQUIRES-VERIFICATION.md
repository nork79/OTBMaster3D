# Remediation update — 2026-09-28

Native GLFW 3.4 source and NATIVE-LICENSE.txt are collected. Exact binary build options and MSVCR120 redistribution entitlement remain under review.

## Historical finding

# Native GLFW and its runtime

The Python glfw 2.10.2 wrapper licence is copied in LICENSE.txt. It is distinct
from the GLFW 3.4.0 DLL loaded by this environment. Native GLFW uses the zlib/libpng
licence according to https://www.glfw.org/license.html . Obtain its exact COPYRIGHT
file from the matching upstream source: https://github.com/glfw/glfw/tree/3.4 .

The installed wrapper also contains msvcr120.dll. Verify its provenance and
Microsoft redistribution rights before release. Do not treat it as MIT or GLFW code.
