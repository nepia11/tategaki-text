# コピペする用　__init__への登録は解除しといたほうが良い
import bpy
from logging import getLogger
from .util import random_name
import mathutils
from math import pi
import os


logger = getLogger(__name__)

translation = bpy.app.translations.pgettext


def load_fonts():
    path = os.path.dirname(__file__)
    fonts_dir = os.path.join(path, "fonts")
    fonts_name = os.listdir(fonts_dir)
    for name in fonts_name:
        if not bpy.data.fonts.find("name") == -1:
            continue
        _path = os.path.join(fonts_dir, name)
        bpy.ops.font.open(relative_path=False, filepath=_path)
        bpy.data.fonts[name].use_fake_user = True


class TategakiTextUtil:
    """縦書きテキスト用のutilとかをまとめておく"""

    """utilities"""
    # 特殊文字の判定
    @staticmethod
    def decision_special_character(single_str: str):
        """文字のタイプを判定して返す"""
        if single_str in "、。,.":
            return "upper_right"
        elif single_str in "[]()<>＜＞「」｛｝{}-ー―=＝~〜…":
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
        bound_box.update()
        count = len(bound_box)
        temp = [0, 0, 0]
        for x, y, z in bound_box:
            logger.debug(f"{x,y,z}")
            temp[0] += x
            temp[1] += y
            temp[2] += z
        result = [v / count for v in temp]
        logger.debug(f"center:{result}")
        return result

    @staticmethod
    def calc_punctuation_offset(bound_box_center: list):
        """句読点の位置オフセットを求める"""
        offset = [v * -2 for v in bound_box_center]
        return offset

    @staticmethod
    def textformat_to_prop(textfromat: bpy.types.TextCharacterFormat):
        """フォーマットからプロパティを取り出す"""
        prop = dict(
            material_index=textfromat.material_index,
            use_bold=textfromat.use_bold,
            use_italic=textfromat.use_italic,
            use_small_caps=textfromat.use_small_caps,
        )
        return prop

    @staticmethod
    def prop_to_format(format_props, textformat: bpy.types.TextCharacterFormat):
        textformat.use_bold = format_props["use_bold"]
        textformat.use_italic = format_props["use_italic"]
        textformat.use_small_caps = format_props["use_small_caps"]
        textformat.material_index = format_props["material_index"]
        pass

    def text_slice(self, text_object: bpy.types.Object):
        data: bpy.types.TextCurve = text_object.data
        body = data.body
        body_format = data.body_format
        lines = body.splitlines()
        index = 0
        lines_format = []
        for line in lines:
            line_len = len(line)
            index2 = index + line_len
            line_format = body_format[index:index2]
            temp = [self.textformat_to_prop(v) for v in line_format]
            lines_format.append(temp)
            index += line_len + 1
        return lines, lines_format

    """オブジェクト操作"""

    def apply_font_settings(
        self,
        text_object: bpy.types.Object,
        grid_addres: list[int, int],
        character: str,
        format_props,
        props=None,
    ):
        """テキストオブジェクトに設定を反映する"""
        data: bpy.types.TextCurve = text_object.data
        if props is None:
            props = self.props
        # マテリアル割当
        for mat in props["original"].data.materials:
            text_object.data.materials.append(mat)
        # 文字割当
        data.body = character
        # フォント設定
        # data.font = bpy.data.fonts[props["font_name"]]
        data.font = props["original"].data.font
        data.font_bold = props["original"].data.font_bold
        data.font_italic = props["original"].data.font_italic
        data.font_bold_italic = props["original"].data.font_bold_italic

        # 解像度設定
        data.resolution_u = props["resolution"]
        # フォーマット設定
        self.prop_to_format(format_props, data.body_format[0])
        mx, my = props["margin"]
        gx, gy = grid_addres
        rotation = (0, 0, 0)
        location = self.calc_grid_location(mx, my, gx, gy)
        str_type = self.decision_special_character(character)
        if str_type == "upper_right":
            # bound_boxの更新が遅延するためupdateする
            bpy.context.view_layer.update()
            logger.debug(character)
            bound_box = text_object.bound_box
            center = self.calc_bound_box_center_location(bound_box)
            offset = self.calc_punctuation_offset(center)
            logger.debug(f"offset:{offset},location{location}")
            location = mathutils.Vector(location) + mathutils.Vector(offset)
            logger.debug(f"modified location:{location}")
        elif str_type == "rotation":
            rotation = (0, 0, 0 - pi / 2)
            # 回転設定
            text_object.rotation_euler = rotation
        # 座標設定
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
        for line_number, z in enumerate(zip(body, props["lines_format"])):
            # line, line_format = z
            logger.debug(list(z))
            for c_number, character_and_fromat in enumerate(zip(z[0], z[1])):
                logger.debug(list(character_and_fromat))
                character, body_format = character_and_fromat
                text_object = text_objects.pop()
                logger.debug(body_format)
                self.apply_font_settings(
                    text_object, [line_number, c_number], character, body_format, props
                )
                used_append(text_object)
        return used

    def convert_text_object(self, text_object: bpy.types.Object):
        """テキストオブジェクトから縦書きテキストに変換する"""
        props = self.init_props()
        data: bpy.types.TextCurve = text_object.data
        body, format_props = self.text_slice(text_object)
        logger.debug(body)
        logger.debug(format_props)
        props["body"] = body
        props["lines_format"] = format_props
        props["font_name"] = data.font.name
        props["original"] = text_object
        print(props["lines_format"])
        self.set_props(props)
        used = self.apply()
        text_object.id_data["tategaki"] = props
        for child in used:
            logger.debug(child)
            child.parent = text_object

        bpy.ops.outliner.orphans_purge(
            do_local_ids=True, do_linked_ids=True, do_recursive=False
        )

    """プロパティ操作"""

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

    def text_to_props(self, text_object):
        pass


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
        # text_container = t_util.create_text_container()
        text_object = context.active_object
        t_util.convert_text_object(text_object)

        self.report({"INFO"}, f"execute {self.bl_idname}")
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
