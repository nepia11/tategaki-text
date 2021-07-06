# コピペする用　__init__への登録は解除しといたほうが良い
import bpy
from logging import getLogger
from .util import random_name
import mathutils
from math import pi


logger = getLogger(__name__)

translation = bpy.app.translations.pgettext


class TategakiTextUtil:
    """縦書きテキスト用のutilとかをまとめておく"""

    # 特殊文字の判定
    @staticmethod
    def decision_special_character(single_str: str):
        """文字のタイプを判定して返す"""
        if single_str in "、。,.":
            return "upper_right"
        elif single_str in "[]()<>＜＞「」｛｝{}-ー―=＝~〜":
            return "rotation"
        else:
            return "normal"

    @staticmethod
    def insertion_newline_code(strings: str):
        """文字列に改行コードを挿入"""
        inserted = [moji + "\n" for moji in strings]
        return inserted

    @staticmethod
    def create_text_objects(name: str, count: int = 1):
        """任意個のテキストオブジェクトを名前をつけて生成、テキストオブジェクトのリストを返す"""
        objects = []
        append = objects.append
        for i in range(count):
            bpy.ops.object.text_add(location=(0, 0, 0))
            obj = bpy.context.active_object
            obj.name = f"{name}.{i}"
            data: bpy.types.TextCurve = obj.data
            # 初期値を入れておく
            data.body = ""
            # 中央寄せにする
            data.align_x = "CENTER"
            data.align_y = "CENTER"
            append(obj)
        return objects

    @staticmethod
    def calc_grid_location(margin_x: float, margin_y: float, grid_x: int, grid_y: int):
        """マージンとグリッドの番地から座標を求める"""
        x = 0 - margin_x * grid_x
        y = 0 - margin_y * grid_y
        location = [x, y, 0.0]
        return location

    @staticmethod
    def calc_bound_box_center_location(bound_box):
        """bound_boxの中心座標を求める"""
        count = len(bound_box)
        temp = [0, 0, 0]
        for x, y, z in bound_box:
            temp[0] += x
            temp[1] += y
            temp[2] += z
        return [v / count for v in temp]

    @staticmethod
    def calc_punctuation_offset(bound_box_center: list):
        """句読点の位置オフセットを求める"""
        offset = [v * -2 for v in bound_box_center]
        return offset

    def create_text_container(self, props=None, name: str = "tatetext", count: int = 1):
        """テキストコンテナを作る"""
        bpy.ops.object.text_add(align="CURSOR", scale=(1, 1, 1))
        text_container: bpy.types.Object = bpy.context.active_object
        text_container.name = name
        props = self.init_props()

        text_container.id_data["tategaki"] = props

        used = self.apply()
        for ob in used:
            ob.parent = text_container

        bpy.context.view_layer.objects.active = text_container
        text_container.select_set(True)
        return text_container

    def apply_font_settings(
        self,
        text_object: bpy.types.Object,
        grid_addres: list[int, int],
        character: str,
        props=None,
    ):
        """テキストオブジェクトに設定を反映する"""
        data: bpy.types.TextCurve = text_object.data
        if props is None:
            props = self.props
        data.body = character
        data.font = bpy.data.fonts[props["font_name"]]
        data.resolution_u = props["resolution"]
        mx, my = props["margin"]
        gx, gy = grid_addres
        rotation = (0, 0, 0)
        location = self.calc_grid_location(mx, my, gx, gy)
        str_type = self.decision_special_character(character)
        if str_type == "upper_right":
            bound_box = text_object.bound_box
            center = self.calc_bound_box_center_location(bound_box)
            offset = self.calc_punctuation_offset(center)
            location = mathutils.Vector(location) + mathutils.Vector(offset)
        elif str_type == "rotation":
            rotation = (0, 0, 0 - pi / 2)
            text_object.rotation_euler = rotation
        text_object.location = location

    def add_object_pool(self, count):
        pool_len = len(self.pool)
        if pool_len < count:
            objects = self.create_text_objects(self.props["tag"], count)
            self.pool.extend(objects)

    def apply(self, props=None):
        if props is None:
            props = self.props
        body = props["body"]
        count = sum(len(c) for c in body)
        self.add_object_pool(count)
        text_objects = self.pool
        used = []
        used_append = used.append
        for line_number, line in enumerate(body):
            for c_number, character in enumerate(line):
                text_object = text_objects.pop()
                self.apply_font_settings(
                    text_object, [line_number, c_number], character, props
                )
                used_append(text_object)
        return used

    def init_props(self):
        tag: str = random_name(8)
        margin = [1.0, 1.0]
        resolution: int = 12
        scale = [1.0, 1.0, 1.0]
        font_name: str = bpy.data.fonts[0].name
        body = ["<012345>", "abcd"]
        props = dict(
            tag=tag,
            margin=margin,
            resolution=resolution,
            scale=scale,
            font_name=font_name,
            body=body,
        )
        self.props = props
        self.pool = []
        return props

    def get_props(self):
        return self.props.copy()

    def set_props(self, props: dict):
        """チェックしてから反映する"""
        self.props = props.copy()


class TATEGAKI_OT_AddText(bpy.types.Operator):
    """縦書きテキストオブジェクトを追加"""

    bl_idname = "tategaki.add_text"
    bl_label = translation("my operator")
    bl_description = "縦書きテキストオブジェクトを追加"
    bl_options = {"REGISTER", "UNDO"}

    text: bpy.props.StringProperty(name="text test", default="「あいうえお。」")

    # メニューを実行したときに呼ばれるメソッド
    def execute(self, context):
        # infoにメッセージを通知
        t_util = TategakiTextUtil()
        text_container = t_util.create_text_container()

        self.report({"INFO"}, f"execute {self.bl_idname},obj name is{text_container}")
        # 正常終了ステータスを返す
        return {"FINISHED"}


def tategaki_menu(self, context):
    self.layout.operator(TATEGAKI_OT_AddText.bl_idname, text="縦書きテキスト", icon="PLUGIN")


class TATEGAKI_PT_Panel(bpy.types.Panel):

    bl_label = "My panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TATEGAKI"

    # 本クラスの処理が実行可能かを判定する
    @classmethod
    def poll(cls, context):
        try:
            # うまく行かない
            # if context.active_object["tategaki"]:
            return True
        except AttributeError:
            return False

    def draw(self, context):
        layout = self.layout
        layout.label(text="object name")
        layout.label(text=context.active_object.name)
        mx, my = context.active_object["tategaki"]["margin"]
        layout.label(text=f"{mx},{my}")

        props = layout.operator("tategaki.my_operator")
        layout.prop(props, "text")


classses = [TATEGAKI_OT_AddText, TATEGAKI_PT_Panel]
tools = []


def register():
    for c in classses:
        bpy.utils.register_class(c)
    for t in tools:
        bpy.utils.register_tool(t)

    bpy.types.VIEW3D_MT_add.append(tategaki_menu)


def unregister():
    for c in classses:
        bpy.utils.unregister_class(c)
    for t in tools:
        bpy.utils.unregister_tool(t)

    bpy.types.VIEW3D_MT_add.remove(tategaki_menu)
