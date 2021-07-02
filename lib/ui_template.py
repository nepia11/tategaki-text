import bpy
from logging import getLogger

logger = getLogger(__name__)


class TEMPLATE_PT_MyPanel(bpy.types.Panel):

    bl_label = "My panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MY"

    # 本クラスの処理が実行可能かを判定する
    @classmethod
    def poll(cls, context):
        try:
            # 何かしらの判定処理
            return True
        except AttributeError:
            return False

    def draw(self, context):
        layout = self.layout
        layout.label(text="hoge")
        layout.operator("template.my_operator")
        layout.separator()
        # ストローク並べ替え
        layout.label(text="Sorting strokes")
        arrange_props = [
            ("TOP", "Bring to Front"),
            ("UP", "Bring Forward"),
            ("DOWN", "Send Backward"),
            ("BOTTOM", "Send to Back"),
        ]
        for prop in arrange_props:
            op = layout.operator("gpencil.stroke_arrange", text=prop[1])
            op.direction = prop[0]
        layout.separator()


classses = [TEMPLATE_PT_MyPanel]
tools = []


def register():
    for c in classses:
        bpy.utils.register_class(c)
    for t in tools:
        bpy.utils.register_tool(t)


def unregister():
    for c in classses:
        bpy.utils.unregister_class(c)
    for t in tools:
        bpy.utils.unregister_tool(t)
