# python-practice

Python の練習と、授業課題「GitHub Version Control 実習」の提出用リポジトリです。

## 中身

| フォルダ | 内容 |
|---|---|
| [`game/`](game/) | **LAVA CRAFT 3D**: Ursina で作った 3D ゲーム。くわしくは [game/README.md](game/README.md) |

## LAVA CRAFT 3D（～ 天国まで逃げろ！ ～）

下から溶岩が上がってくる、たてに長い穴の中から、ブロックをほって・置いて上へにげるゲームです。高さ 120m の天国の門に着いたらクリアです。

```
pip install -r requirements.txt
cd game
python lava_craft_3d.py
```

Windows なら `game/run_3d.bat` をダブルクリックしても起動できます。

## バージョンの記録（修正・改善したところ）

| バージョン | コミット | 修正・改善したところ |
|---|---|---|
| Version 1 | `Add LAVA CRAFT 3D (Ursina) game` | 最初の版。たて穴の世界、ほる・置く、上がってくる溶岩、溶岩の波、落石、回復の実、ジェット機、ゲームオーバー / クリア |
| Version 2 | `Version 2: Updated Python code` | ゲームを仕上げた版（詳しくは下の箇条書き） |
| Version 3 | `Version 3: Add README with code explanation` | `game/README.md` に、遊び方・ルール・プログラムのしくみ（①〜⑨）・工夫した点を追加 |

Version 2 で修正・改善したところ:

- むずかしさ選択を追加（やさしい / ふつう / むずかしい）
- むずかしさごとのベストスコアを保存するようにした
- 効果音を追加。プログラムで波形を作るので、音のファイルは使わない
- エリアごとのけしき（結晶・木・雲・柱）と、天国の門を追加
- 手に持ったブロック、ほったときのかけら、ジェット機の炎、天国までの進み具合バーを追加
- 溶岩が近いと画面が赤くなるようにした
- 開発用の表示（FPS・エンティティ数）を消した

Version 2 の行の例:

| | 行 | 説明 |
|---|---|---|
| 追加 | `+ def make_sound(path, kind, notes, rate=22050):` | 効果音を作る関数 |
| 削除 | `- window.fps_counter.enabled = True` | 開発中に使っていた FPS 表示 |

変更の中身は、[Commits](https://github.com/dreampass2021-coder/python-practice/commits/main) から各コミットを開くと、緑（追加）と赤（削除）の行で見られます。

## 使ったもの

- Python 3.13
- [Ursina](https://www.ursinaengine.org/)（3D ゲームエンジン）
- Git / GitHub / VS Code
