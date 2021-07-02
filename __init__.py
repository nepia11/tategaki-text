import importlib
from logging import getLogger, StreamHandler, Formatter, handlers, DEBUG
import sys
import bpy
import os
import datetime
from .lib import get_module_names


# アドオン情報
bl_info = {
    "name": "tategaki text",
    "author": "nepia",
    "version": (0, 1, 0),
    "blender": (2, 83, 0),
    "location": "addon (operator,panel,ui) location",
    "description": "addon description",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "",
}


def setup_logger(log_folder: str, modname=__name__):
    """loggerの設定をする"""
    logger = getLogger(modname)
    logger.setLevel(DEBUG)
    # log重複回避　https://nigimitama.hatenablog.jp/entry/2021/01/27/084458
    if not logger.hasHandlers():
        sh = StreamHandler()
        sh.setLevel(DEBUG)
        formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        fh = handlers.RotatingFileHandler(log_folder, maxBytes=500000, backupCount=2)
        fh.setLevel(DEBUG)
        fh_formatter = Formatter(
            "%(asctime)s - %(filename)s - %(name)s"
            " - %(lineno)d - %(levelname)s - %(message)s"
        )
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)
    return logger


# log周りの設定
scripts_dir = os.path.dirname(os.path.abspath(__file__))
log_folder = os.path.join(scripts_dir, "log", f"{datetime.date.today()}.log")
logger = setup_logger(log_folder, modname=__name__)
logger.debug("hello")


# サブモジュールのインポート
module_names = get_module_names()
namespace = {}
for name in module_names:
    fullname = "{}.{}.{}".format(__package__, "lib", name)
    # if "bpy" in locals():
    if fullname in sys.modules:
        namespace[name] = importlib.reload(sys.modules[fullname])
    else:
        namespace[name] = importlib.import_module(fullname)
logger.debug(namespace)


def register_icons():
    icons = [
        "TEST",
    ]
    bpy.types.Scene.scatter_gpencil = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    for icon in icons:
        bpy.types.Scene.scatter_gpencil.load(
            icon, os.path.join(icons_dir, icon + ".png"), "IMAGE"
        )


def unregister_icons():
    bpy.utils.previews.remove(bpy.types.Scene.scatter_gpencil)


def register():
    for module in namespace.values():
        module.register()
    # register_icons()
    _name = bl_info["name"]
    _version = bl_info["version"]
    logger.debug(f"succeeded register {_name}:version{_version}")


def unregister():
    for module in namespace.values():
        module.unregister()
    # unregister_icons()


if __name__ == "__main__":
    register()
