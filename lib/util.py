import random
import string
import bpy
from bpy.types import Material
import mathutils
from time import time
from logging import getLogger


logger = getLogger(__name__)


def random_name(n: int) -> str:
    """引数で指定した桁数のランダムなstrを返す"""
    if n < 0:
        raise ValueError
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def object_duplicate_helper(obj: bpy.types.Object, name: str) -> bpy.types.Object:
    """
    オブジェクトに任意の名前をつけて複製するヘルパー　複製したオブジェクトを返す
    """
    _mode = bpy.context.mode
    temp_name = random_name(10)
    orig_name = obj.name
    obj.name = temp_name
    bpy.ops.object.duplicate({"selected_objects": [obj]})
    obj.name = orig_name
    new_obj = bpy.data.objects[temp_name + ".001"]
    new_obj.name = name
    bpy.ops.object.mode_set(mode=_mode)
    new_obj.select_set(False)
    return new_obj


def calc_vector_length(a: mathutils.Vector, b: mathutils.Vector) -> float:
    """2つのベクトルから長さを求める"""
    vec = b - a
    return vec.length


def gp_licker(gp_data: bpy.types.GreasePencil, func, state={}):

    if type(gp_data) is not bpy.types.GreasePencil:
        logger.info("not gpencil")
        raise TypeError

    for li, layer in enumerate(gp_data.layers):
        func(state["layers"][li], layer, "layer")
        for fi, frame in enumerate(layer.frames):
            func(state["layers"][li]["frames"][fi], frame, "frame")
            for si, stroke in enumerate(frame.strokes):
                func(state["layers"][li]["frames"][fi]["strokes"][si], stroke, "stroke")


def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        finish_time = time()
        time_spend = finish_time - start_time
        logger.debug(f"{func.__name__} time: {time_spend*1000}ms")
        return result

    return wrapper


def mesh_transform_apply(
    obj: bpy.types.Object, location=True, rotation=True, scale=True, world=True
):
    """メッシュオブジェクトのトランスフォームを適応する"""
    # mw = obj.matrix_world
    if world is True:
        matrix = obj.matrix_world
    else:
        matrix = obj.matrix_local
    matrix = mathutils.Matrix(matrix)
    loc, rot, sca = matrix.decompose()
    # create a location matrix
    if location:
        mat_loc = mathutils.Matrix.Translation(loc)
    else:
        mat_loc = mathutils.Matrix.Translation((0.0, 0.0, 0.0))

    if scale:
        mat_sca = (
            mathutils.Matrix.Scale(sca[0], 4, (1, 0, 0))
            @ mathutils.Matrix.Scale(sca[1], 4, (0, 1, 0))
            @ mathutils.Matrix.Scale(sca[2], 4, (0, 0, 1))
        )
    else:
        mat_sca = mathutils.Matrix.Scale(1, 4)

    # create a rotation matrix
    if rotation:
        mat_rot = rot.to_matrix()
        mat_rot = mat_rot.to_4x4()
    else:
        mat_rot = mathutils.Matrix.Rotation(0, 4, "X")

    # combine transformations
    mat_out = mat_loc @ mat_rot @ mat_sca

    msh = obj.data
    for v in msh.vertices:
        v.co = mat_out @ v.co

    obj.location = [0, 0, 0]
    obj.rotation_euler = mathutils.Euler()
    obj.scale = [1, 1, 1]


def convert_to_mesh(obj: bpy.types.Object, parent_inheritance=True) -> bpy.types.Object:
    """
    変換可能なオブジェクトをメッシュオブジェクトに変換する
    :return converted_object
    """
    # generate object
    mesh = obj.to_mesh()
    if mesh is None:
        mesh = bpy.data.meshes.new("empty_mesh")
    else:
        mesh = mesh.copy()
    _converted_object = bpy.data.objects.new(f"{obj.name}.{random_name(4)}", mesh)
    bpy.context.scene.collection.objects.link(_converted_object)
    # transform
    _converted_object.location = obj.location
    _converted_object.rotation_euler = obj.rotation_euler
    _converted_object.scale = obj.scale
    # material
    if len(mesh.materials) != 0:
        material_names = obj.material_slots.keys()
        for i, name in enumerate(material_names):
            material = bpy.data.materials.get(name)
            _converted_object.data.materials[i] = material
    # parent
    if parent_inheritance:
        _converted_object.parent = obj.parent
    return _converted_object


def convert_to_curve(
    obj: bpy.types.Object, parent_inheritance=True
) -> bpy.types.Object:
    """
    変換可能なオブジェクトをカーブオブジェクトに変換する
    うまく行かない
    :return converted_object
    """
    curve = obj.to_curve(bpy.context.evaluated_depsgraph_get())
    if curve is None:
        curve = bpy.data.curves.new("empty_curve", "CURVE")
    else:
        curve = curve.copy()
    _converted_object = bpy.data.objects.new(f"{obj.name}.{random_name(4)}", curve)
    bpy.context.scene.collection.objects.link(_converted_object)
    # transform
    _converted_object.location = obj.location
    _converted_object.rotation_euler = obj.rotation_euler
    _converted_object.scale = obj.scale
    # material
    if len(obj.data.materials) != 0:
        material_names = obj.material_slots.keys()
        for i, name in enumerate(material_names):
            material = bpy.data.materials.get(name)
            _converted_object.data.materials[i] = material
    if parent_inheritance:
        _converted_object.parent = obj.parent
    return _converted_object
