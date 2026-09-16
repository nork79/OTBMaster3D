"""Run with Blender 2.79: blender -b scifi_chess.blend --disable-autoexec -P tools/convert_scifi.py.

Exports Drummyfish's CC0 chassis and their child wheels, with applied modifiers,
triangulation, world transforms and conversion from Z-up to Y-up.
"""
import bpy
import bmesh
from pathlib import Path

target = Path(__file__).resolve().parents[1]/'assets'/'pieces'/'scifi'
target.mkdir(parents=True,exist_ok=True)

def descendants(obj):
    yield obj
    for child in obj.children:
        yield from descendants(child)

for name in ('pawn','knight','bishop','rook','queen','king'):
    count = 0
    with (target/(name+'.obj')).open('w') as output:
        output.write('# Sci-fi chess by Drummyfish (CC0); converted for OTBMaster3D\n')
        for obj in descendants(bpy.data.objects[name]):
            if obj.type != 'MESH':
                continue
            mesh = obj.to_mesh(bpy.context.scene,True,'PREVIEW')
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm,faces=list(bm.faces))
            bm.to_mesh(mesh)
            bm.free()
            for vertex in mesh.vertices:
                point = obj.matrix_world * vertex.co
                output.write('v {:.7f} {:.7f} {:.7f}\n'.format(point.y,point.z,point.x))
            for triangle in mesh.polygons:
                output.write('f {} {} {}\n'.format(*(count+i+1 for i in triangle.vertices)))
            count += len(mesh.vertices)
            bpy.data.meshes.remove(mesh)
    print('Exported',name,count,'vertices')
