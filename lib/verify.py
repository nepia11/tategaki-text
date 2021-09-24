# 動作検証やパフォーマンスの検証をするコードをおいておくところ
import bpy
from bpy.types import Object, TextCurve
from .util import timer


@timer
def test_create_text_object(count: int = 100):
    """任意個のテキストオブジェクトを名前をつけて生成、テキストオブジェクトのリストを返す"""
    collection = bpy.context.scene.collection  # Master Collection

    data_list = [bpy.data.curves.new(f"test.{i}", "FONT") for i in range(count)]
    objects: Object = [bpy.data.objects.new(data.name, data) for data in data_list]

    for obj in objects:
        collection.objects.link(obj)

    return objects


@timer
def test_create_linked_text_object(count: int = 100):
    """
    任意個のテキストオブジェクトを名前をつけて生成、テキストオブジェクトのリストを返す
    連続実行した場合こっちのほうが速い
    リンクオブジェクトのメッシュ化と結合は一瞬でできるっぽい
    """
    collection = bpy.context.scene.collection  # Master Collection

    orig_data = bpy.data.curves.new(f"test", "FONT")
    objects: Object = [
        bpy.data.objects.new(f"test.{i}", orig_data) for i in range(count)
    ]

    for obj in objects:
        collection.objects.link(obj)

    return objects


def unique_strings(string: str):
    """
    文字列の重複を排除する
    サンプルテキストで399 -> 110まで重複を減らせたので有用かも
    """
    return "".join(set(string))


def get_chr_data(font_name: str, chr: str):
    """フォントの文字を取得"""
    name = f"{font_name}.{chr}"
    data = bpy.data.curves.get(name)
    if data is None:
        data = bpy.data.curves.new(name, "FONT")
        data.body = chr
        data.align_y = "CENTER"
        data.align_x = "CENTER"
        data.font = bpy.data.fonts[font_name]
    return data


@timer
def test_get_chr_data(count=100):
    """検索は結構速い"""
    li = [get_chr_data("Bfont", "A") for c in range(count)]
    pass
