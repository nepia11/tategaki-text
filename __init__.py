import importlib
from logging import getLogger, StreamHandler, Formatter, handlers, DEBUG, INFO
import sys
import os
import datetime

# import bpy

module_names = [
    "translations",
    "tategaki",
]

# アドオン情報
bl_info = {
    "name": "Tategaki Text Tools",
    "author": "nepia",
    "version": (3, 0, 0),
    "blender": (2, 93, 0),
    "location": "view3d>object_context_menu>Tategaki Tools",
    "description": "テキストオブジェクトを縦書きに変換、細かな調整をするツール郡です",
    "warning": "",
    "wiki_url": "https://github.com/nepia11/tategaki-text",
    "tracker_url": "",
    "category": "Object",
}


LOGLEVEL = DEBUG
# LOGLEVEL = INFO


def setup_logger(log_folder: str, modname=__name__):
    """loggerの設定をする"""
    logger = getLogger(modname)
    logger.setLevel(LOGLEVEL)
    # log重複回避　https://nigimitama.hatenablog.jp/entry/2021/01/27/084458
    if not logger.hasHandlers():
        sh = StreamHandler()
        sh.setLevel(LOGLEVEL)
        formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        fh = handlers.RotatingFileHandler(log_folder, maxBytes=500000, backupCount=2)
        fh.setLevel(LOGLEVEL)
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
namespace = {}
for name in module_names:
    fullname = "{}.{}.{}".format(__package__, "lib", name)
    # if "bpy" in locals():
    if fullname in sys.modules:
        namespace[name] = importlib.reload(sys.modules[fullname])
    else:
        namespace[name] = importlib.import_module(fullname)
logger.debug(namespace)


def register():
    print(__name__)
    for module in namespace.values():
        module.register()
    logger.info(f"registered {bl_info['name']}:version{bl_info['version']}")


def unregister():
    for module in namespace.values():
        module.unregister()
    logger.info(f"unregistered {bl_info['name']}:version{bl_info['version']}")


if __name__ == "__main__":
    register()
