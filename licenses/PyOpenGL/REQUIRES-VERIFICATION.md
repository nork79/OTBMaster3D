# Remediation update — 2026-09-28

Full pinned 3.1.10 sdist licence has been acquired as LICENSE.txt. The earlier URL failure is resolved.

## Historical finding

# PyOpenGL 3.1.10 — requires verification before release

Installed package metadata did not provide a License or License-Expression field
or a top-level licence file. Do not infer the exact grant from package popularity.
Obtain the licence/copyright notices from the matching upstream source distribution:
https://github.com/mcfletch/pyopengl
https://pypi.org/project/PyOpenGL/3.1.10/

Optional OpenGL/DLLS/freeglut_COPYING.txt and gle_COPYING files describe separate
components, not the whole Python package. This app uses GL/GLU, not GLUT/GLE;
the draft deployment excludes those optional DLLs. Verify the resulting binary list.
