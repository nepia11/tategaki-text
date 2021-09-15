import bpy
from logging import getLogger

from bpy.types import TextBox
from .util import random_name, timer, mesh_transform_apply, convert_to_mesh
import mathutils
from math import pi
import os
import pprint
from typing import TypedDict, Final

logger = getLogger(__name__)

translation = bpy.app.translations.pgettext

# types
TATEGAKI: Final[str] = "tategaki"
TATEGAKI_CHR: Final[str] = "tategaki_chr"
Objects = list[bpy.types.Object]


def load_fonts():
    path = os.path.dirname(__file__)
    fonts_dir = os.path.join(path, "fonts")
    fonts_name = os.listdir(fonts_dir)
    for name in fonts_name:
        if name in bpy.data.fonts.keys():
            continue
        _path = os.path.join(fonts_dir, name)
        bpy.ops.font.open(relative_path=False, filepath=_path)
        bpy.data.fonts[name].use_fake_user = True


class TategakiState(TypedDict):
    """
    縦書きテキストの状態を保存するやつ
    """

    container: bpy.types.Object
    original: bpy.types.Object
    tag: str
    resolution: int
    body: list[str]
    lines_format: list
    line_spacing: float
    chr_spacing: float
    blank_size: float
    pool: Objects
    line_containers: dict[str, bpy.types.Object]
    auto_kerning: bool
    materials: list[bpy.types.Material]
    font: bpy.types.VectorFont
    font_bold: bpy.types.VectorFont
    font_italic: bpy.types.VectorFont
    font_bold_italic: bpy.types.VectorFont


class TategakiTextUtil:
    """縦書きテキスト用のutilとかをまとめておく"""

    """utilities"""
    # 特殊文字の判定
    @staticmethod
    def decision_special_character(single_str: str):
        """文字のタイプを判定して返す"""
        if single_str in "、。,.":
            return "upper_right"
        elif single_str in "[]()（）<>＜＞「」｛｝{}-ー―=＝~〜…":
            return "rotation"
        elif single_str in " 　":
            return "blank"
        else:
            return "normal"

    @staticmethod
    def insertion_newline_code(strings: str):
        """文字列に改行コードを挿入 使わん"""
        inserted = [moji + "\n" for moji in strings]
        return inserted

    @staticmethod
    @timer
    def create_text_objects(name: str, count: int = 1):
        """任意個のテキストオブジェクトを名前をつけて生成、テキストオブジェクトのリストを返す"""
        collection = bpy.data.collections.get("tategaki_pool")
        if collection is None:
            collection = bpy.data.collections.new("tategaki_pool")

        data_list = [bpy.data.curves.new(f"{name}.{i}", "FONT") for i in range(count)]
        objects: Objects = [bpy.data.objects.new(data.name, data) for data in data_list]

        for obj in objects:
            data: bpy.types.TextCurve = obj.data
            data.body = ""
            data.align_y = "CENTER"
            data.align_x = "CENTER"
            collection.objects.link(obj)

        if bpy.context.scene.collection.children.get(collection.name) is None:
            bpy.context.scene.collection.children.link(collection)

        return objects

    @staticmethod
    def calc_grid_location(
        line_spacing: float, chr_spacing: float, grid_x: int, grid_y: int
    ):
        """マージンとグリッドの番地から座標を求める"""
        x = 0 - line_spacing * grid_x
        y = 0 - chr_spacing * grid_y
        location = [x, y, 0.0]
        return location

    @staticmethod
    def calc_bound_box_center_location(bound_box):
        """bound_boxの中心座標を求める"""
        count = len(bound_box)
        center_xyz = [sum(v) / count for v in zip(*bound_box)]
        return mathutils.Vector(center_xyz)

    @staticmethod
    def calc_bound_box_width(bound_box):
        width_xyz = [max(v) - min(v) for v in zip(*bound_box)]
        return mathutils.Vector(width_xyz)

    @staticmethod
    def calc_bound_box_height(bound_box):
        xyz = [list(v) for v in zip(*bound_box)]
        max_min = (max(xyz[1]), min(xyz[1]))
        return max_min

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

    @staticmethod
    @timer
    def get_empty():
        collection = bpy.data.collections.get("tategaki_pool")
        if collection is None:
            collection = bpy.data.collections.new("tategaki_pool")
        empty = bpy.data.objects.new("empty", None)
        collection.objects.link(empty)
        return empty

    """オブジェクト操作"""

    def apply_font_settings(
        self,
        text_object: bpy.types.Object,
        grid_addres: list[int],
        character: str,
        format_props,
        state: TategakiState = None,
    ):
        """テキストオブジェクトに設定を反映する"""
        data: bpy.types.TextCurve = text_object.data
        if state is None:
            state = self.state
        # マテリアル割当
        for mat in state["materials"]:
            text_object.data.materials.append(mat)
        # 文字割当
        data.body = character
        # フォント設定
        data.font = state["font"]
        data.font_bold = state["font_bold"]
        data.font_italic = state["font_italic"]
        data.font_bold_italic = state["font_bold_italic"]

        # 解像度設定
        data.resolution_u = state["resolution"]
        # フォーマット設定
        self.prop_to_format(format_props, data.body_format[0])
        mx, my = state["line_spacing"], state["chr_spacing"]
        gx, gy = grid_addres
        rotation = (0.0, 0.0, 0.0)
        location = self.calc_grid_location(mx, my, gx, gy)
        str_type = self.decision_special_character(character)
        if str_type == "upper_right":
            # bound_boxの更新が遅延するためupdateする
            bpy.context.view_layer.update()
            # logger.debug(character)
            bound_box = text_object.bound_box
            center = self.calc_bound_box_center_location(bound_box)
            offset = self.calc_punctuation_offset(center)
            # logger.debug(f"offset:{offset},location{location}")
            location = mathutils.Vector(location) + mathutils.Vector(offset)
            # logger.debug(f"modified location:{location}")
        elif str_type == "rotation":
            rotation = (0.0, 0.0, 0.0 - pi / 2)
            # 回転設定
            text_object.rotation_euler = rotation
        # 座標設定
        text_object.location = location

    def add_object_pool(self, count):
        pool_len = len(self.state["pool"])
        if pool_len < count:
            objects = self.create_text_objects(self.state["tag"], count)
            for obj in objects:
                obj.parent = self.state["container"]
            self.state["pool"].extend(objects)

    def get_pool_object(self):
        if not len(self.state["pool"]) == 0:
            return self.state["pool"].pop()
        else:
            self.add_object_pool(10)

    def apply_constant_kerning(self, text_line: Objects):
        chr_spacing = self.state["chr_spacing"]
        for chr_num, text_object in enumerate(text_line):
            data: bpy.types.TextCurve = text_object.data
            character = data.body
            location = self.calc_grid_location(0, chr_spacing, 0, chr_num)
            str_type = self.decision_special_character(character)
            if str_type == "upper_right":
                # bound_boxの更新が遅延するためupdateする
                bpy.context.view_layer.update()
                bound_box = text_object.bound_box
                center = self.calc_bound_box_center_location(bound_box)
                offset = self.calc_punctuation_offset(center)
                location = mathutils.Vector(location) + mathutils.Vector(offset)
            # 座標設定
            text_object.location = location

    @timer
    def apply_auto_kerning(self, text_line: Objects):
        """縦書き文字のカーニングをする"""
        MAX, MIN = 0, 1
        margin = self.state["chr_spacing"]
        forward_object = None
        forward_props = {
            "bound_box_height": [0, 0],
            "bound_bottom": 0,
            "global_bound_bottom": 0,
            "location_y": 0,
        }

        for i, text_object in enumerate(text_line):
            # text_object: bpy.types.Object
            current_str_type = self.decision_special_character(text_object.data.body)

            if current_str_type == "rotation":

                _selected = list(bpy.context.view_layer.objects.selected)
                for _obj in _selected:
                    _obj.select_set(False)

                text_object.select_set(True)
                bpy.context.view_layer.objects.active = text_object

                # text curveからメッシュへ変換してコピー
                _converted_object = convert_to_mesh(text_object)

                _temp_name = _converted_object.name
                bpy.context.view_layer.update()

                mesh_transform_apply(
                    _converted_object, location=False, rotation=True, world=False
                )
                bpy.context.view_layer.update()

                local_current_bound_box_height = self.calc_bound_box_height(
                    bpy.data.objects[_temp_name].bound_box
                )
                local_current_bound_top = local_current_bound_box_height[MAX]

                bpy.data.objects.remove(bpy.data.objects[_temp_name])

            elif current_str_type == "blank":
                local_current_bound_box_height = self.calc_bound_box_height(
                    text_object.bound_box
                )
                local_current_bound_top = self.state["blank_size"]
            else:
                local_current_bound_box_height = self.calc_bound_box_height(
                    text_object.bound_box
                )
                local_current_bound_top = local_current_bound_box_height[MAX]
            # 今のオブジェクトのy座標（グローバル） マージンも反映する
            if i == 0:
                current_location_y = (
                    forward_props["global_bound_bottom"] - local_current_bound_top
                )
            else:
                current_location_y = (
                    forward_props["global_bound_bottom"]
                    - local_current_bound_top
                    - margin
                )
            text_object.location[1] = current_location_y
            forward_object = text_object
            current_bound_bottom = local_current_bound_box_height[MIN]
            forward_props = {
                "bound_box_height": local_current_bound_box_height,
                "bound_bottom": current_bound_bottom,
                "global_bound_bottom": current_bound_bottom + current_location_y,
                "location_y": current_location_y,
            }

    @timer
    def apply_lines(self, state: TategakiState, line, line_format, line_number: int):
        """行単位での文字設定などをする"""
        if state is None:
            state = self.state
        container_name = state["container"].name
        used: Objects = []
        used_append = used.append
        line_containers = self.state["line_containers"]
        # line_containersに在庫があったらそれを使う
        line_container = line_containers.get(str(line_number))
        # 在庫がなかったら生成してに追加する
        if line_container is None:
            line_container = self.get_empty()
            line_containers[str(line_number)] = line_container
        mx, my = state["line_spacing"], state["chr_spacing"]
        line_container.location = self.calc_grid_location(mx, my, line_number, 0)
        line_container.parent = state["container"]
        line_container.empty_display_size = 0.5
        line_container.hide_viewport = True
        for c_number, character_and_fromat in enumerate(zip(line, line_format)):
            character, body_format = character_and_fromat
            text_object = self.get_pool_object()
            # logger.debug(body_format)
            self.apply_font_settings(
                text_object, [0, c_number], character, body_format, state
            )
            name = f"{container_name}.{line_number}.{c_number}.{character}"
            text_object.name = name
            text_object.parent = line_container
            used_append(text_object)

        bpy.context.view_layer.update()

        if state["auto_kerning"] is True:
            self.apply_auto_kerning(text_line=used)
        return used

    def update_lines_spacing(self):
        line_spacing = self.state["line_spacing"]
        lines = self.state["line_containers"]
        for key, obj in lines.items():
            line_number = key
            loc = self.calc_grid_location(0, line_spacing, 0, line_number)
            obj.location = loc

    def update_chr_spacing(self):
        auto_kerning = self.state["auto_kerning"]
        chr_spacing = self.state["chr_spacing"]
        line_containers = self.state["line_containers"]
        lci = line_containers.items()
        if auto_kerning:
            for _num, line_container in lci:
                text_line = list(line_container.children)
                self.apply_auto_kerning(text_line)
        else:
            for _num, line_container in lci:
                text_line = list(line_container.children)
                self.apply_constant_kerning(text_line)

    def apply(self, state=None):
        if state is None:
            state = self.state
        body = state["body"]
        count = sum(len(c) for c in body)
        self.add_object_pool(count)
        used = []
        for line_number, z in enumerate(zip(body, state["lines_format"])):
            line, line_format = z
            _used = self.apply_lines(state, line, line_format, line_number)
            used.extend(_used)
        return used

    @timer
    def convert_text_object(self, text_object: bpy.types.Object):
        """テキストオブジェクトから縦書きテキストに変換する"""
        container = self.get_empty()
        container.location = bpy.context.scene.cursor.location
        container.name = f"{text_object.name}.tategaki"
        state = self.init_state(container=container, original=text_object)
        body, format_props = self.text_slice(text_object)
        state["body"] = body
        state["lines_format"] = format_props
        state["auto_kerning"] = True
        self.set_state(state)
        used = self.apply()
        bpy.ops.outliner.orphans_purge(
            do_local_ids=True, do_linked_ids=True, do_recursive=False
        )
        self.save_state()
        return container

    """プロパティ操作"""

    def init_state(
        self, container: bpy.types.Object = None, original: bpy.types.Object = None
    ):
        body = ["<012345>", "abcd"]
        if original is not None:
            data: bpy.types.TextCurve = original.data
            body = data.body.splitlines()

        font = data.font
        font_bold = data.font_bold
        font_italic = data.font_italic
        font_bold_italic = data.font_bold_italic

        materials = list(data.materials)

        state = TategakiState(
            container=container,
            original=original,
            tag=random_name(8),
            resolution=12,
            body=body,
            lines_format=[],
            line_spacing=1.0,
            chr_spacing=0.1,
            blank_size=0.5,
            pool=[],
            line_containers=dict(),
            auto_kerning=False,
            materials=materials,
            font=font,
            font_bold=font_bold,
            font_italic=font_italic,
            font_bold_italic=font_bold_italic,
        )

        self.state = state
        return state

    def get_state(self):
        return self.state.copy()

    def set_state(self, state: TategakiState):
        self.state = TategakiState(**state)

    def save_state(self):
        """オブジェクトにstateを保存する"""
        state_dict = self.state.copy()
        container = self.state["container"]
        if TATEGAKI in container.keys():
            container[TATEGAKI].update(state_dict)
        else:
            container[TATEGAKI] = state_dict

    def load_object_state(self, obj: bpy.types.Object):
        state = obj[TATEGAKI].to_dict()
        self.set_state(state)
        return self.state

    def export_state(self, state):
        if state is None:
            state = self.state
        export = bpy.data.texts.new("export")
        text = pprint.pformat(
            self.state,
        )
        export.write(text)

    def update(self):
        state = self.state
        body = state["body"]
        # count = sum(len(c) for c in body)
        # self.add_object_pool(count)
        used = []
        for line_number, z in enumerate(zip(body, state["lines_format"])):
            line, line_format = z
            _used = self.apply_lines(state, line, line_format, line_number)
            used.extend(_used)
        return used


class TATEGAKI_OT_RemoveChildren(bpy.types.Operator):
    bl_idname = "tategaki.remove_children"
    bl_label = "remove children"
    bl_options = {"REGISTER", "UNDO", "MACRO"}

    def execute(self, context):
        children = context.active_object.children
        logger.debug(children)
        _context = bpy.context.copy()
        _context["selected_objects"] = list(children)
        bpy.ops.object.delete(context)
        return {"FINISHED"}


class TATEGAKI_OT_AddText(bpy.types.Operator):
    """縦書きテキストオブジェクトを追加"""

    bl_idname = "tategaki.add_text"
    bl_label = "add tategaki text"
    bl_description = "アクティブなテキストオブジェクトから縦書きテキストオブジェクトを生成"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if context.active_object.type == "FONT":
            return True
        else:
            return False

    # メニューを実行したときに呼ばれるメソッド
    def execute(self, context):
        t_util = TategakiTextUtil()
        text_object = context.active_object
        container = t_util.convert_text_object(text_object)
        bpy.ops.object.select_all(action="DESELECT")
        container.select_set(True)
        context.view_layer.objects.active = container
        # infoにメッセージを通知
        self.report({"INFO"}, f"execute {self.bl_idname}")
        # 正常終了ステータスを返す
        return {"FINISHED"}


class TATEGAKI_OT_UpdateObject(bpy.types.Operator):
    """縦書きテキストオブジェクトを更新する"""

    bl_idname = "tategaki.update_object"
    bl_label = "update tategaki object"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    auto_kerning: bpy.props.BoolProperty(
        name="auto kerning",
        description="自動的に文字詰めをする",
        default=False,
    )

    chr_spacing: bpy.props.FloatProperty(
        name="character spacing",
        description="文字間隔",
        default=0.5,
    )
    line_spacing: bpy.props.FloatProperty(
        name="line spacing",
        description="行間隔",
        default=1,
    )

    @classmethod
    def poll(cls, context):
        if TATEGAKI in context.active_object.keys():
            return True
        else:
            return False

    is_running = False

    def modal(self, context, event):
        # エリアを再描画
        if context.area:
            context.area.tag_redraw()
        if event.type == "TIMER":
            try:
                pass
            except (KeyError):
                # モーダルモードを終了
                logger.debug("key error")
                return {"CANCELLED"}

        return {"PASS_THROUGH"}

    def invoke(self, context, event):

        if context.area.type == "VIEW_3D":
            if not self.is_running:
                # モーダルモードを開始
                self.is_running = True
                return {"RUNNING_MODAL"}
            else:
                # モーダルモードを終了
                self.__handle_remove(context)
                return {"FINISHED"}
        else:
            return {"FINISHED"}


def tategaki_menu(self, context):
    self.layout.operator(TATEGAKI_OT_AddText.bl_idname, text="縦書きテキスト", icon="PLUGIN")


class TATEGAKI_PT_Panel(bpy.types.Panel):

    bl_label = "Tategaki Tool"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"

    line_spacing = bpy.props.FloatProperty()

    # 本クラスの処理が実行可能かを判定する
    @classmethod
    def poll(cls, context):
        try:
            # うまく行かない
            # if context.active_object[TATEGAKI]:
            return True
        except AttributeError:
            return False

    def draw(self, context):
        layout = self.layout
        layout.label(text="object name", icon="DOT")
        layout.label(text=context.active_object.name)
        state: TategakiState = context.active_object[TATEGAKI]
        line_spacing, chr_spacing = state["line_spacing"], state["chr_spacing"]
        layout.label(text=f"line_spacing:  {line_spacing}")
        layout.label(text=f"chr_spacing:  {chr_spacing}")
        update_object = layout.operator("tategaki.update_object")
        layout.prop(update_object, "auto_kerning")
        layout.prop(update_object, "chr_spacing")
        layout.prop(update_object, "line_spacing")


classses = [TATEGAKI_OT_AddText, TATEGAKI_PT_Panel, TATEGAKI_OT_UpdateObject]
tools: list = []


def register():
    for c in classses:
        bpy.utils.register_class(c)
    for t in tools:
        bpy.utils.register_tool(t)

    bpy.types.VIEW3D_MT_add.append(tategaki_menu)
    bpy.types.Scene.tategaki_margin = bpy.props.FloatVectorProperty(
        name="margin x y blank",
        size=3,
        default=(1.0, 0.1, 0.5),
        subtype="LAYER",
    )


def unregister():
    for c in classses:
        bpy.utils.unregister_class(c)
    for t in tools:
        bpy.utils.unregister_tool(t)

    bpy.types.VIEW3D_MT_add.remove(tategaki_menu)
    del bpy.types.Scene.tategaki_margin
