# コピペする用　__init__への登録は解除しといたほうが良い
import bpy
from logging import getLogger

logger = getLogger(__name__)

translation = bpy.app.translations.pgettext


class TEMPLATE_OT_MyOperator(bpy.types.Operator):
    """my operator description"""

    bl_idname = "template.my_operator"
    bl_label = translation("my operator")
    bl_description = "operator description"
    bl_options = {"REGISTER", "UNDO"}

    # メニューを実行したときに呼ばれるメソッド
    def execute(self, context):
        # logging
        logger.debug("exec my ops")
        # infoにメッセージを通知
        self.report({"INFO"}, "execute my operator")
        # 正常終了ステータスを返す
        return {"FINISHED"}


class TEMPLATE_OT_MyTimerEventOperator(bpy.types.Operator):
    """
    タイマーイベントを使ってアレコレするオペレータ
    timer eventについて参照
    https://colorful-pico.net/introduction-to-addon-development-in-blender/2.8/html/chapter_03/03_Handle_Timer_Event.html
    """

    bl_idname = "template.my_timer_event_operator"
    bl_label = "timer event operator"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    # タイマのハンドラ
    __timer = None
    interval = 0.2

    @classmethod
    def is_running(cls):
        # モーダルモード中はTrue
        return True if cls.__timer else False

    def __handle_add(self, context):
        op_cls = TEMPLATE_OT_MyTimerEventOperator
        if not self.is_running():
            # タイマを登録
            interval = self.interval
            op_cls.__timer = context.window_manager.event_timer_add(
                interval, window=context.window
            )
            # モーダルモードへの移行
            context.window_manager.modal_handler_add(self)

    def __handle_remove(self, context):
        op_cls = TEMPLATE_OT_MyTimerEventOperator
        if self.is_running():
            # タイマの登録を解除
            context.window_manager.event_timer_remove(op_cls.__timer)
            op_cls.__timer = None

    def modal(self, context, event):
        # エリアを再描画
        if context.area:
            context.area.tag_redraw()
        if not self.is_running():
            return {"FINISHED"}
        # タイマーイベントが来た時にする処理
        if event.type == "TIMER":
            try:
                pass
            except (KeyError):
                # モーダルモードを終了
                logger.debug("key error")
                return {"CANCELLED"}

        return {"PASS_THROUGH"}

    def invoke(self, context, event):
        op_cls = TEMPLATE_OT_MyTimerEventOperator

        if context.area.type == "VIEW_3D":
            if not op_cls.is_running():
                # モーダルモードを開始
                self.__handle_add(context)
                return {"RUNNING_MODAL"}
            # [終了] ボタンが押された時の処理
            else:
                # モーダルモードを終了
                self.__handle_remove(context)
                return {"FINISHED"}
        else:
            return {"FINISHED"}


classses = [TEMPLATE_OT_MyTimerEventOperator, TEMPLATE_OT_MyTimerEventOperator]
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
