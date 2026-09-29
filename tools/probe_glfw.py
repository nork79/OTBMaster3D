"""Exercise either native GLFW DLL in its own process without changing packages."""
import ctypes as c
import json
from pathlib import Path
import sys

dll = c.CDLL(str(Path(sys.argv[1]).resolve()))
dll.glfwGetVersionString.restype = c.c_char_p
dll.glfwCreateWindow.argtypes = [c.c_int,c.c_int,c.c_char_p,c.c_void_p,c.c_void_p]
dll.glfwCreateWindow.restype = c.c_void_p
for name in ('glfwMakeContextCurrent','glfwSwapBuffers','glfwDestroyWindow'):
    getattr(dll,name).argtypes = [c.c_void_p]
report = {'library':sys.argv[1], 'version':dll.glfwGetVersionString().decode()}
assert dll.glfwInit(), 'glfwInit failed'
try:
    dll.glfwWindowHint(0x00020004, 0)  # GLFW_VISIBLE
    window = dll.glfwCreateWindow(128,128,b'Native runtime verification',None,None)
    assert window, 'Window/context creation failed'
    try:
        dll.glfwMakeContextCurrent(window)
        gl = c.WinDLL('opengl32.dll')
        gl.glClearColor.argtypes = [c.c_float]*4
        gl.glClearColor(0.25,0.5,0.75,1)
        gl.glClear(0x4000)
        gl.glFinish()
        pixels = (c.c_ubyte*4)()
        gl.glReadPixels(64,64,1,1,0x1908,0x1401,pixels)
        assert gl.glGetError() == 0
        assert all(abs(a-b)<=2 for a,b in zip(pixels[:3],[64,128,191])), list(pixels)
        dll.glfwSwapBuffers(window); dll.glfwPollEvents()
        report.update(pixel=list(pixels), ok=True)
    finally:
        dll.glfwDestroyWindow(window)
finally:
    dll.glfwTerminate()
Path(sys.argv[2]).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
