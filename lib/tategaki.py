import math
import bpy
from bpy.types import (
    Context,
    Curve,
    Material,
    TextCurve,
    Object,
    VectorFont,
    TextCharacterFormat,
    DecimateModifier,
    EdgeSplitModifier,
)
import mathutils
from logging import getLogger
from .util import (
    random_name,
    timer,
    mesh_transform_apply,
    convert_to_mesh,
    mesh_to_gpencil,
)
import os
import pprint
from typing import TypedDict, Final
import re

# setup
logger = getLogger(__name__)
translation = bpy.app.translations.pgettext

# utils
# https://dlrecord.hatenablog.com/entry/2020/07/30/230234
def atoi(text: str):
    return int(text) if text.isdigit() else text


def natural_keys(text: str):
    return [atoi(c) for c in re.split(r"(\d+)", text)]


def object_sort_function(obj: Object):
    """ソートの評価関数オブジェクトの名前でソートする 数値もいい感じに処理する"""
    return natural_keys(obj.name)


def load_fonts():
    """日本語フォントを同梱したときに自動的に読み込もうと思っていたけど別にいらないかなと思った"""
    path = os.path.dirname(__file__)
    fonts_dir = os.path.join(path, "fonts")
    fonts_name = os.listdir(fonts_dir)
    for name in fonts_name:
        if name in bpy.data.fonts.keys():
            continue
        _path = os.path.join(fonts_dir, name)
        bpy.ops.font.open(relative_path=False, filepath=_path)
        bpy.data.fonts[name].use_fake_user = True


# /utils

# types
TATEGAKI: Final[str] = "tategaki"
TATEGAKI_CHR: Final[str] = "tategaki_chr"
Objects = list[Object]


class BoundBoxHeight(TypedDict):
    max: float
    min: float


class CharacterProp(TypedDict):
    """1文字単位のプロパティ"""

    character: str
    material_index: int
    use_bold: bool
    use_italic: bool
    use_small_caps: bool


class TategakiState(TypedDict):
    """
    縦書きテキストの状態を保存するやつ
    """

    container: Object  # 入れ物にするエンプティオブジェクト
    original: Object  # もとのテキストオブジェクト
    name: str  # コレクションの名前
    tag: str  # 何かしらに使う識別子
    resolution: int  # テキストカーブの細分化数
    body: list[str]  # 改行で分割された文字列のリスト
    text_props: list
    body_object_name_list: list[list[str]]
    limit_length: int  # 行文字数制限
    kerning_hints: dict[str, BoundBoxHeight]
    line_spacing: float  # 行間
    chr_spacing: float  # 字間
    blank_size: float  # 空白文字の大きさ
    line_containers: dict[str, str]  # 行ごとのコンテナ(エンプティ) keyがintのdictをid-propに格納できない
    auto_kerning: bool
    materials: list[bpy.types.Material]
    font: VectorFont
    font_bold: VectorFont
    font_italic: VectorFont
    font_bold_italic: VectorFont


# /types


class TategakiTextUtil:
    """縦書きテキスト用のutilとかをまとめておく"""

    """utilities"""

    @staticmethod
    def decision_special_character(single_str: str):
        """特殊文字の判定　文字のタイプを判定して返す"""
        if single_str in "、。,.":
            return "upper_right"
        elif single_str in "[]()（）<>＜＞「」【】『』〈〉《》«»［］｛｝{}-ー―=＝~〜…":
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
    def unique_strings(string: str):
        """文字列の重複を排除する"""
        return "".join(set(string))

    @staticmethod
    def get_chr_data(font_name: str, chr: str) -> TextCurve:
        """font.chr TextCurveを取得"""
        name = f"{font_name}.{chr}"
        data = bpy.data.curves.get(name)
        if data is None:
            data = bpy.data.curves.new(name, "FONT")
            data.body = chr
            data.align_y = "CENTER"
            data.align_x = "CENTER"
            data.font = bpy.data.fonts[font_name]
            material = bpy.data.materials.get("Material")
            if material is None:
                material = bpy.data.materials.new("Material")
            data.materials.append(material)
        return data

    @staticmethod
    def get_collection(name: str):
        """collectionを取得（生成）"""
        collection = bpy.data.collections.get(name)
        if collection is None:
            collection = bpy.data.collections.new(name)
        return collection

    @staticmethod
    def calc_grid_location(
        line_spacing: float, chr_spacing: float, line_number: int, chr_number: int
    ):
        """マージンと行列番号(?)から座標を求める"""
        x = 0 - line_spacing * line_number
        y = 0 - chr_spacing * chr_number
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
        Y = 1
        xyz = [list(v) for v in zip(*bound_box)]  # [x,y,z]
        result = BoundBoxHeight(max=max(xyz[Y]), min=min(xyz[Y]))
        return result

    @staticmethod
    def calc_punctuation_offset(bound_box_center: list):
        """句読点の位置オフセットを求める"""
        offset = [v * -2 for v in bound_box_center]
        return offset

    @staticmethod
    def gen_character_prop(character: str, textfromat: TextCharacterFormat):
        """フォーマットからプロパティを取り出す"""
        prop = CharacterProp(
            character=character,
            material_index=textfromat.material_index,
            use_bold=textfromat.use_bold,
            use_italic=textfromat.use_italic,
            use_small_caps=textfromat.use_small_caps,
        )
        return prop

    def text_to_props(self, text_object: Object):
        """テキストから文字単位のpropのリストを生成して返す"""
        data: TextCurve = text_object.data
        body = data.body
        body_format = data.body_format
        lines = body.splitlines()
        index = 0
        lines_chr_props: list[list[CharacterProp]] = []
        for line in lines:
            line_len = len(line)
            index2 = index + line_len
            line_format = body_format[index:index2]
            temp = [self.gen_character_prop(s, f) for s, f in zip(line, line_format)]
            lines_chr_props.append(temp)
            index += line_len + 1
        return lines_chr_props

    def modify_text_props(self, lines_chr_props: list, limit_length: int):
        """行文字数制限を適応したpropsを生成"""
        line: list[CharacterProp]
        modified_lines_chr_props: list[list[CharacterProp]] = []
        for line in lines_chr_props:
            length = len(line)
            if length > limit_length:
                splitted = [
                    line[idx : idx + limit_length]
                    for idx in range(0, length, limit_length)
                ]
                modified_lines_chr_props.extend(splitted)
            else:
                modified_lines_chr_props.append(line)
        return modified_lines_chr_props

    def character_prop_to_object(self, chr_prop: CharacterProp):
        """CharacterPropから文字オブジェクトを生成する"""
        font_name = ""
        character = chr_prop["character"]
        materials = self.state["materials"]
        material = materials[chr_prop["material_index"]]
        # 使うフォントを決定する
        if chr_prop["use_bold"] and chr_prop["use_italic"]:
            font_name = self.state["font_bold_italic"].name
        elif chr_prop["use_bold"]:
            font_name = self.state["font_bold"].name
        elif chr_prop["use_italic"]:
            font_name = self.state["font_italic"].name
        else:
            font_name = self.state["font"].name

        chr_data = self.get_chr_data(font_name, character)
        chr_data.resolution_u = self.state["resolution"]
        obj = bpy.data.objects.new(chr_data.name, chr_data)
        obj.material_slots[0].link = "OBJECT"
        obj.material_slots[0].material = material
        return obj

    @staticmethod
    def get_empty(collection_name: str = "tategaki_pool"):
        collection = bpy.data.collections.get(collection_name)
        if collection is None:
            collection = bpy.data.collections.new(collection_name)
        empty: Object = bpy.data.objects.new("empty", None)
        collection.objects.link(empty)
        return empty

    @staticmethod
    def get_empty_mesh_object(collection_name: str = "tategaki_pool"):
        collection = bpy.data.collections.get(collection_name)
        if collection is None:
            collection = bpy.data.collections.new(collection_name)
        name = random_name(8)
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj

    @staticmethod
    def get_empty_curve_object(collection_name: str = "tategaki_pool"):
        collection = bpy.data.collections.get(collection_name)
        if collection is None:
            collection = bpy.data.collections.new(collection_name)
        name = random_name(8)
        data = bpy.data.curves.new(name, "CURVE")
        obj = bpy.data.objects.new(name, data)
        collection.objects.link(obj)
        return obj

    @timer
    def calc_kerning_hint(self, text_object: Object):
        """カーニング用の情報を計算する"""
        str_type = self.decision_special_character(text_object.data.body)
        if str_type == "rotation":
            # text curveからメッシュへ変換してコピー
            _converted_object = convert_to_mesh(text_object, parent_inheritance=False)
            _temp_name = _converted_object.name
            bpy.context.view_layer.update()
            mesh_transform_apply(
                _converted_object, location=False, rotation=True, world=False
            )
            bpy.context.view_layer.update()
            bound_box_height = self.calc_bound_box_height(
                bpy.data.objects[_temp_name].bound_box
            )
            bpy.data.objects.remove(bpy.data.objects[_temp_name])
        elif str_type == "blank":
            bound_box_height = self.calc_bound_box_height(text_object.bound_box)
        else:
            bound_box_height = self.calc_bound_box_height(text_object.bound_box)
        return bound_box_height

    """オブジェクト操作"""

    def set_character_transform(
        self,
        text_object: Object,
        grid_addres: list[int],
        character: str,
        state: TategakiState = None,
    ):
        if state is None:
            state = self.state
        """stateに基づいてテキストオブジェクトの位置回転を設定する"""
        # フォーマット設定
        mx, my = state["line_spacing"], state["chr_spacing"]
        gx, gy = grid_addres
        rotation = (0.0, 0.0, 0.0)
        location = self.calc_grid_location(mx, my, gx, gy)
        str_type = self.decision_special_character(character)
        if str_type == "upper_right":
            # bound_boxの更新が遅延するためupdateする
            bpy.context.view_layer.update()
            bound_box = text_object.bound_box
            center = self.calc_bound_box_center_location(bound_box)
            offset = self.calc_punctuation_offset(center)
            location = mathutils.Vector(location) + mathutils.Vector(offset)
        elif str_type == "rotation":
            rotation = (0.0, 0.0, math.radians(-90))
            # 回転設定
            text_object.rotation_euler = rotation
        # 座標設定
        text_object.location = location

    def apply_constant_kerning(self, text_line: Objects):
        chr_spacing = self.state["chr_spacing"]
        for chr_num, text_object in enumerate(text_line):
            data: TextCurve = text_object.data
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

    def apply_auto_kerning(self, text_line: Objects):
        """縦書き文字のカーニングをする"""
        margin = self.state["chr_spacing"]
        # 一つ前のオブジェクトの情報
        forward_global_bound_bottom = 0.0

        for i, text_object in enumerate(text_line):
            # text_object: Object
            # hintはfont.character形式で保存する
            hint = self.state["kerning_hints"].get(text_object.data.name)
            if hint is None:
                logger.debug(f"{text_object.data.name} hint is None")
                hint = self.calc_kerning_hint(text_object)
                self.state["kerning_hints"].update({text_object.data.name: hint})

            current_str_type = self.decision_special_character(text_object.data.body)

            if current_str_type == "rotation":
                local_current_bound_box_height = hint
                local_current_bound_top = local_current_bound_box_height["max"]
            elif current_str_type == "blank":
                local_current_bound_box_height = hint
                local_current_bound_top = self.state["blank_size"]
            else:
                local_current_bound_box_height = hint
                local_current_bound_top = local_current_bound_box_height["max"]
            # 今のオブジェクトのy座標（グローバル） マージンも反映する
            if i == 0:
                current_location_y = (
                    forward_global_bound_bottom - local_current_bound_top
                )
            else:
                current_location_y = (
                    forward_global_bound_bottom - local_current_bound_top - margin
                )

            text_object.location[1] = current_location_y
            current_bound_bottom = local_current_bound_box_height["min"]
            forward_global_bound_bottom = current_bound_bottom + current_location_y

    def get_line_container(self, index: int):
        state = self.state
        tag = state["tag"]
        collection_name = state["name"]
        container = state["container"]
        # 行コンテナを作って位置を設定
        line_container_name = f"{tag}.{index}"
        line_container = bpy.data.objects.get(line_container_name)
        if line_container is None:
            line_container = self.get_empty(collection_name)
            line_container.name = line_container_name

        line_container.location = self.calc_grid_location(
            state["line_spacing"], 0, index, 0
        )
        # 行コンテナを非表示にしておく
        line_container.empty_display_size = 0.5
        line_container.hide_viewport = True
        line_container.parent = container
        return line_container

    @timer
    def convert_text_object(self, text_object: Object):
        """テキストオブジェクトから縦書きテキストに変換する"""
        # コレクションの取得
        body = text_object.data.body
        # stateの初期化
        state = self.init_state(original=text_object)
        # テキストオブジェクトからプロパティを生成
        text_props = self.text_to_props(text_object)
        # 行文字数制限で改行する
        mod_text_props = self.modify_text_props(text_props, limit_length=20)
        state["body"] = body.splitlines()
        state["text_props"] = text_props
        state["auto_kerning"] = False
        state["name"] = f"{text_object.name}.{state['tag']}"
        state["limit_length"] = 20
        self.set_state(state)
        # apply
        # 改行済み文字propsがあるのでこれをよしなにする
        container = self.generate_tategaki_text_from_state(state)
        return container

    def generate_tategaki_text_from_state(self, state: TategakiState):
        body_object_name_list = []
        line_containers = {}
        chr_count = 0
        mod_text_props = self.modify_text_props(
            state["text_props"], state["limit_length"]
        )
        # コレクションの取得
        collection_name = state["name"]
        collection = self.get_collection(collection_name)
        collection_name = collection.name
        # テキストオブジェクトをペアレントするエンプティの作成
        container = self.get_empty(collection_name=collection_name)
        container.location = bpy.context.scene.cursor.location
        container.name = collection_name
        state["container"] = container
        tag = state["tag"]
        for i0, line in enumerate(mod_text_props):
            line_names: list[str] = []
            line_container = self.get_line_container(index=i0)
            line_container.parent = container
            line_containers.update({str(i0): line_container.name})
            for i1, chr_prop in enumerate(line):
                character = chr_prop["character"]
                obj = self.character_prop_to_object(chr_prop)
                self.set_character_transform(obj, [0, i1], character, state)
                name = f"{tag}.{chr_count}.{character}"
                obj.name = name
                obj.parent = line_container
                # コレクションにオブジェクトをリンクしないと表示されない
                collection.objects.link(obj)
                line_names.append(name)
                chr_count += 1
            body_object_name_list.append(line_names)
        state["body_object_name_list"] = body_object_name_list
        state["line_containers"] = line_containers
        self.update_kerning_hint(state)
        self.set_state(state)
        # シーンにリンク
        if bpy.context.scene.collection.children.get(collection.name) is None:
            bpy.context.scene.collection.children.link(collection)
        self.save_state()
        return container

    """プロパティ操作"""

    def init_state(self, container: Object = None, original: Object = None):
        body = ["<012345>", "abcd"]
        if original is not None:
            data: TextCurve = original.data
            body = data.body.splitlines()

        font = data.font
        font_bold = data.font_bold
        font_italic = data.font_italic
        font_bold_italic = data.font_bold_italic

        materials = list(data.materials)
        if materials == []:
            mat = bpy.data.materials.new("Empty_Mat")
            materials.append(mat)

        state = TategakiState(
            container=container,
            original=original,
            name=random_name(8),
            tag=random_name(8),
            resolution=2,
            body=body,
            text_props=[],
            limit_length=80,
            kerning_hints=dict(),
            body_object_name_list=[],
            line_spacing=1.0,
            chr_spacing=1.0,
            blank_size=0.5,
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

    def load_object_state(self, obj: Object):
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

    @timer
    def update_lines_spacing(self, state: TategakiState = None):
        """stateに合わせて行間を更新する"""
        if state is None:
            state = self.state
        line_spacing = self.state["line_spacing"]
        lines = self.state["line_containers"]
        calc_grid_location = self.calc_grid_location
        for key, name in lines.items():
            line_number = int(key)
            obj = bpy.data.objects.get(name)
            loc = calc_grid_location(line_spacing, 0, line_number, 0)
            obj.location = loc

    @timer
    def update_chr_spacing(self, state: TategakiState = None):
        """stateに合わせて字間を更新する"""
        if state is None:
            state = self.state
        auto_kerning = self.state["auto_kerning"]
        chr_spacing = self.state["chr_spacing"]
        apply_auto_kerning = self.apply_auto_kerning
        apply_constant_kerning = self.apply_constant_kerning
        line_containers = self.state["line_containers"]
        lci = line_containers.items()
        if auto_kerning:
            for _num, name in lci:
                line_container = bpy.data.objects.get(name)
                text_line = list(line_container.children)
                text_line.sort(key=object_sort_function)
                apply_auto_kerning(text_line)
        else:
            for _num, name in lci:
                line_container = bpy.data.objects.get(name)
                if line_container is None:
                    continue
                text_line = list(line_container.children)
                text_line.sort(key=object_sort_function)
                apply_constant_kerning(text_line)

    @timer
    def update_limit_length(self, state: TategakiState = None):
        if state is None:
            state = self.state
        # 参照しやすくする
        tag = state["tag"]
        limit_length = state["limit_length"]
        text_props = state["text_props"]
        line_containers = state["line_containers"]
        line_containers2 = {}
        collection = bpy.data.collections.get(state["name"])
        mod_text_props = self.modify_text_props(text_props, limit_length)
        chr_count = 0
        for i0, line in enumerate(mod_text_props):
            # 1行分のオブジェクトを取得
            names = [
                f"{tag}.{chr_count+i1}.{prop['character']}"
                for i1, prop in enumerate(line)
            ]
            objects = [bpy.data.objects.get(name) for name in names]
            chr_count += len(names)
            # line_containerを取得　なかったら作成
            line_container = self.get_line_container(index=i0)
            line_containers2.update({str(i0): line_container.name})

            for i1, obj in enumerate(objects):
                obj.parent = line_container
        state["line_containers"] = line_containers2
        # logger.debug(line_containers2)
        # self.set_state(state)

    @timer
    def update_kerning_hint(self, state: TategakiState = None):
        """stateに合わせてカーニングヒントを更新する"""
        if state is None:
            state = self.state
        calc_kerning_hint = self.calc_kerning_hint
        line_containers = state["line_containers"]
        lci = line_containers.items()
        kerning_hints = {}
        for _num, name in lci:
            line_container = bpy.data.objects.get(name)
            text_line = list(line_container.children)
            text_line.sort(key=object_sort_function)
            # 行ごとのヒント情報を計算
            line_hints = {obj.data.name: calc_kerning_hint(obj) for obj in text_line}
            kerning_hints.update(line_hints)
            # logger.debug(line_hints)
        # logger.debug(kerning_hints)
        state["kerning_hints"] = kerning_hints
        self.set_state(state)
        return kerning_hints

    @timer
    def freeze(self, context, resolution=2, freeze_type: str = "MESH"):
        """縦書きテキストをメッシュまたはカーブに変換する"""

        line_containers = self.state["line_containers"]
        lci = line_containers.items()
        objects: Objects = []

        # オブジェクトのリストを作成
        for _num, container_name in lci:
            line_container = bpy.data.objects.get(container_name)
            text_line: Objects = list(line_container.children)
            # childrenがNoneのときがあるので除外する
            if len(text_line) == 0:
                continue
            else:
                objects.extend(text_line)

        for obj in objects:
            data: TextCurve = obj.data
            data.resolution_u = resolution

        # debug
        # logger.debug(pprint.pformat(objects))
        body_len = sum([len(s) for s in self.state["body"]])
        objects_len = len(objects)
        logger.info(f"body len:{body_len}, objects len:{objects_len}")

        # freeze_typeに応じてカーブかメッシュに変換
        if freeze_type == "MESH":

            converted_objects = [convert_to_mesh(obj) for obj in objects]
            # 結合するときに都合がいいので空のメッシュオブジェクトを作る
            empty_object = self.get_empty_mesh_object(self.state["name"])

        elif freeze_type == "CURVE":

            materials = self.state["materials"]
            material_keys = [mat.name for mat in materials]

            for obj in objects:
                # コピーを作らないと重複文字がリンクデータなのでおかしくなる
                obj.data = obj.data.copy()

            bpy.ops.object.select_all(action="DESELECT")
            object_names = [obj.name for obj in objects]

            for obj in objects:
                obj.select_set(True)

            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.convert(target="CURVE")
            converted_objects = [bpy.data.objects.get(name) for name in object_names]

            # マテリアルをよしなにする
            for obj in converted_objects:
                # マテリアルインデックスの交換対応表を作る
                src_materials_keys = obj.material_slots.keys()
                mat_exchage_index = [
                    material_keys.index(keys) for keys in src_materials_keys
                ]

                # materialsを初期化
                obj.data.materials.clear()
                for mat in materials:
                    obj.data.materials.append(mat)

                # curveのマテリアルインデックスを対応表に応じて交換
                for spline in obj.data.splines:
                    src_index = spline.material_index
                    spline.material_index = mat_exchage_index[src_index]

            # 統合オブジェクトを作るときの位置調整用空カーブオブジェクトを作る
            empty_object = self.get_empty_curve_object(self.state["name"])

            for mat in materials:
                empty_object.data.materials.append(mat)

        else:
            logger.info(f"freeze_type='{freeze_type}' is invalid. 'MESH' or 'CURVE'")
            raise TypeError

        empty_object.parent = self.state["container"]
        empty_object.name = f"{self.state['name']}.freeze"
        joined_object_name = empty_object.name
        converted_objects.append(empty_object)

        # オーバーライドコンテキストを作る
        override = context.copy()
        override["selected_objects"] = converted_objects
        override["selected_editable_objects"] = converted_objects
        override["active_object"] = bpy.data.objects[joined_object_name]
        bpy.ops.object.join(override)

        location = self.state["container"].location
        joint_object = bpy.data.objects[joined_object_name]
        joint_object.location = location

        if freeze_type == "CURVE":
            _data: Curve = joint_object.data
            _data.fill_mode = "FRONT"
        return joint_object


######### Operators ###########


class TATEGAKI_OT_ConvertToTategakiText(bpy.types.Operator):
    """縦書きテキストオブジェクトを追加"""

    bl_idname = "tategaki.convert_text"
    bl_label = "Convert to vertical text"
    bl_description = "Create a vertical text object from the active text object."

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


class TATEGAKI_OT_Remove(bpy.types.Operator):
    """縦書きテキストオブジェクトを削除"""

    bl_idname = "tategaki.remove"
    bl_label = "Remove"
    bl_description = ""

    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if TATEGAKI in context.object.keys():
            return True
        else:
            return False

    # メニューを実行したときに呼ばれるメソッド
    def execute(self, context):
        # setup
        t_util = TategakiTextUtil()
        tategaki_obj = context.object
        state = t_util.load_object_state(tategaki_obj)

        # 削除するオブジェクトを取得する
        collection = bpy.data.collections.get(state["name"])
        deletion_objects = []

        if collection is None:
            pass
        else:
            deletion_objects = list(collection.all_objects)

        # removed = [o.name for o in deletion_objects]

        # 削除
        del_obj: Object
        for del_obj in deletion_objects:
            del_obj.parent = None
            bpy.data.objects.remove(del_obj)

        bpy.data.collections.remove(collection)

        # clean
        bpy.ops.outliner.orphans_purge(
            do_local_ids=True, do_linked_ids=True, do_recursive=True
        )

        # infoにメッセージを通知
        self.report({"INFO"}, f"execute {self.bl_idname}. removed tategaki object")
        # 正常終了ステータスを返す
        return {"FINISHED"}


class TATEGAKI_OT_Duplicate(bpy.types.Operator):
    """縦書きテキストオブジェクトを複製"""

    bl_idname = "tategaki.duplicate"
    bl_label = "Duplicate vertical text"
    bl_description = "Duplicate the active vertical text object"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if TATEGAKI in context.active_object.keys():
            return True
        else:
            return False

    # メニューを実行したときに呼ばれるメソッド
    def execute(self, context):
        # 初期化など
        t_util = TategakiTextUtil()
        obj = context.object
        state = t_util.load_object_state(obj)
        old_name = state["name"]
        old_tag = state["tag"]
        new_tag = random_name(8)
        orig_name = old_name.replace(f".{old_tag}", "")
        new_name = f"{orig_name}.{new_tag}"

        logger.debug(f"oname:{old_name},otag:{old_tag},nname:{new_name},ntag{new_tag}")

        # 新しいタグと名前をつける
        state["name"] = new_name
        state["tag"] = new_tag

        # 生成
        t_util.set_state(state)
        container = t_util.generate_tategaki_text_from_state(state)

        # 行間字間適応
        t_util.update_chr_spacing()
        t_util.update_lines_spacing()

        # 選択状態を操作
        bpy.ops.object.select_all(action="DESELECT")
        container.select_set(True)
        context.view_layer.objects.active = container

        # infoにメッセージを通知
        self.report({"INFO"}, f"execute {self.bl_idname}")
        # 正常終了ステータスを返す
        return {"FINISHED"}


class TATEGAKI_OT_UpdateChrSpacing(bpy.types.Operator):
    """縦書きテキストの文字間隔と自動カーニングオプションを更新する"""

    bl_idname = "tategaki.update_chr_spacing"
    bl_label = "update character spacing"
    bl_description = (
        "Update character spacing and auto-kerning options for vertical text"
    )
    bl_options = {"REGISTER", "UNDO"}

    auto_kerning: bpy.props.BoolProperty(
        name="auto kerning",
        description="Automatic character spacing.",
        default=False,
    )

    chr_spacing: bpy.props.FloatProperty(
        name="character spacing",
        description="character spacing",
        default=0.5,
    )

    @classmethod
    def poll(cls, context):
        if TATEGAKI in context.active_object.keys():
            return True
        else:
            return False

    def execute(self, context):
        obj = context.object
        t_util = TategakiTextUtil()
        state = t_util.load_object_state(obj)
        state["chr_spacing"] = self.chr_spacing
        state["auto_kerning"] = self.auto_kerning
        t_util.set_state(state)
        t_util.update_chr_spacing()
        t_util.save_state()  # 検証する

        return {"FINISHED"}

    def invoke(self, context: Context, event):
        if self.poll(context):
            wm = context.window_manager
            return wm.invoke_props_popup(self, event)
        else:
            self.report({"WARNING"}, "No active object, could not finish")
            return {"CANCELLED"}


class TATEGAKI_OT_UpdateLineSpacing(bpy.types.Operator):
    """縦書きテキストの行間を更新する"""

    bl_idname = "tategaki.update_line_spacing"
    bl_label = "update line spacing"
    bl_description = "Update line spacing for Vertical text."
    bl_options = {"REGISTER", "UNDO"}

    line_spacing: bpy.props.FloatProperty(
        name="line spacing",
        description="line spacing",
        default=1,
    )

    @classmethod
    def poll(cls, context):
        if TATEGAKI in context.active_object.keys():
            return True
        else:
            return False

    def execute(self, context):

        obj = context.object
        t_util = TategakiTextUtil()
        state = t_util.load_object_state(obj)
        state["line_spacing"] = self.line_spacing
        t_util.set_state(state)
        t_util.update_lines_spacing()
        t_util.save_state()  # 検証する

        return {"FINISHED"}

    def invoke(self, context: Context, event):
        if self.poll(context):
            wm = context.window_manager
            return wm.invoke_props_popup(self, event)
        else:
            self.report({"WARNING"}, "No active object, could not finish")
            return {"CANCELLED"}


class TATEGAKI_OT_UpdateLineCharacterLimit(bpy.types.Operator):
    """縦書きテキストの1行あたりの文字数制限を更新する"""

    bl_idname = "tategaki.update_line_character_limit"
    bl_label = "update line character limit"
    bl_description = "Update the character limit per line for vertical text."

    bl_options = {"REGISTER", "UNDO"}

    limit_length: bpy.props.IntProperty(
        name="line character limit",
        description="line character limit",
        default=20,
        min=1,
        soft_max=100,
    )

    @classmethod
    def poll(cls, context):
        if TATEGAKI in context.active_object.keys():
            return True
        else:
            return False

    def execute(self, context):
        obj = context.object
        t_util = TategakiTextUtil()
        state = t_util.load_object_state(obj)
        state["limit_length"] = self.limit_length
        t_util.set_state(state)
        t_util.update_limit_length()
        t_util.update_chr_spacing()
        t_util.save_state()

        return {"FINISHED"}

    def invoke(self, context: Context, event):
        if self.poll(context):
            wm = context.window_manager
            return wm.invoke_props_popup(self, event)
        else:
            self.report({"WARNING"}, "No active object, could not finish")
            return {"CANCELLED"}


class TATEGAKI_OT_Freeze(bpy.types.Operator):
    """縦書きテキストオブジェクトをメッシュ、カーブ、gpencilに変換する"""

    bl_idname = "tategaki.freeze"
    bl_label = "freeze"
    bl_description = "Convert vertical text objects to meshes, curves, and gpencils"
    bl_options = {"REGISTER", "UNDO"}

    keep_original: bpy.props.BoolProperty(name="keep_original", default=False)

    resolution: bpy.props.IntProperty(name="resolution", default=2)

    freeze_type: bpy.props.EnumProperty(
        name="freeze_type",
        default="MESH",
        items=[
            ("MESH", "MESH", ""),
            ("CURVE", "CURVE", ""),
            ("GPENCIL", "GPENCIL", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        try:
            if TATEGAKI in context.active_object.keys():
                return True
            else:
                return False
        except:
            return False

    def execute(self, context: bpy.types.Context):
        active_object: Object = context.active_object
        wm = context.window_manager
        wm.progress_begin(0, 5)

        if TATEGAKI in active_object.keys():

            t_util = TategakiTextUtil()
            t_util.load_object_state(active_object)
            location = active_object.location

            wm.progress_update(1)

            freeze_type = self.freeze_type
            if freeze_type == "GPENCIL":
                # gpencilに変換する時に色々最適化する
                obj = t_util.freeze(context, self.resolution, "MESH")
                obj_name = obj.name

                wm.progress_update(2)

                obj.modifiers.clear()

                decimate: DecimateModifier = obj.modifiers.new(
                    name="gp_pre_decimate", type="DECIMATE"
                )
                decimate.decimate_type = "DISSOLVE"
                decimate.angle_limit = math.radians(1)

                edge_split: EdgeSplitModifier = obj.modifiers.new(
                    name="gp_pre_edge_split", type="EDGE_SPLIT"
                )
                edge_split.use_edge_angle = False
                edge_split.use_edge_sharp = False

                _override = context.copy()
                _override["object"] = obj
                _override["active_object"] = obj

                for mod in obj.modifiers:
                    bpy.ops.object.modifier_apply(_override, modifier=mod.name)

                wm.progress_update(3)

                # mesh_to_gpencil実装
                gpencil_data = mesh_to_gpencil(obj.data)
                obj = bpy.data.objects.new(obj_name, gpencil_data)

                wm.progress_update(4)
            else:
                obj = t_util.freeze(context, self.resolution, freeze_type)
                wm.progress_update(4)

            obj.name = f"{t_util.state['name']}.freeze"
            obj.parent = None
            collection = t_util.get_collection(t_util.state["name"])

            # collectionにあったりなかったりするので分別
            if obj in list(collection.objects):
                collection.objects.unlink(obj)
            if obj in list(context.collection.objects):
                pass
            else:
                context.scene.collection.objects.link(obj)
            obj.location = location

            if self.keep_original is False:
                # コレクションの中身と自身を削除
                all_objects = list(collection.all_objects)

                for obj in all_objects:
                    bpy.data.objects.remove(obj)

                bpy.data.collections.remove(collection)
                bpy.ops.outliner.orphans_purge(
                    do_local_ids=True, do_linked_ids=True, do_recursive=True
                )

                wm.progress_update(5)
                wm.progress_end()

                return {"FINISHED"}
            else:
                # keep_object Trueのときの処理を書こうと思ったけどめんどくさくなった
                return {"FINISHED"}

        else:
            # pollで弾くので普通は表示されない
            self.report({"ERROR"}, f"active object is not tategaki-text-container")
            return {"CANCELED"}


######### UI ##########


class TATEGAKI_MT_Tools(bpy.types.Menu):
    """ツールの一覧メニュー"""

    bl_label = "Tategaki Tools"
    bl_idname = "TATEGAKI_MT_Tools"

    # 本クラスの処理が実行可能かを判定する
    @classmethod
    def poll(cls, context):
        try:
            # うまく行かない
            if TATEGAKI in context.active_object.keys():
                return True
            if context.active_object.type == "FONT":
                return True
            return False
        except AttributeError:
            return False

    def draw(self, context):
        layout = self.layout
        layout.operator(TATEGAKI_OT_ConvertToTategakiText.bl_idname)
        layout.operator(TATEGAKI_OT_Duplicate.bl_idname)
        layout.separator()
        layout.operator(TATEGAKI_OT_UpdateChrSpacing.bl_idname)
        layout.operator(TATEGAKI_OT_UpdateLineSpacing.bl_idname)
        layout.operator(TATEGAKI_OT_UpdateLineCharacterLimit.bl_idname)
        layout.separator()
        layout.operator_menu_enum(
            TATEGAKI_OT_Freeze.bl_idname, "freeze_type", text="Convert To"
        )


def tategaki_menu(self, context):
    layout: bpy.types.UILayout = self.layout
    layout.separator()
    layout.menu(TATEGAKI_MT_Tools.bl_idname, icon="PLUGIN")


######### registration ##########

classses = [
    TATEGAKI_MT_Tools,
    TATEGAKI_OT_ConvertToTategakiText,
    TATEGAKI_OT_UpdateChrSpacing,
    TATEGAKI_OT_UpdateLineSpacing,
    TATEGAKI_OT_UpdateLineCharacterLimit,
    TATEGAKI_OT_Freeze,
    TATEGAKI_OT_Duplicate,
]
tools: list = []


def register():

    for c in classses:
        bpy.utils.register_class(c)
    for t in tools:
        bpy.utils.register_tool(t)

    bpy.types.VIEW3D_MT_object.append(tategaki_menu)
    bpy.types.VIEW3D_MT_object_context_menu.append(tategaki_menu)


def unregister():
    for c in classses:
        bpy.utils.unregister_class(c)
    for t in tools:
        bpy.utils.unregister_tool(t)

    bpy.types.VIEW3D_MT_object.remove(tategaki_menu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(tategaki_menu)
