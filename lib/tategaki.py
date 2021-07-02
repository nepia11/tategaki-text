# コピペする用　__init__への登録は解除しといたほうが良い
import bpy
from logging import getLogger
from .util import random_name

logger = getLogger(__name__)

translation = bpy.app.translations.pgettext


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
        bpy.ops.object.empty_add(type="PLAIN_AXES", align="CURSOR", scale=(1, 1, 1))
        text_container: bpy.types.Object = context.active_object
        text_container.name = "tatetext"
        tag = random_name(8)
        props = {
            "is_tategaki": True,
            "grid": [10, 10],
            "margin": [0.2, 0.2],
            "tag": tag,
        }
        text_container.id_data["tategaki"] = props

        # chrコンテナを作る
        # まず行
        def create_line(line_length: int, margin: float):
            chr_list = []
            for _i in range(line_length):
                bpy.ops.object.empty_add(
                    radius=0.1,
                    type="CUBE",
                    align="WORLD",
                    location=(0.0, 0.0, 0.0),
                    rotation=(0.0, 0.0, 0.0),
                )
                chr_container: bpy.types.Object = context.active_object
                chr_list.append(chr_container)
            for i, _chr in enumerate(chr_list):
                if i == 0:
                    continue
                # リストの一個目を親にしてparentと位置を動かす
                _chr: bpy.types.Object
                _chr.parent = chr_list[0]
                _chr.location = (0.0, 0 - margin * i, 0.0)
                _chr.hide_select = True
            return chr_list

        chr_lists = []
        for i in range(props["grid"][1]):
            margin_x, margin_y = props["margin"]
            chr_list = create_line(line_length=props["grid"][0], margin=margin_y)
            chr_list[0].parent = text_container
            chr_list[0].location = (0 - margin_x * i, 0, 0)
            # rename
            for r, _chr in enumerate(chr_list):
                _chr.name = f"chr_{tag}.{r}.{i}"
            chr_lists.append(chr_list)

        # logger.debug(chr_lists)
        context.view_layer.objects.active = text_container
        text_container.select_set(True)
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
            if context.active_object["tategaki"]:
                return True
        except AttributeError:
            return False

    def draw(self, context):
        layout = self.layout
        layout.label(text="hoge")
        layout.label(text=str(context.active_object["tategaki"]))
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
