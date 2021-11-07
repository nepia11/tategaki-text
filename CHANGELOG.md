# Changelog

[参考](https://keepachangelog.com/ja/1.0.0/)
[テンプレート](##template)

## [3.0.0] - 2021-11-07

### Added

- ops.tategaki.duplicate 実装: 縦書きテキストから新規縦書きテキストを生成
- ops.tategaki.remove 実装: 縦書きテキストオブジェクトをきれいに削除する
- ops.tategaki.freeze に gpencil への変換を実装
- 翻訳を実装(jp/en)

### Changed

- ops.tategaki.freeze に進捗表示を追加

## [2.0.0] - 2021-10-24

### Added

- 行文字数調整 : 縦書きテキストの 1 行あたりの文字数制限を調整する
- メッシュに変換 : 縦書きテキストを単一のメッシュオブジェクトに変換
- カーブに変換 : 縦書きテキストを単一のカーブオブジェクトに変換

### Changed

- ops ベースの処理から data ベースに書き換えて高速化
- TextCurve data の重複を排除してテキストオブジェクト生成を高速化
- 行間・字間調整オペレータを分割

## [0.2.0] - 2021-08-14

### Changed

- bpy.ops で実装していた部分を bpy.data で処理するように変更して高速化
  - 600ms かかる処理が 200ms ほどになった
  - 部分的には 400ms->5ms
- 細かやなコードの整理
- changelog の追加
- 自動カーニングが安定動作するようになった

## template

## [0.0.0] - 2021-01-01

### Added

- 新機能について。

### Changed

- 既存機能の変更について。

### Deprecated

- 間もなく削除される機能について。

### Removed

- 今回で削除された機能について。

### Fixed

- バグ修正について。

### Security

- 脆弱性に関する場合。
