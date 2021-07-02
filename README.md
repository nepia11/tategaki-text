# 縦書きテキスト

縦書きテキストをいい感じに作るアドオン

## メモ

作文用紙みたいに等間隔にテキストオブジェクトを作って位置文字ずつ配置するのはどうだろう

オブジェクトが膨大になってしまうのでフリーズ・復元機能が必要そう

文字組みはスクリプトでいい感じにする（、。「」（）など）

### 構造

```
text_container:empty
  grid(0,0)
  body:strings
  style:etc
  chrbox:empty
    layout
    str
    textobject
```
