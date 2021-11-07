import bpy

keys = [
    {
        "context": "Operator",
        "key": "Convert to vertical text",
        "ja_JP": "縦書きテキストに変換",
    },
    {
        "context": "*",
        "key": "Create a vertical text object from the active text object.",
        "ja_JP": "アクティブなテキストオブジェクトから縦書きテキストオブジェクトを生成",
    },
    {
        "context": "Operator",
        "key": "Duplicate vertical text",
        "ja_JP": "縦書きテキストを複製",
    },
    {
        "context": "*",
        "key": "Duplicate the active vertical text object",
        "ja_JP": "アクティブな縦書きテキストオブジェクトを複製",
    },
    {
        "context": "Operator",
        "key": "update character spacing",
        "ja_JP": "文字間隔を更新",
    },
    {
        "context": "*",
        "key": "Update character spacing and auto-kerning options for vertical text",
        "ja_JP": "縦書きテキストの文字間隔と自動カーニングオプションを更新する",
    },
    {
        "context": "*",
        "key": "Automatic character spacing.",
        "ja_JP": "自動的に文字詰めをする",
    },
    {
        "context": "*",
        "key": "character spacing",
        "ja_JP": "文字間隔",
    },
    {
        "context": "*",
        "key": "line spacing",
        "ja_JP": "行間隔",
    },
    {
        "context": "Operator",
        "key": "update line spacing",
        "ja_JP": "行間を更新",
    },
    {
        "context": "*",
        "key": "Update line spacing for Vertical text.",
        "ja_JP": "縦書きテキストの行間を更新する",
    },
    {
        "context": "*",
        "key": "Update the character limit per line for vertical text.",
        "ja_JP": "縦書きテキストの1行あたりの文字数制限を更新する",
    },
    {
        "context": "*",
        "key": "line character limit",
        "ja_JP": "行文字数制限",
    },
    {
        "context": "Operator",
        "key": "update line character limit",
        "ja_JP": "行文字数制限を更新",
    },
    {
        "context": "*",
        "key": "Convert vertical text objects to meshes, curves, and gpencils",
        "ja_JP": "縦書きテキストオブジェクトをメッシュ、カーブ、gpencilに変換する",
    },
    {
        "context": "*",
        "key": "Deleting a vertical text object",
        "ja_JP": "縦書きテキストオブジェクトを削除する",
    },
]


def get_dict():
    translation_dict = {
        "en_US": {(v["context"], v["key"]): v["key"] for v in keys},
        "ja_JP": {(v["context"], v["key"]): v["ja_JP"] for v in keys},
    }
    return translation_dict


def register():
    transration_dict = get_dict()
    bpy.app.translations.register(__name__, transration_dict)


def unregister():
    bpy.app.translations.unregister(__name__)
