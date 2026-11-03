# ============================================================
#  LAVA CRAFT 3D（～ 天国まで逃げろ！ ～）  Ursina 版
#
#  たてに長い「たて穴」の中で、下から 溶岩が 上がってくる。
#  かべや 浮き島の ブロックを ほって 資材を あつめ、
#  ブロックを 置いて 足場を 作りながら 上へ 上へ にげる。
#  高さ 120m の 天国の 門に 着いたら クリア！
#  とちゅうの かべの 奥には 鍵が 3つ かくれている。全部 見つけて クリアすると…？
#
#  操作:
#    WASD     … 移動          マウス … 見回す       Space … ジャンプ
#    左クリック … おしつづけて ブロックを ほる（かたい ブロックほど 時間が かかる）
#    右クリック … ブロックを 置く
#    Q        … 自分の 真下に ブロックを 積んで 1だん 上がる（おしつづけると 連続）
#               ※真下を 見て 右クリックを おしつづけても 同じ
#    F        … 剣を ふる（敵を たおすと コインが もらえる）
#    B        … ショップ（コインで お助けアイテムを 買う）
#    1 / 2 / 3 … 置く 材料を えらぶ（木・石・鉄）   ※タイトルでは むずかしさを えらぶ
#    C        … ジェット機（石と鉄を 使って 一気に 上へ）
#    Esc      … メニュー（もどる / 全画面 / やめる）
#    F11      … 全画面 ⇔ ウィンドウ を 切りかえる（いつでも）
#
#  デバッグモード（テスト用）: run_3d_debug.bat か「python lava_craft_3d.py --debug」で 起動すると 使える
#    F1 資材・コイン +50 と HP まんたん   F2 無敵 ON/OFF        F3 10m 上へ ワープ
#    F4 次の エリアへ ワープ               F5 溶岩 止める/動かす  F6 敵を 出す
#    F7 鍵の 宝箱の 高さへ ワープ          F8 くわしい 情報を 表示
#    ※デバッグモードでは ベストスコアを 保存しない
#
#  プログラムの つくり（上から 順番に 読めば わかるように 並べてある）
#    ① 準備        … Ursina を 起動して、フォント・効果音・テクスチャを 用意する
#    ② 設定        … ゲームの 数字（速さ・高さ・敵・ショップ など）を まとめた所
#    ③ ブロック    … Block クラスと、たて穴を 作る 関数
#    ④ けしき      … エリアごとの かざり と、まわりを ただよう 光の粒
#    ⑤ プレイヤーと 画面の 文字
#    ⑥ 落石・敵・剣・回復の実・ジェット機・真下に積む・小さな 演出
#    ⑦ ゲームの 流れ（タイトル・スタート・ゲームオーバー・メニュー・ショップ）
#    ⑧ input()  … キー・マウスを おしたとき（Ursina が 自動で よぶ）
#    ⑨ update() … 毎フレーム（1秒に 約60回）よばれる
# ============================================================
import json
import math
import os
import random
import shutil
import struct
import sys
import wave

from PIL import Image                                  # テクスチャを 作るのに 使う（Ursina と いっしょに 入る）
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController


# ============================================================
# ① 準備
# ============================================================
app = Ursina(title='LAVA CRAFT 3D')
window.exit_button.visible = False
window.fps_counter.enabled = False
for counter in ('entity_counter', 'collider_counter'):   # 右上の 数字（開発用の 表示）を 消す
    if hasattr(window, counter):
        getattr(window, counter).enabled = False
HERE = os.path.dirname(os.path.abspath(__file__))

# 日本語が 出る フォント
#   Ursina は「このファイルと 同じ フォルダ」から フォントを さがすので、
#   Windows の メイリオを ここに コピーしてから 使う（2回目からは コピー済みの ものを 使う）
for name in ('meiryo.ttc', 'YuGothM.ttc', 'msgothic.ttc'):
    src = os.path.join(r'C:\Windows\Fonts', name)
    dst = os.path.join(HERE, name)
    if not os.path.exists(dst) and os.path.exists(src):
        shutil.copy(src, dst)
    if os.path.exists(dst):
        Text.default_font = name
        break


# 効果音: 音の ファイルは 使わず、プログラムで 波形を 計算して wav を 作る（sounds フォルダ）
#   notes = [(周波数Hz, 長さ秒), ...]   kind = 'sine'（なめらか）/ 'square'（ピコピコ）/ 'noise'（ザッ）
SOUNDS = {
    'mine':  ('noise',  [(0, 0.07)]),
    'place': ('square', [(220, 0.05)]),
    'hurt':  ('square', [(160, 0.08), (110, 0.12)]),
    'heal':  ('sine',   [(660, 0.07), (880, 0.1)]),
    'jet':   ('noise',  [(0, 0.6)]),
    'warn':  ('square', [(880, 0.15), (0, 0.08), (880, 0.15), (0, 0.08), (880, 0.15)]),
    'clear': ('sine',   [(523, 0.12), (659, 0.12), (784, 0.12), (1047, 0.35)]),
    'over':  ('sine',   [(392, 0.18), (330, 0.18), (262, 0.4)]),
    'pick':  ('sine',   [(990, 0.05)]),
    'tick':  ('noise',  [(0, 0.03)]),                      # ほっている 途中の コツコツ音
    'swing': ('noise',  [(0, 0.09)]),                      # 剣を ふる 音
    'hit':   ('square', [(330, 0.04), (220, 0.05)]),       # 敵に 当たった 音
    'coin':  ('sine',   [(1320, 0.05), (1760, 0.09)]),     # コインが 入った 音
    'key':   ('sine',   [(784, 0.1), (988, 0.1), (1319, 0.25)]),   # 鍵を 見つけた 音
    'buy':   ('sine',   [(880, 0.06), (1175, 0.1)]),       # 買い物の 音
}


def make_sound(path, kind, notes, rate=22050):
    frames = bytearray()
    for freq, sec in notes:
        n = int(rate * sec)
        for i in range(n):
            fade = min(1.0, (n - i) / (rate * 0.03))       # 音の 終わりを なめらかに 消す
            t = i / rate
            if freq == 0 and kind != 'noise':
                v = 0                                     # 周波数 0 は 休み
            elif kind == 'noise':
                v = random.uniform(-1, 1) * (1 - i / n)
            elif kind == 'square':
                v = 1 if math.sin(2 * math.pi * freq * t) > 0 else -1
            else:
                v = math.sin(2 * math.pi * freq * t)
            frames += struct.pack('<h', int(v * fade * 9000))
    with wave.open(path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(bytes(frames))


sound_files = {}
os.makedirs(os.path.join(HERE, 'sounds'), exist_ok=True)
for name, (kind, notes) in SOUNDS.items():
    path = os.path.join(HERE, 'sounds', name + '.wav')
    if not os.path.exists(path):
        make_sound(path, kind, notes)
    try:
        sound_files[name] = Audio('sounds/' + name + '.wav', autoplay=False, loop=False, volume=0.5)
    except Exception:
        pass                                              # 音が 出せない PC でも ゲームは 動く


def sfx(name):
    s = sound_files.get(name)
    if s:
        try:
            s.play()
        except Exception:
            pass


# テクスチャ: 画像ファイルは 使わず、16×16 の ドット絵を プログラムで 描く
#   random.Random(名前) を 使うので、毎回 同じ 絵に なる
def make_texture(kind):
    rnd = random.Random(kind)
    img = Image.new('RGB', (16, 16))
    px = img.load()

    def put(x, y, c):
        px[x % 16, y % 16] = tuple(max(0, min(255, int(v))) for v in c)

    def noise(base, amount):                            # 全体を 少しずつ ちがう 色で ぬる
        for y in range(16):
            for x in range(16):
                d = rnd.uniform(-amount, amount)
                put(x, y, (base[0] + d, base[1] + d, base[2] + d))

    def specks(colors, count, size=2):                  # つぶつぶを 散らす
        for _ in range(count):
            x, y, c = rnd.randrange(16), rnd.randrange(16), rnd.choice(colors)
            for dx in range(size):
                for dy in range(size):
                    if rnd.random() < 0.8:
                        put(x + dx, y + dy, c)

    if kind == 'stone':
        noise((128, 128, 138), 12)
        specks([(100, 100, 112), (150, 150, 160)], 10, 2)
    elif kind == 'wood':                                # 木の 板（横の 板が 4まい）
        for y in range(16):
            for x in range(16):
                c = 150 + rnd.uniform(-8, 8) + (12 if (y // 4) % 2 else 0) + (6 if (x + y * 3) % 7 == 0 else 0)
                put(x, y, (c + 45, c - 5, c - 70))
        for y in range(3, 16, 4):
            for x in range(16):
                put(x, y, (120, 75, 35))
        for y in range(16):
            put((y // 4) * 5 + 2, y, (120, 75, 35))
    elif kind == 'iron':                                # 石に 銀色の 鉱石が まざる
        noise((120, 120, 132), 12)
        specks([(235, 238, 250), (205, 212, 230), (250, 236, 210)], 15, 2)
    elif kind == 'rubble':                              # くず石（じゃり）
        noise((98, 86, 76), 10)
        specks([(70, 60, 54), (130, 116, 100), (85, 74, 66)], 26, 2)
    elif kind == 'cloud':
        noise((240, 244, 255), 6)
        specks([(225, 232, 250)], 8, 3)
    elif kind == 'gold':
        noise((235, 185, 55), 12)
        for i in range(16):
            put(i, i, (255, 236, 150))
            put(i + 1, i, (255, 226, 120))
    elif kind == 'ground':
        noise((70, 64, 82), 10)
        specks([(52, 46, 62), (90, 84, 104)], 14, 2)
    elif kind == 'chest':                               # 宝箱（鍵が 入っている）
        noise((140, 88, 44), 10)
        for x in range(16):
            for y in (7, 8):
                put(x, y, (235, 190, 60))
        for x, y in ((7, 6), (8, 6), (7, 9), (8, 9), (6, 7), (9, 7), (6, 8), (9, 8)):
            put(x, y, (255, 235, 130))
        put(7, 7, (50, 30, 20))
        put(8, 8, (50, 30, 20))
    for i in range(16):                                 # ふちを 少し 暗く（さかい目が 分かる）
        for x, y in ((i, 0), (i, 15), (0, i), (15, i)):
            r, gg, b = px[x, y]
            px[x, y] = (int(r * 0.75), int(gg * 0.75), int(b * 0.75))
    t = Texture(img)
    t.filtering = None                                  # ぼかさない（ドット絵らしく）
    return t


TEXTURES = {k: make_texture(k) for k in ('stone', 'wood', 'iron', 'rubble', 'cloud', 'gold', 'ground', 'chest')}


# ============================================================
# ② 設定（ここの 数字を 変えると むずかしさが 変わる）
# ============================================================
GOAL = 120                  # 天国の 高さ（m）。1ブロック = 1m
HALF = 5                    # たて穴の 広さ（まんなかから かべまで 5ブロック）
REACH = 6                   # ほる・置く ことが できる きょり（ブロック）
MAX_HP = 5

LAVA_START_SPEED = 0.12     # 溶岩の 最初の 速さ（m/秒）
LAVA_ACCEL = 0.004          # 1秒ごとに 速くなる 量
LAVA_MAX_SPEED = 1.2        # 溶岩の 最高速度
WAVE_INTERVAL = (35, 50)    # 溶岩の「波」が 来る 間かく（秒）
WAVE_WARNING = 3            # 警告から 波までの 時間（秒）
WAVE_TIME = 3               # 波が つづく 時間（秒）
WAVE_POWER = 4              # 波のあいだ 溶岩が 何倍 速くなるか
WOOD_BURN = 3               # 置いた 木は、溶岩から この高さまで 近づくと 燃える

# かたさ: ほりおわるまでに 左クリックを おしつづける 時間（秒）
HARDNESS = {'cloud': 0.2, 'rubble': 0.35, 'wood': 0.3, 'stone': 0.7, 'iron': 1.5, 'chest': 1.0}

PILLAR_WAIT = 0.18          # Q で 積むときの 間かく（秒）
PILLAR_SPEED = 9            # 積むときに 体が 上がる 速さ（m/秒）

ROCK_INTERVAL = 5           # 落石の 間かく（秒）
ROCK_START = 8              # この 高さ（m）より 上で 落石が はじまる

JET_COST = {'stone': 8, 'iron': 8}   # ジェット機の 材料
JET_TIME = 3                # ジェット機が 飛ぶ 時間（秒）
JET_SPEED = 10              # ジェット機の 上る 速さ（m/秒）→ 3秒で 30m

# 敵: エリア → (名前, HP, 速さ, たおすと もらえる コイン, 動き方, 色)
#   動き方: 'fly' = 飛んで 追いかけてくる   'hop' = ブロックの 上を ぴょんぴょん はねてくる
ENEMY_TYPES = {
    '洞窟': ('コウモリ',   2, 1.8, 2, 'fly', '#5b3b8c'),
    '森':   ('スライム',   3, 2.6, 3, 'hop', '#4fcf6a'),
    '空':   ('カラス',     3, 3.0, 3, 'fly', '#2a2a36'),
    '天国': ('まよい天使', 4, 2.8, 4, 'fly', '#fff4d6'),
}
ENEMY_INTERVAL = 10         # 敵が 出てくる 間かく（秒）
ENEMY_FIRST = 20            # ゲームが はじまって 最初の 敵が 出るまでの 時間（秒）
ENEMY_MAX = 3               # 同時に 出る 敵の 数
ENEMY_START = 6             # この 高さ（m）より 上で 敵が 出はじめる
ENEMY_REST = 4.0            # 敵が 突進したあと、はなれていく 時間（秒）
ENEMY_WINDUP = 0.8          # 飛ぶ敵が 突進する 前に 止まって 赤く 光る 時間（秒）= よける・斬る チャンス
SWORD_REACH = 2.8           # 剣が とどく きょり
SWORD_WAIT = 0.35           # 剣を ふる 間かく（秒）

# ショップ: (名前, 値段コイン, せつめい, こうか)
SHOP_ITEMS = [
    ('回復薬',       5, 'HP を 1 回復',                  'heal'),
    ('資材パック',   4, '木 5・石 5',                    'pack'),
    ('鉄インゴット', 6, '鉄 3',                          'iron'),
    ('シールド',     8, '次の ダメージを 1回 ふせぐ',    'shield'),
    ('溶岩ストップ', 10, '溶岩を 10秒 止める',           'stop'),
    ('鍵さがし',     8, '近い 鍵の 方向を 40秒 教える',  'radar'),
    ('ジェット券',   15, '材料なしで ジェット機に 1回',  'jet'),
]

# 鍵: (エリア, かくれている 高さの はんい m)。エリアごとに 1つ、かべの 奥の 宝箱に 入っている
KEY_RANGES = [('洞窟', 8, 26), ('森', 34, 56), ('空', 64, 86)]

# やられたときの ひとこと: 原因 → (ことば, [ヒント, ...])
DEATH_HINTS = {
    'lava':  ('溶岩に のまれた…', ['Q を おしつづけると、真下に ブロックを 積んで すばやく 上れる',
                                    '石 8・鉄 8 で C の ジェット機。一気に 30m 上がれる',
                                    'ショップの「溶岩ストップ」で 10秒 時間が かせげる']),
    'rock':  ('落石に つぶされた…', ['地面の 黒い 影が、石が 落ちてくる 場所。影から はなれよう',
                                     'ショップの「シールド」で 1回 ダメージを ふせげる']),
    'enemy': ('敵に やられた…', ['F で 剣を ふれる。たおすと コインが もらえる',
                                 '敵は 足場の 上だと 戦いやすい。ショップの 回復薬も 使おう']),
}

# むずかしさ: (名前, 溶岩の 速さの 倍率, 溶岩が 動きだすまでの 時間, 最初の 資材)
DIFFICULTIES = [
    ('やさしい',   0.7, 35, {'wood': 16, 'stone': 16, 'iron': 4}),
    ('ふつう',     1.0, 25, {'wood': 10, 'stone': 10, 'iron': 0}),
    ('むずかしい', 1.4, 12, {'wood': 3, 'stone': 3, 'iron': 0}),
]
BEST_FILE = os.path.join(HERE, 'lava_craft_3d_best.json')
DEBUG = '--debug' in sys.argv           # デバッグモード（F1〜F8 の テスト用キー）

# エリア: (はじまる 高さ m, 名前, 空の色, 資材の 出やすさ, 霧の こさ)
#   鉄は 大事な 鉱石なので 少なめ。そのかわり まわりを くず石で 囲ってある
AREAS = [
    (0,  '洞窟', color.hex('#100c22'), {'wood': 0.20, 'stone': 0.68, 'iron': 0.12}, 0.055),
    (30, '森',   color.hex('#3f7a6a'), {'wood': 0.60, 'stone': 0.30, 'iron': 0.10}, 0.035),
    (60, '空',   color.hex('#6aa2ee'), {'wood': 0.25, 'stone': 0.50, 'iron': 0.25}, 0.014),
    (90, '天国', color.hex('#ffe2c0'), {'wood': 0.20, 'stone': 0.50, 'iron': 0.30}, 0.022),
]
BLOCK_COLOR = {                         # かけら・手に 持つ ブロックの 色
    'ground': color.hex('#5a5664'),
    'wood':   color.hex('#d08c4c'),
    'stone':  color.hex('#a8a8b4'),
    'iron':   color.hex('#eef1fa'),
    'rubble': color.hex('#6e6258'),     # くず石（ほっても 資材に ならない。鉄の まわりに ある）
    'cloud':  color.hex('#f4f6ff'),     # 雲（ほれるけど 資材に ならない）
    'gold':   color.hex('#ffd24a'),     # 天国の 床（ほれない）
    'chest':  color.hex('#c08040'),     # 宝箱（鍵が 入っている）
}
NAME = {'wood': '木', 'stone': '石', 'iron': '鉄', 'rubble': 'くず石', 'cloud': '雲', 'chest': '宝箱'}
MATERIALS = ['wood', 'stone', 'iron']
UNBREAKABLE = ('ground', 'gold')
CRYSTAL_COLORS = [color.hex(c) for c in ('#8f6bff', '#4fd6ff', '#ff6bd6', '#6bffd0')]


def area_at(height):
    """その 高さの エリアを 返す"""
    area = AREAS[0]
    for a in AREAS:
        if height >= a[0]:
            area = a
    return area


# ============================================================
# ③ ブロック
#    blocks という 辞書に「(x, y, z) → ブロック」を 入れて おぼえておく
# ============================================================
blocks = {}


def make_shaded_cube():
    """面ごとに 明るさを 決めた 立方体（上の面が いちばん 明るく、下の面も 真っ暗に ならない）
       → 見上げても 見下ろしても、ブロックの 形と さかい目が 分かる"""
    s = 0.5
    faces = [   # (4つの 角, 明るさ)
        ([(-s, s, -s), (-s, s, s), (s, s, s), (s, s, -s)], 1.00),      # 上
        ([(-s, -s, -s), (s, -s, -s), (s, -s, s), (-s, -s, s)], 0.68),  # 下
        ([(s, -s, -s), (s, s, -s), (s, s, s), (s, -s, s)], 0.86),      # 右
        ([(-s, -s, -s), (-s, -s, s), (-s, s, s), (-s, s, -s)], 0.80),  # 左
        ([(-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)], 0.76),      # 奥
        ([(-s, -s, -s), (-s, s, -s), (s, s, -s), (s, -s, -s)], 0.92),  # 手前
    ]
    verts, tris, uvs, cols = [], [], [], []
    for corners, light in faces:
        n = len(verts)
        verts += corners
        tris += [n, n + 1, n + 2, n, n + 2, n + 3]
        uvs += [(0, 0), (0, 1), (1, 1), (1, 0)]
        cols += [Vec4(light, light, light, 1)] * 4
    return Mesh(vertices=verts, triangles=tris, uvs=uvs, colors=cols)


class Block(Entity):
    def __init__(self, position, kind, placed=False):
        c = lerp(color.white, color.gray, random.uniform(0, 0.25))   # 少しずつ 明るさを 変えると 自然に 見える
        super().__init__(model=make_shaded_cube(), texture=TEXTURES[kind], position=position, color=c,
                         collider='box', double_sided=True)
        self.key = position                             # 辞書の キー (x, y, z)
        self.kind = kind
        self.placed = placed                            # 自分で 置いた ブロックなら True
        blocks[position] = self
        if not placed:
            self.decorate(area_at(position[1])[1])

    def decorate(self, area):
        """自然の ブロックに、エリアらしい かざりを つける（子どもの Entity なので、ほると いっしょに 消える）"""
        if area == '洞窟' and self.kind in ('stone', 'iron', 'rubble') and random.random() < 0.15:
            for _ in range(random.randint(1, 3)):     # 光る 結晶
                Entity(parent=self, model='diamond', color=random.choice(CRYSTAL_COLORS),
                       position=(random.uniform(-0.3, 0.3), 0.62, random.uniform(-0.3, 0.3)),
                       scale=(0.14, random.uniform(0.3, 0.55), 0.14),
                       rotation=(random.uniform(-25, 25), random.uniform(0, 90), random.uniform(-25, 25)))
        elif area == '森' and self.kind in ('stone', 'wood', 'rubble') and random.random() < 0.55:
            Entity(parent=self, model='cube', color=color.hex(random.choice(('#4f9a4a', '#5fae52', '#3f8a44'))),
                   position=(0, 0.47, 0), scale=(1.03, 0.08, 1.03))          # こけ
            if random.random() < 0.3:                   # たれさがる ツタ
                Entity(parent=self, model='cube', color=color.hex('#3f8a44'),
                       position=(random.uniform(-0.4, 0.4), -0.2, random.choice((-0.52, 0.52))),
                       scale=(0.08, random.uniform(0.8, 1.6), 0.02))


def add_block(x, y, z, kind, placed=False):
    if (x, y, z) not in blocks:
        Block((x, y, z), kind, placed)


def aimed_block():
    """マウス（画面の まんなか）が ねらっている、手の とどく ブロック。なければ None"""
    t = mouse.hovered_entity
    if not isinstance(t, Block) or blocks.get(t.key) is not t:   # こわした すぐあとの ブロックは 使わない
        return None
    if distance(Vec3(*t.key), camera.world_position) > REACH:
        return None
    return t


def remove_block(pos):
    b = blocks.pop(pos, None)
    if b:
        destroy(b)


def surround(x, y, z, kind='rubble'):
    """(x, y, z) の まわり 6方向を くず石で 囲う（もう ブロックが ある 所は そのまま）"""
    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        nx, ny, nz = x + dx, y + dy, z + dz
        if abs(nx) <= HALF and abs(nz) <= HALF and 1 <= ny < GOAL:
            add_block(nx, ny, nz, kind)


def add_resource(x, y, z, height):
    """資材の ブロックを 置く。鉄（大事な 鉱石）なら、まわりを くず石で 囲う"""
    kind = random_resource(height)
    add_block(x, y, z, kind)
    if kind == 'iron':
        surround(x, y, z)


def random_resource(height):
    """その 高さに 合った 資材を 1つ 決める（上に 行くほど 鉄が 多い）"""
    rate = area_at(height)[3]
    x = random.random()
    if x < rate['iron']:
        return 'iron'
    if x < rate['iron'] + rate['stone']:
        return 'stone'
    return 'wood'


def make_chest(y):
    """かべの 中に 宝箱（鍵入り）を うめて、くず石で かくす"""
    i = random.randint(-HALF + 1, HALF - 1)
    x, z = random.choice(((i, -HALF), (i, HALF), (-HALF, i), (HALF, i)))
    remove_block((x, y, z))
    add_block(x, y, z, 'chest')
    surround(x, y, z)
    chests.append((x, y, z))


def make_layer(y):
    """高さ y の 1だんを 作る"""
    if y == 0:                                          # 地面
        for x in range(-HALF, HALF + 1):
            for z in range(-HALF, HALF + 1):
                add_block(x, 0, z, 'ground')
        return
    if y == GOAL:                                       # 天国の 床（金色）と 門
        for x in range(-HALF, HALF + 1):
            for z in range(-HALF, HALF + 1):
                if abs(x) == HALF or abs(z) == HALF or random.random() < 0.15:
                    add_block(x, y, z, 'gold')
        make_gate(y)
        return
    if y > GOAL:
        return
    # まわりの かべ（ところどころ。ほると 資材に なる）
    for i in range(-HALF, HALF + 1):
        for x, z in ((i, -HALF), (i, HALF), (-HALF, i), (HALF, i)):
            if random.random() < 0.3:
                add_resource(x, y, z, y)
    if y in g.key_heights:                              # 鍵の 宝箱
        make_chest(y)
    # 5だんごとに 浮き島
    if y % 5 == 0:
        cx, cz = random.randint(-2, 2), random.randint(-2, 2)
        size = random.randint(1, 2)
        cloud = area_at(y)[1] == '空' and random.random() < 0.5
        for x in range(cx - size, cx + size):
            for z in range(cz - size, cz + size):
                if cloud:
                    add_block(x, y, z, 'cloud')
                else:
                    add_resource(x, y, z, y)
        if random.random() < 0.25:                      # ときどき 回復の実
            berries.append(Entity(model='sphere', color=color.hex('#e83c5a'), scale=0.45,
                                  position=(cx, y + 0.8, cz)))
    # 2だんごとに たて穴の 外の けしき
    if y % 2 == 0:
        make_scenery(y)
    if y == 96:
        make_rainbow(y)


# たて穴の 外に 出られないように する 見えない かべ
for x, z, sx, sz in ((HALF + 1, 0, 1, HALF * 2 + 3), (-HALF - 1, 0, 1, HALF * 2 + 3),
                     (0, HALF + 1, HALF * 2 + 3, 1), (0, -HALF - 1, HALF * 2 + 3, 1)):
    Entity(model='cube', position=(x, 500, z), scale=(sx, 1000, sz), collider='box', visible=False)


# ============================================================
# ④ けしき（さわれない かざり。かべの すきまから 見える）
# ============================================================
scenery = []                                            # (高さ, かざり) の リスト。溶岩に しずんだら 消す


def deco(y, **kw):
    e = Entity(**kw)
    scenery.append((y, e))
    return e


def outside_point(near=3, far=10):
    """たて穴の 外の、少し はなれた 場所 (x, z)"""
    side = random.choice((-1, 1))
    d = random.uniform(HALF + near, HALF + far)
    a = random.uniform(-HALF - far, HALF + far)
    return (side * d, a) if random.random() < 0.5 else (a, side * d)


def make_scenery(y):
    area = area_at(y)[1]
    if area == '洞窟':
        # 遠くの 岩かべ（洞窟の 中に いる 感じ）
        for _ in range(2):
            x, z = outside_point(9, 14)
            s = random.uniform(3, 6)
            deco(y, model=make_shaded_cube(), texture=TEXTURES['stone'], color=color.hex('#4a4060'),
                 position=(x, y + random.uniform(-1, 2), z), scale=(s, random.uniform(3, 7), s),
                 rotation=(0, random.uniform(0, 90), 0))
        # 光る 結晶の むれ
        x, z = outside_point(2, 7)
        for _ in range(random.randint(3, 5)):
            deco(y, model='diamond', color=random.choice(CRYSTAL_COLORS),
                 position=(x + random.uniform(-0.8, 0.8), y + random.uniform(0, 1), z + random.uniform(-0.8, 0.8)),
                 scale=(0.4, random.uniform(1.2, 2.8), 0.4),
                 rotation=(random.uniform(-30, 30), random.uniform(0, 90), random.uniform(-30, 30)))
        # 天井から たれる つらら
        if random.random() < 0.6:
            x, z = outside_point(2, 9)
            deco(y, model='diamond', color=color.hex('#6a6488'), position=(x, y + 5, z),
                 scale=(0.5, random.uniform(2, 4), 0.5))
        # 光る キノコ
        if random.random() < 0.5:
            x, z = outside_point(2, 6)
            deco(y, model='cube', color=color.hex('#d8d0e8'), position=(x, y + 0.4, z), scale=(0.15, 0.8, 0.15))
            deco(y, model='sphere', color=color.hex('#5ff2ff'), position=(x, y + 0.85, z), scale=(0.7, 0.3, 0.7))
    elif area == '森':
        # 大きな 木（みき と 葉っぱ）
        x, z = outside_point(3, 10)
        h = random.uniform(5, 9)
        deco(y, model=make_shaded_cube(), texture=TEXTURES['wood'], color=color.hex('#8a6040'),
             position=(x, y + h / 2, z), scale=(0.9, h, 0.9))
        for _ in range(3):
            deco(y, model=make_shaded_cube(), color=color.hex(random.choice(('#3f8a44', '#4f9a4a', '#5fae52'))),
                 position=(x + random.uniform(-1, 1), y + h + random.uniform(-0.8, 0.8), z + random.uniform(-1, 1)),
                 scale=(random.uniform(2, 3.2), random.uniform(1.4, 2.2), random.uniform(2, 3.2)))
        # 木もれ日の 光の 柱
        if random.random() < 0.4:
            x, z = outside_point(1, 6)
            e = deco(y, model='cube', color=color.hex('#fff2a8'), position=(x, y + 4, z),
                     scale=(0.6, 10, 0.6), rotation=(0, 0, random.uniform(-15, 15)))
            e.alpha = 0.12
        # 光る キノコ
        if random.random() < 0.4:
            x, z = outside_point(2, 6)
            deco(y, model='cube', color=color.hex('#f2ead8'), position=(x, y + 0.3, z), scale=(0.15, 0.6, 0.15))
            deco(y, model='sphere', color=color.hex('#ffb04a'), position=(x, y + 0.65, z), scale=(0.6, 0.25, 0.6))
    elif area == '空':
        # 流れていく 雲
        x, z = outside_point(3, 12)
        cloud = deco(y, position=(x, y + random.uniform(0, 2), z))
        for _ in range(3):
            Entity(parent=cloud, model='cube', color=color.white,
                   position=(random.uniform(-1.5, 1.5), random.uniform(-0.2, 0.3), random.uniform(-1, 1)),
                   scale=(random.uniform(2, 4), random.uniform(0.6, 1.0), random.uniform(1.5, 3)))
        cloud.mover = 'cloud'
        cloud.speed = random.uniform(0.3, 0.8)
        # うかぶ 島
        if random.random() < 0.35:
            x, z = outside_point(6, 12)
            deco(y, model=make_shaded_cube(), color=color.hex('#5fae52'), position=(x, y + 1, z), scale=(3, 0.4, 3))
            deco(y, model=make_shaded_cube(), texture=TEXTURES['stone'], color=color.hex('#9a8670'),
                 position=(x, y + 0.2, z), scale=(2.4, 1.4, 2.4))
        # 鳥の むれ（たて穴の まわりを 回る）
        if random.random() < 0.25:
            flock = deco(y, position=(0, y + 3, 0))
            for i in range(3):
                Entity(parent=flock, model='cube', color=color.hex('#2a2a36'),
                       position=(i * 0.8, 0, -abs(i - 1) * 0.6), scale=(0.5, 0.06, 0.15))
            flock.mover = 'bird'
            flock.angle = random.uniform(0, 360)
            flock.radius = random.uniform(9, 13)
    else:
        # 天国の 金の 柱と 光の 玉
        x, z = outside_point(3, 10)
        deco(y, model=make_shaded_cube(), texture=TEXTURES['gold'], position=(x, y + 2, z), scale=(0.8, 4, 0.8))
        deco(y, model='sphere', color=color.hex('#fff8e0'), position=(x, y + 4.4, z), scale=0.6)
        if random.random() < 0.5:
            x, z = outside_point(2, 8)
            orb = deco(y, model='sphere', color=color.hex('#fffbe8'), position=(x, y + 1.5, z), scale=0.35)
            orb.mover = 'bob'
            orb.base_y = orb.y


def make_rainbow(y):
    """天国の 入り口に かかる 虹（小さな 箱を 半円に ならべる）"""
    for i, c in enumerate(('#ff5a5a', '#ffa94a', '#ffe14a', '#6fe36f', '#4fb6ff', '#9b6bff')):
        r = 13 - i * 0.45
        for k in range(15):
            a = math.pi * k / 14
            e = deco(y, model='cube', color=color.hex(c), position=(math.cos(a) * r, y + math.sin(a) * r * 0.6, HALF + 8),
                     scale=(1.1, 0.45, 0.3), rotation=(0, 0, -math.degrees(a) + 90))
            e.alpha = 0.7


def make_gate(y):
    """天国の 門（2本の 柱と 横の はり）"""
    for x in (-2, 2):
        deco(y, model=make_shaded_cube(), texture=TEXTURES['gold'], position=(x, y + 2.5, 0), scale=(0.6, 4, 0.6))
    deco(y, model='cube', color=color.hex('#fff1b8'), position=(0, y + 4.7, 0), scale=(5.2, 0.5, 0.8))
    deco(y, model='sphere', color=color.hex('#ffffff'), position=(0, y + 5.6, 0), scale=1.0)


def update_scenery(dt):
    """動く かざり（雲・鳥・光の玉）を 動かす"""
    for _, e in scenery:
        kind = getattr(e, 'mover', None)
        if kind == 'cloud':
            e.x += e.speed * dt
            if e.x > HALF + 14:
                e.x = -HALF - 14
        elif kind == 'bird':
            e.angle += 20 * dt
            a = math.radians(e.angle)
            e.x, e.z = math.cos(a) * e.radius, math.sin(a) * e.radius
            e.rotation_y = -e.angle
            for i, w in enumerate(e.children):
                w.rotation_z = math.sin(time.time() * 10 + i) * 25
        elif kind == 'bob':
            e.y = e.base_y + math.sin(time.time() * 1.5 + e.x) * 0.4


# まわりを ただよう 光の粒（エリアで 変わる: 洞窟=ホタル、森=葉っぱ、空=風のつぶ、天国=光）
motes = []
for _ in range(36):
    m = Entity(model='quad', billboard=True, scale=0.08)
    m.life = 0
    m.v = Vec3(0, 0, 0)
    m.phase = random.uniform(0, 6)
    motes.append(m)


def respawn_mote(m, area):
    m.position = player.position + Vec3(random.uniform(-7, 7), random.uniform(-2, 8), random.uniform(-7, 7))
    m.life = random.uniform(3, 7)
    if area == '洞窟':
        m.color = random.choice(CRYSTAL_COLORS)
        m.scale = random.uniform(0.06, 0.12)
        m.v = Vec3(random.uniform(-0.3, 0.3), random.uniform(-0.1, 0.3), random.uniform(-0.3, 0.3))
    elif area == '森':
        m.color = color.hex(random.choice(('#7fcf5a', '#b4d84a', '#e8a040')))
        m.scale = 0.14
        m.v = Vec3(random.uniform(-0.3, 0.3), -0.6, random.uniform(-0.3, 0.3))
    elif area == '空':
        m.color = color.white
        m.scale = (0.4, 0.03)
        m.v = Vec3(3, 0, random.uniform(-0.3, 0.3))
    else:
        m.color = color.hex('#ffe7a0')
        m.scale = random.uniform(0.05, 0.1)
        m.v = Vec3(0, random.uniform(0.4, 0.9), 0)


def update_motes(dt, area):
    for m in motes:
        m.life -= dt
        if m.life <= 0 or distance(m.position, player.position) > 12:
            respawn_mote(m, area)
        m.position += m.v * dt
        if area == '森':
            m.x += math.sin(time.time() * 2 + m.phase) * 0.5 * dt   # ひらひら
        m.alpha = 0.35 + 0.35 * math.sin(time.time() * 3 + m.phase)


# ============================================================
# ⑤ プレイヤーと 画面の 文字
# ============================================================
player = FirstPersonController(position=(0, 1, 0), speed=6, jump_height=2.2)
player.enabled = False

lava = Entity(model='cube', color=color.hex('#ff5a14'), scale=(HALF * 2 + 3, 60, HALF * 2 + 3))
LAVA_COLORS = (color.hex('#ff4a10'), color.hex('#ffa030'))           # 溶岩の 色（2色の あいだで ゆらめく）
highlight = Entity(model='cube', color=color.white, scale=1.02)      # ねらっている ブロックの 印
highlight.alpha = 0.25
# ほっている ときの 進み具合バー（画面の まん中の 少し下）
mine_back = Entity(parent=camera.ui, model='quad', position=(0, -0.09), scale=(0.18, 0.014), color=color.black, enabled=False)
mine_back.alpha = 0.55
mine_fill = Entity(parent=camera.ui, model='quad', origin=(-0.5, 0), position=(-0.09, -0.09), scale=(0.001, 0.014),
                   color=color.hex('#ffd24a'), enabled=False)
mine_label = Text(position=(0, -0.055), origin=(0, 0), scale=0.9, enabled=False)
hand = Entity(parent=camera, model=make_shaded_cube(), position=(0.62, -0.5, 1.5),
              scale=0.22, rotation=(10, -25, 0))                     # 手に 持っている ブロック
# 左手の 剣（刃・つば・にぎり）
sword = Entity(parent=camera, position=(-0.55, -0.42, 1.25), rotation=(25, 20, -15))
Entity(parent=sword, model='cube', color=color.hex('#dfe8f2'), position=(0, 0.33, 0), scale=(0.05, 0.55, 0.015))
Entity(parent=sword, model='cube', color=color.hex('#c9a227'), scale=(0.2, 0.04, 0.05))
Entity(parent=sword, model='cube', color=color.hex('#5a3a22'), position=(0, -0.1, 0), scale=(0.045, 0.16, 0.045))

height_text = Text(position=(-0.86, 0.47), scale=1.6)
hp_text = Text(position=(-0.86, 0.41), scale=1.4, color=color.hex('#ff6a80'))
item_text = Text(position=(0.3, 0.47), scale=1.3)
jet_text = Text(position=(0.3, 0.42), scale=1.0, color=color.hex('#bfe3ff'))
coin_text = Text(position=(0.3, 0.385), scale=1.0, color=color.hex('#ffd24a'))
radar_text = Text(position=(0, 0.36), origin=(0, 0), scale=1.4, color=color.hex('#ffe680'))
lava_text = Text(position=(0, -0.42), origin=(0, 0), scale=1.6)
message_text = Text(position=(0, -0.34), origin=(0, 0), scale=1.2)
warn_text = Text(text='溶岩の 波が 来る！ 上へ にげろ！', position=(0, 0.25), origin=(0, 0),
                 scale=2.5, color=color.hex('#ff5028'), enabled=False)
# 右はしの 「天国まで あと どれくらい」バー
bar_back = Entity(parent=camera.ui, model='quad', position=(0.84, 0), scale=(0.018, 0.6), color=color.hex('#000000'))
bar_back.alpha = 0.5
bar_fill = Entity(parent=camera.ui, model='quad', origin=(0, -0.5), position=(0.84, -0.3), scale=(0.018, 0.001), color=color.hex('#ffd24a'))
bar_lava = Entity(parent=camera.ui, model='quad', position=(0.84, -0.3), scale=(0.03, 0.006), color=color.hex('#ff5a14'))
lava_glow = Entity(parent=camera.ui, model='quad', scale=(2, 1), color=color.hex('#ff5a14'))   # 溶岩が 近いと 画面が 赤く
lava_glow.alpha = 0
hurt_flash = Entity(parent=camera.ui, model='quad', scale=(2, 1), color=color.red)
hurt_flash.alpha = 0
panel = Entity(parent=camera.ui, model='quad', scale=(1.45, 0.8), position=(0, 0.04), color=color.black)
panel.alpha = 0.6                                                     # 文字の うしろの 黒い 板
big_text = Text(position=(0, 0.3), origin=(0, 0), scale=3)
sub_text = Text(position=(0, 0.04), origin=(0, 0), scale=1.2)
hud = [height_text, hp_text, item_text, jet_text, coin_text, radar_text, lava_text,
       bar_back, bar_fill, bar_lava, hand, sword]


class State:
    """ゲームの 状態を まとめた 箱"""
    pass


g = State()
g.diff = 1                                              # むずかしさ（DIFFICULTIES の 番号）
g.key_heights = []


def say(text, time=2.5):
    message_text.text = text
    g.message_time = time


def load_best():
    try:
        with open(BEST_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_best(data):
    try:
        with open(BEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


# ============================================================
# ⑥ 落石・敵・剣・回復の実・ジェット機・真下に積む・小さな 演出
# ============================================================
rocks = []
berries = []
sparks = []                                             # こわした ときの かけら
enemies = []
chests = []                                             # 鍵の 宝箱が ある 場所 (x, y, z)


class Rock(Entity):
    """上から 落ちてくる 石。地面に 影が 出るので、どこに 落ちるか わかる"""

    def __init__(self, x, y, z):
        super().__init__(model='sphere', color=color.hex('#5a504c'), scale=0.7, position=(x, y, z))
        self.speed = 0
        hit = raycast((x, y, z), (0, -1, 0), distance=60, ignore=(self, player))
        self.land_y = hit.world_point.y if hit.hit else y - 60
        self.target = hit.entity if hit.hit else None
        self.shadow = Entity(model='quad', rotation_x=90, color=color.black, scale=0.8,
                             position=(x, self.land_y + 0.03, z))
        self.shadow.alpha = 0.5

    def fall(self):
        """落ちる。地面に とどいたら True を 返す"""
        self.speed += 15 * time.dt
        self.y -= self.speed * time.dt
        if self.y - 0.35 <= self.land_y:
            t = self.target
            if isinstance(t, Block) and blocks.get(t.key) is t and t.placed and t.kind != 'iron':
                remove_block(t.key)                      # 置いた 木・石は こわれる（鉄は だいじょうぶ）
            burst(self.position, color.hex('#5a504c'), 5)
            destroy(self.shadow)
            return True
        return False


class Enemy(Entity):
    """エリアごとの 弱い敵。さわると HP -1。剣で たおすと コイン"""

    def __init__(self, area, pos):
        name, hp, speed, coins, move, col = ENEMY_TYPES[area]
        fly = move == 'fly'
        super().__init__(model='sphere' if fly else 'cube', color=color.hex(col), position=pos,
                         scale=0.55 if fly else 0.6)
        self.base_color = self.color
        self.name, self.hp, self.speed, self.coins, self.move = name, hp, speed, coins, move
        self.vy = 0
        self.vx = Vec3(0, 0, 0)                         # 横の 速さ（はねる敵）
        self.hop_wait = 1.0
        self.kb = Vec3(0, 0, 0)                         # はじかれた ときの 速さ
        self.flash = 0
        self.rest = 0                                   # 0 より 大きい あいだは はなれていく（当たらない）
        self.mode = 'chase'                             # 飛ぶ敵: chase（追う）→ windup（ためる）→ dash（突進）
        self.phase = random.uniform(0, 6)
        for x in (-0.18, 0.18):                         # 目
            Entity(parent=self, model='cube', color=color.white, position=(x, 0.12, -0.45), scale=(0.2, 0.22, 0.05))
            Entity(parent=self, model='cube', color=color.black, position=(x, 0.1, -0.48), scale=(0.09, 0.12, 0.05))
        self.wings = []
        if fly:                                         # つばさ
            for side in (-1, 1):
                w = Entity(parent=self, model='cube', color=self.color, position=(side * 0.7, 0.05, 0),
                           scale=(0.9, 0.06, 0.45))
                w.side = side
                self.wings.append(w)
        if area == '天国':                              # 天使の わっか
            Entity(parent=self, model='cube', color=color.hex('#ffd24a'), position=(0, 0.75, 0), scale=(0.6, 0.06, 0.6))

    def step(self, dt):
        target = player.position + Vec3(0, 1.0, 0)
        to = target - self.position
        self.look_at_2d(player.position, 'y')
        self.rotation_y += 180                          # 目の ある 面を プレイヤーに 向ける
        if self.rest > 0:                               # 当たったあとは はなれる
            self.rest -= dt
            to = -to
        if self.move == 'fly':
            t = time.time() * 2.5 + self.phase
            wobble = Vec3(math.sin(t), math.sin(t * 0.9) * 0.6, math.cos(t)) * 0.8
            if self.rest > 0:
                self.mode = 'chase'
                self.position += (to.normalized() * self.speed + wobble) * dt
            elif self.mode == 'chase':
                self.position += (to.normalized() * self.speed + wobble) * dt
                if to.length() < 2.4:                   # 近づいたら 止まって ためる
                    self.mode, self.timer = 'windup', ENEMY_WINDUP
                    self.color = color.hex('#ff4040')
            elif self.mode == 'windup':
                self.timer -= dt
                self.position += Vec3(random.uniform(-1, 1), 0, random.uniform(-1, 1)) * dt   # ぶるぶる
                if self.timer <= 0:
                    self.mode, self.timer = 'dash', 0.45
                    self.dash_v = to.normalized() * self.speed * 4
                    self.color = self.base_color
            else:                                       # 突進（このときだけ 当たる）
                self.timer -= dt
                self.position += self.dash_v * dt
                if self.timer <= 0:
                    self.mode = 'chase'
                    self.rest = ENEMY_REST
            for w in self.wings:
                w.rotation_z = math.sin(time.time() * 18 + self.phase) * 35 * w.side
        else:
            self.vy -= 20 * dt
            ny = self.y + self.vy * dt
            cell = (round(self.x), math.floor(ny - 0.3 + 0.5), round(self.z))
            if self.vy <= 0 and cell in blocks:         # ブロックの 上に 着地
                self.y = cell[1] + 0.5 + 0.3
                self.vy = 0
                self.vx = Vec3(0, 0, 0)
                self.hop_wait -= dt
                if self.hop_wait <= 0:                  # プレイヤーの ほうへ ぴょん
                    self.hop_wait = random.uniform(0.6, 1.2)
                    self.vy = 7 if to.y > -1 else 4
                    flat = Vec3(to.x, 0, to.z)
                    self.vx = flat.normalized() * self.speed if flat.length() > 0.1 else Vec3(0, 0, 0)
            else:
                self.y = ny
            self.position += self.vx * dt
            self.x = max(-HALF + 0.5, min(HALF - 0.5, self.x))
            self.z = max(-HALF + 0.5, min(HALF - 0.5, self.z))
            self.scale_y = 0.6 * (1.15 if self.vy > 0 else 0.9)   # ぷにぷに
        self.position += self.kb * dt
        self.kb *= max(0, 1 - 6 * dt)
        if self.flash > 0:
            self.flash -= dt
            if self.flash <= 0:
                self.color = self.base_color


def spawn_enemy():
    area = area_at(height())[1]
    if ENEMY_TYPES[area][4] == 'fly':
        a = random.uniform(0, math.pi * 2)
        pos = (math.cos(a) * 4, player.y + random.uniform(3, 6), math.sin(a) * 4)
    else:
        pos = (random.randint(-HALF + 1, HALF - 1), player.y + random.uniform(3, 5), random.randint(-HALF + 1, HALF - 1))
    enemies.append(Enemy(area, pos))


def kill_enemy(e):
    burst(e.position, e.base_color, 8)
    g.coins += e.coins
    g.kills += 1
    sfx('coin')
    say(f'{e.name}を たおした！  コイン +{e.coins}', 1.5)
    enemies.remove(e)
    destroy(e)


def swing_sword():
    """剣を ふる。前に いる 敵（とどく きょり・前の 方向）に ダメージ"""
    if g.swing_wait > 0:
        return
    g.swing_wait = SWORD_WAIT
    g.swing = 0.25
    sfx('swing')
    fwd = camera.forward
    for e in enemies[:]:
        d = e.position - camera.world_position
        if d.length() < 1.2 or (d.length() < SWORD_REACH and d.normalized().dot(fwd) > 0.45):
            e.hp -= 1
            e.color = color.white
            e.flash = 0.1
            e.kb = Vec3(fwd.x, 0.3, fwd.z) * 6
            e.rest = 1.0
            sfx('hit')
            if e.hp <= 0:
                kill_enemy(e)


def enemy_in_aim():
    """画面の まんなかで ねらっている 敵（剣が とどく）が いれば True"""
    fwd = camera.forward
    for e in enemies:
        d = e.position - camera.world_position
        if d.length() < SWORD_REACH + 0.5 and d.normalized().dot(fwd) > 0.85:
            return True
    return False


def burst(pos, col, n=6):
    """小さな かけらを とびちらせる（演出）"""
    for _ in range(n):
        e = Entity(model='cube', color=col, scale=0.15, position=pos)
        e.v = Vec3(random.uniform(-3, 3), random.uniform(2, 5), random.uniform(-3, 3))
        e.life = 0.5
        sparks.append(e)


def update_sparks(dt):
    for e in sparks[:]:
        e.v.y -= 15 * dt
        e.position += e.v * dt
        e.life -= dt
        e.scale = max(0.01, e.life * 0.3)
        if e.life <= 0:
            sparks.remove(e)
            destroy(e)


def show_mining(on, block=None, rate=0):
    """ほっている 進み具合を 画面に 出す（on=False で 消す）"""
    mine_back.enabled = mine_fill.enabled = mine_label.enabled = on
    if on:
        mine_fill.scale_x = max(0.001, 0.18 * rate)
        mine_label.text = f'{NAME[block.kind]}  かたさ {HARDNESS[block.kind]}秒'


def mine(target):
    """ブロックを ほりおえた ときに よぶ"""
    if target.kind == 'chest':                          # 鍵を 見つけた！
        g.keys += 1
        if target.key in chests:
            chests.remove(target.key)
        sfx('key')
        say(f'鍵を 見つけた！ ({g.keys}/3)' + ('  全部 そろった！ 天国へ 行こう！' if g.keys == 3 else ''), 4)
    elif target.kind in g.items:
        g.items[target.kind] += 1
    else:                                               # くず石・雲は 資材に ならない
        say(f'{NAME[target.kind]}は 資材に ならない', 1.2)
    burst(target.key, BLOCK_COLOR[target.kind])
    sfx('mine')
    remove_block(target.key)


def hurt(cause):
    """ダメージを 受ける。cause は 'rock' / 'enemy'（ゲームオーバーの ヒントに 使う）"""
    if g.invincible > 0 or g.god:
        return
    g.invincible = 1.5
    if g.shield:                                        # シールドで 1回 ふせぐ
        g.shield = False
        say('シールドで ふせいだ！', 1.5)
        sfx('pick')
        return
    g.hp -= 1
    g.last_hit = cause
    hurt_flash.alpha = 0.45
    sfx('hurt')


def ride_jet():
    if g.jet > 0:
        return
    if g.free_jet > 0:                                  # ジェット券が あれば 材料なしで
        g.free_jet -= 1
    elif any(g.items[k] < v for k, v in JET_COST.items()):
        say('ジェット機には 石 8 と 鉄 8 が いる（ショップの ジェット券でも OK）')
        return
    else:
        for k, v in JET_COST.items():
            g.items[k] -= v
    g.lift = None
    g.jet = JET_TIME
    player.gravity = 0                                  # 重力を 切って 上へ
    g.placed += 10
    sfx('jet')
    say('ジェット機で 一気に 上へ！')


def end_jet():
    """ジェット機が 終わったら、ブロックの 中なら 上へ 出して、足の下に 石の 足場を 作る"""
    land_safely()


def land_safely():
    """ブロックの 中なら 上へ 出して、足の下に 石の 足場（3×3）を 作る（ジェット機・ワープの あと）"""
    player.gravity = 1
    px, pz = round(player.x), round(player.z)
    y = round(player.y)
    while (px, y, pz) in blocks or (px, y + 1, pz) in blocks:
        y += 1
    player.y = y - 0.5
    for x in range(px - 1, px + 2):
        for z in range(pz - 1, pz + 2):
            if abs(x) < HALF and abs(z) < HALF:
                add_block(x, y - 1, z, 'stone', placed=True)


def pillar():
    """自分の 真下に ブロックを 積んで、体を 1だん 上げる（Q キー）
       足の ある マス に ブロックを 置き、体は その 上まで すっと 上がる"""
    if g.lift is not None or g.pillar_wait > 0 or g.jet > 0:
        return
    px, pz = round(player.x), round(player.z)
    if abs(px) > HALF or abs(pz) > HALF:
        return
    feet = math.floor(player.y + 0.5)                   # 足が ある マスの 高さ
    if (px, feet, pz) in blocks or (px, feet + 2, pz) in blocks:
        say('頭の 上が つまっていて 積めない', 1)
        g.pillar_wait = 0.5
        return
    mat = MATERIALS[g.mat]
    if g.items[mat] < 1:                                # えらんだ 材料が なければ、ほかの 材料を 使う
        others = [m for m in ('stone', 'wood', 'iron') if g.items[m] > 0]
        if not others:
            say('材料が ない。かべを ほって あつめよう', 1.5)
            g.pillar_wait = 0.5
            return
        mat = others[0]
    g.items[mat] -= 1
    g.lift = (feet + 0.5, px, pz, mat, feet)
    g.pillar_wait = PILLAR_WAIT
    player.gravity = 0


def update_lift(dt):
    """pillar() で 上がっている とちゅう。上まで 着いたら ブロックを 置く"""
    target, px, pz, mat, feet = g.lift
    player.y = min(target, player.y + PILLAR_SPEED * dt)
    player.x = lerp(player.x, px, min(1, 15 * dt))     # マスの まんなかへ よせる
    player.z = lerp(player.z, pz, min(1, 15 * dt))
    if player.y >= target:
        add_block(px, feet, pz, mat, placed=True)
        g.placed += 1
        sfx('place')
        player.gravity = 1
        if hasattr(player, 'air_time'):
            player.air_time = 0                         # 落ちる いきおいを リセット
        g.lift = None


def key_direction():
    """いちばん 近い 宝箱の 方向を 矢印と 高さで 返す（鍵さがし）"""
    if not chests:
        return '近くに 鍵は ない'
    c = min(chests, key=lambda p: distance(Vec3(*p), player.position))
    dx, dz = c[0] - player.x, c[2] - player.z
    rel = (math.degrees(math.atan2(dx, dz)) - player.rotation_y) % 360
    arrow = '↑↗→↘↓↙←↖'[round(rel / 45) % 8]
    dy = c[1] - height()
    return f'鍵の 方向 {arrow}   {"上" if dy >= 0 else "下"} {abs(dy)}m'


# ============================================================
# ⑦ ゲームの 流れ
# ============================================================
def new_game():
    """世界を 作りなおして、タイトル画面に する"""
    for pos in list(blocks):
        remove_block(pos)
    for e in rocks + berries + sparks + enemies + [e for _, e in scenery]:
        if isinstance(e, Rock):
            destroy(e.shadow)
        destroy(e)
    rocks.clear()
    berries.clear()
    sparks.clear()
    enemies.clear()
    scenery.clear()
    chests.clear()
    name, mult, delay, items = DIFFICULTIES[g.diff]
    g.state = 'title'
    g.time = 0
    g.hp = MAX_HP
    g.invincible = 0
    g.items = dict(items)
    g.mat = 0
    g.placed = 0
    g.best = 0
    g.top_layer = -1
    g.lava_y = -6.0
    g.wave = None
    g.wave_t = 0
    g.wave_timer = random.uniform(*WAVE_INTERVAL)
    g.rock_timer = ROCK_INTERVAL
    g.jet = 0
    g.message_time = 0
    g.area_idx = 0
    g.mine_block = None                                 # いま ほっている ブロック
    g.mine_t = 0                                        # ほりはじめてからの 時間
    g.lift = None                                       # Q で 上がっている とちゅうの 情報
    g.pillar_wait = 0
    g.coins = 0
    g.kills = 0
    g.keys = 0
    g.key_heights = [random.randint(a, b) for _, a, b in KEY_RANGES]
    g.enemy_timer = ENEMY_FIRST
    g.swing = 0
    g.swing_wait = 0
    g.shield = False
    g.lava_stop = 0
    g.radar = 0
    g.free_jet = 0
    g.last_hit = 'lava'
    g.god = False                                       # デバッグ: 無敵
    g.debug_lava = False                                # デバッグ: 溶岩を 止める
    g.debug_info = False                                # デバッグ: 情報を 表示
    player.position = (0, 1, 0)
    player.rotation = (0, 0, 0)
    player.gravity = 1
    generate()
    show_title()


def show_title():
    best = load_best()
    lines = []
    for i, (name, *_) in enumerate(DIFFICULTIES):
        mark = '▶ ' if i == g.diff else '   '
        lines.append(f'{mark}{i + 1}. {name}   ベスト {best.get(name, 0)}')
    big_text.text = 'LAVA CRAFT 3D' + ('  [デバッグ]' if DEBUG else '')
    big_text.color = color.hex('#ffc850')
    sub_text.text = ('～ 天国まで 逃げろ！ ～   かべの 奥に 鍵が 3つ…？\n\n' + '\n'.join(lines) +
                     '\n\n1 / 2 / 3 で むずかしさを えらんで、クリック か Enter で スタート\n\n'
                     'WASD 移動 ・ 左クリック長押し ほる ・ 右クリック 置く ・ Q 真下に 積む\n'
                     'F 剣 ・ B ショップ ・ C ジェット機 ・ F11 全画面')
    camera.background_color = AREAS[0][2]
    show_mining(False)
    big_text.enabled = sub_text.enabled = panel.enabled = True
    for e in hud:
        e.enabled = False


def start():
    g.state = 'play'
    big_text.enabled = sub_text.enabled = panel.enabled = False
    for e in hud:
        e.enabled = True
    player.enabled = True
    mouse.locked = True
    name, mult, delay, items = DIFFICULTIES[g.diff]
    say(f'むずかしさ: {name}。溶岩が 動きだす 前に 資材を あつめよう！  Q で 真下に 積める', 5)


def generate():
    """プレイヤーの 少し上まで だんを 作り、溶岩に しずんだ だんは 消す（軽くするため）"""
    while g.top_layer < min(player.y + 16, GOAL):
        g.top_layer += 1
        make_layer(g.top_layer)
    for pos in [p for p in blocks if p[1] < g.lava_y - 4]:
        remove_block(pos)
    for c in [c for c in chests if c[1] < g.lava_y - 4]:
        chests.remove(c)
    for b in [b for b in berries if b.y < g.lava_y]:
        berries.remove(b)
        destroy(b)
    for item in [s for s in scenery if s[0] < g.lava_y - 8]:
        scenery.remove(item)
        destroy(item[1])


def height():
    return max(0, round(player.y - 0.5))


def finish(result):
    g.state = result
    player.enabled = False
    player.gravity = 1
    g.lift = None
    mouse.locked = False
    for e in hud:
        e.enabled = False
    show_mining(False)
    warn_text.enabled = False
    lava_glow.alpha = 0
    name = DIFFICULTIES[g.diff][0]
    true_end = result == 'clear' and g.keys == 3
    score = (int(g.time) + g.best * 10 + g.placed * 2 + g.kills * 20 + g.keys * 300
             + (500 if result == 'clear' else 0) + (1000 if true_end else 0))
    best = load_best()
    record = score > best.get(name, 0) and not DEBUG     # デバッグ中は 記録しない
    if record:
        best[name] = score
        save_best(best)
    if true_end:
        big_text.text = '真エンディング！'
        big_text.color = color.hex('#b8f0ff')
        head = '3つの 鍵で 天国の 宝物庫が ひらいた！\n\n'
        sfx('clear')
    elif result == 'clear':
        big_text.text = '天国に 着いた！'
        big_text.color = color.hex('#ffe678')
        head = f'鍵 {g.keys}/3 …… 全部 あつめると 何かが 起きるかも？\n\n'
        sfx('clear')
    else:
        big_text.text = 'ゲームオーバー'
        big_text.color = color.hex('#ff5a46')
        cause = g.last_hit if g.hp <= 0 else 'lava'
        words, hints = DEATH_HINTS[cause]
        head = f'{words}\nヒント: {random.choice(hints)}\n\n'
        sfx('over')
    sub_text.text = (head + f'むずかしさ: {name}\n'
                     f'時間 {int(g.time)} + 高さ {g.best}m×10 + 置いた数 {g.placed}×2 + 敵 {g.kills}×20 + 鍵 {g.keys}×300'
                     + (' + 天国 500' if result == 'clear' else '') + (' + 真エンド 1000' if true_end else '')
                     + f'\n\nスコア  {score}' + ('   ★ 新記録！' if record else f'   （ベスト {best.get(name, 0)}）')
                     + '\n\nR で もう一度   T で タイトルへ')
    big_text.enabled = sub_text.enabled = panel.enabled = True


# Esc の メニュー（授業の サンプルと 同じ しくみ）
menu_open = False
resume_button = Button(text='もどる', color=color.gray, scale=(0.3, 0.08), position=(0, -0.18), enabled=False)
quit_button = Button(text='やめる', color=color.red, scale=(0.3, 0.08), position=(0, -0.38), enabled=False)
quit_button.on_click = application.quit
full_button = Button(text='全画面 (F11)', color=color.azure, scale=(0.3, 0.08), position=(0, -0.28), enabled=False)


def toggle_fullscreen():
    """全画面 ⇔ ウィンドウ（ゲーム中は マウスが 固定されて ウィンドウの 拡大ボタンを おせないので キーで 切りかえる）"""
    window.fullscreen = not window.fullscreen


full_button.on_click = toggle_fullscreen


def open_menu():
    global menu_open
    menu_open = True
    player.enabled = False
    mouse.locked = False
    resume_button.enabled = quit_button.enabled = full_button.enabled = True


def close_menu():
    global menu_open
    menu_open = False
    resume_button.enabled = quit_button.enabled = full_button.enabled = False
    if g.state == 'play':
        player.enabled = True
        mouse.locked = True


resume_button.on_click = close_menu


# ショップ（B キー）: コインで お助けアイテムを 買う。開いている あいだは ゲームが 止まる
shop_open = False
shop_panel = Entity(parent=camera.ui, model='quad', scale=(1.1, 0.86), color=color.hex('#1a1426'), enabled=False)
shop_panel.alpha = 0.92
shop_title = Text(position=(0, 0.38), origin=(0, 0), scale=1.8, color=color.hex('#ffd24a'), enabled=False)
shop_buttons = []
for i, (item_name, price, desc, effect) in enumerate(SHOP_ITEMS):
    b = Button(text=f'{i + 1}. {item_name}  {price}コイン  … {desc}', scale=(0.98, 0.07),
               position=(0, 0.27 - i * 0.082), color=color.hex('#3a2f52'), enabled=False)
    b.text_entity.scale *= 0.85
    b.on_click = Func(lambda n=i: buy(n))
    shop_buttons.append(b)
shop_close = Button(text='とじる（B / Esc）', scale=(0.4, 0.07), position=(0, -0.36), color=color.gray, enabled=False)


def refresh_shop():
    shop_title.text = f'ショップ   コイン {g.coins}'
    for b, (item_name, price, desc, effect) in zip(shop_buttons, SHOP_ITEMS):
        b.color = color.hex('#3a6f52') if g.coins >= price else color.hex('#3a2f52')


def open_shop():
    global shop_open
    shop_open = True
    player.enabled = False
    mouse.locked = False
    for e in [shop_panel, shop_title, shop_close] + shop_buttons:
        e.enabled = True
    show_mining(False)
    refresh_shop()


def close_shop():
    global shop_open
    shop_open = False
    for e in [shop_panel, shop_title, shop_close] + shop_buttons:
        e.enabled = False
    if g.state == 'play':
        player.enabled = True
        mouse.locked = True


shop_close.on_click = close_shop


def buy(n):
    item_name, price, desc, effect = SHOP_ITEMS[n]
    if g.coins < price:
        say(f'コインが たりない（あと {price - g.coins}）', 1.5)
        return
    if effect == 'heal' and g.hp >= MAX_HP:
        say('HP は まんたん', 1.5)
        return
    g.coins -= price
    if effect == 'heal':
        g.hp += 1
    elif effect == 'pack':
        g.items['wood'] += 5
        g.items['stone'] += 5
    elif effect == 'iron':
        g.items['iron'] += 3
    elif effect == 'shield':
        g.shield = True
    elif effect == 'stop':
        g.lava_stop += 10
    elif effect == 'radar':
        g.radar = 40
    elif effect == 'jet':
        g.free_jet += 1
    sfx('buy')
    say(f'{item_name}を 買った！', 1.5)
    refresh_shop()


# デバッグ（テスト用の キー）: DEBUG が True の ときだけ 使える
debug_text = Text(position=(-0.86, 0.33), scale=0.9, color=color.hex('#9cff9c'), enabled=False)


def warp(h):
    """高さ h m へ ワープ（まわりの だんを 作ってから、安全な 足場に おろす）"""
    g.lift = None
    g.jet = 0
    player.y = min(h, GOAL - 1) + 0.5
    generate()
    land_safely()


def debug_key(key):
    if key == 'f1':
        for m in MATERIALS:
            g.items[m] += 50
        g.coins += 50
        g.hp = MAX_HP
        say('デバッグ: 資材・コイン +50、HP まんたん')
    elif key == 'f2':
        g.god = not g.god
        say('デバッグ: 無敵 ' + ('ON' if g.god else 'OFF'))
    elif key == 'f3':
        warp(height() + 10)
        say('デバッグ: 10m 上へ ワープ')
    elif key == 'f4':
        nxt = [a[0] for a in AREAS if a[0] > height()]
        warp(nxt[0] + 1 if nxt else GOAL - 2)
        say(f'デバッグ: {area_at(height())[1]}へ ワープ')
    elif key == 'f5':
        g.debug_lava = not g.debug_lava
        say('デバッグ: 溶岩 ' + ('ストップ' if g.debug_lava else 'うごく'))
    elif key == 'f6':
        spawn_enemy()
        say(f'デバッグ: {ENEMY_TYPES[area_at(height())[1]][0]}を 出した')
    elif key == 'f7':
        left = [h for h in g.key_heights if h > height() + 1]
        if left:
            warp(left[0])
            say(f'デバッグ: 鍵の 宝箱の 高さ {left[0]}m へ ワープ（かべを さがそう）')
        else:
            say('デバッグ: この上に 鍵は ない')
    elif key == 'f8':
        g.debug_info = not g.debug_info
        debug_text.enabled = g.debug_info


def update_debug_text():
    if not g.debug_info:
        return
    debug_text.text = (f'[デバッグ]  FPS {int(1 / max(time.dt, 0.001))}\n'
                       f'位置 ({player.x:.1f}, {player.y:.1f}, {player.z:.1f})  溶岩 {g.lava_y:.1f}\n'
                       f'ブロック {len(blocks)}  けしき {len(scenery)}  敵 {len(enemies)}\n'
                       f'鍵の 高さ {g.key_heights}  のこり宝箱 {[c[1] for c in chests]}\n'
                       f'無敵 {"ON" if g.god else "OFF"}  溶岩 {"ストップ" if g.debug_lava else "うごく"}')


# ============================================================
# ⑧ input(): キー・マウスを おした しゅんかんに よばれる
# ============================================================
def input(key):
    if key == 'f11':
        toggle_fullscreen()
        return
    if shop_open:
        if key in ('b', 'escape'):
            close_shop()
        elif key in [str(i + 1) for i in range(len(SHOP_ITEMS))]:
            buy(int(key) - 1)
        return
    if key == 'escape':
        close_menu() if menu_open else open_menu()
        return
    if menu_open:
        return
    if g.state == 'title':
        if key in ('1', '2', '3'):                      # むずかしさを えらぶ
            g.diff = int(key) - 1
            g.items = dict(DIFFICULTIES[g.diff][3])
            sfx('pick')
            show_title()
        elif key in ('left mouse down', 'enter'):
            start()
        return
    if DEBUG and g.state == 'play' and key in ('f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8'):
        debug_key(key)
        return
    if g.state in ('over', 'clear'):
        if key == 'r':
            new_game()
            start()
        elif key == 't':
            new_game()
        return

    if key == 'b':
        open_shop()
        return
    if key in ('1', '2', '3'):
        g.mat = int(key) - 1
        sfx('pick')
        say(f'材料: {NAME[MATERIALS[g.mat]]}', 1.5)
    if key == 'scroll up' or key == 'scroll down':      # マウスホイールでも 材料を かえられる
        g.mat = (g.mat + (1 if key == 'scroll down' else -1)) % len(MATERIALS)
    if key == 'c':
        ride_jet()
    if key == 'f':
        swing_sword()
    if key == 'left mouse down' and enemy_in_aim():     # 敵を ねらって 左クリック → 剣
        swing_sword()
        return
    if key == 'right mouse down' and player.camera_pivot.rotation_x > 55:   # 真下を 見て 右クリック → 積む
        pillar()
        return

    if key not in ('left mouse down', 'right mouse down'):
        return
    target = aimed_block()
    if target is None:
        return
    if key == 'left mouse down' and target.kind in UNBREAKABLE:   # ほるのは update() で（おしつづける）
        say('この ブロックは ほれない', 1.2)
    if key == 'right mouse down':                       # 置く（ねらった 面の となり）
        n = mouse.normal
        pos = (target.key[0] + round(n.x), target.key[1] + round(n.y), target.key[2] + round(n.z))
        if pos in blocks or abs(pos[0]) > HALF or abs(pos[2]) > HALF:
            return
        # 自分の 体と 重なる 所には 置けない
        if abs(pos[0] - player.x) < 0.8 and abs(pos[2] - player.z) < 0.8 and player.y - 0.45 < pos[1] < player.y + 1.8:
            return
        mat = MATERIALS[g.mat]
        if g.items[mat] < 1:
            say(f'{NAME[mat]}が ない。1 / 2 / 3 で 材料を かえよう')
            return
        g.items[mat] -= 1
        add_block(*pos, mat, placed=True)
        g.placed += 1
        sfx('place')


# ============================================================
# ⑨ update(): 毎フレーム よばれる
# ============================================================
def update():
    dt = time.dt
    lava.y = g.lava_y - 30                              # 溶岩の 箱の 上の面 = g.lava_y
    lava.color = lerp(LAVA_COLORS[0], LAVA_COLORS[1], (math.sin(time.time() * 3) + 1) / 4)
    update_sparks(dt)
    update_scenery(dt)
    if g.state != 'play' or menu_open or shop_open:
        return
    g.time += dt
    g.best = max(g.best, height())
    generate()
    name, mult, delay, items = DIFFICULTIES[g.diff]
    area = area_at(height())
    update_motes(dt, area[1])

    # 空の色と 霧を、エリアの 色へ 少しずつ 近づける
    camera.background_color = lerp(camera.background_color, area[2], min(1, dt * 1.5))
    scene.fog_color = camera.background_color
    scene.fog_density = area[4]

    # 溶岩が 上がる（時間が たつほど 速い。ときどき 波）
    if g.lava_stop > 0:
        g.lava_stop -= dt                               # ショップの 溶岩ストップ
    elif g.time > delay and not g.debug_lava:
        speed = min(LAVA_START_SPEED + LAVA_ACCEL * (g.time - delay), LAVA_MAX_SPEED) * mult
        g.wave_timer -= dt
        if g.wave is None and g.wave_timer <= 0:
            g.wave, g.wave_t = 'warn', WAVE_WARNING
            sfx('warn')
        elif g.wave:
            g.wave_t -= dt
            if g.wave == 'warn' and g.wave_t <= 0:
                g.wave, g.wave_t = 'wave', WAVE_TIME
            elif g.wave == 'wave':
                speed *= WAVE_POWER
                if g.wave_t <= 0:
                    g.wave = None
                    g.wave_timer = random.uniform(*WAVE_INTERVAL)
        if player.y - g.lava_y > 20:                    # はなれすぎたら 追いついてくる
            speed += (player.y - g.lava_y - 20) * 0.1
        g.lava_y += speed * dt
    warn_text.enabled = g.wave == 'warn'
    # 波の あいだは 画面が ゆれる
    camera.position = (random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04), 0) if g.wave == 'wave' else (0, 0, 0)

    # 溶岩の 近くの 置いた 木は 燃える
    for pos in [p for p, b in blocks.items() if b.placed and b.kind == 'wood' and p[1] - g.lava_y < WOOD_BURN]:
        burst(pos, color.hex('#ff8a3a'), 4)
        remove_block(pos)

    # 落石
    if height() >= ROCK_START:
        g.rock_timer -= dt
        if g.rock_timer <= 0:
            g.rock_timer = ROCK_INTERVAL
            x = max(-HALF + 1, min(HALF - 1, round(player.x) + random.randint(-1, 1)))
            z = max(-HALF + 1, min(HALF - 1, round(player.z) + random.randint(-1, 1)))
            rocks.append(Rock(x, player.y + 14, z))
    for r in rocks[:]:
        if distance(r.position, player.position + Vec3(0, 1, 0)) < 1.0:
            hurt('rock')
            destroy(r.shadow)
            r.landed = True
        elif r.fall():
            r.landed = True
        if getattr(r, 'landed', False):
            rocks.remove(r)
            destroy(r)

    # 敵
    if height() >= ENEMY_START:
        g.enemy_timer -= dt
        if g.enemy_timer <= 0 and len(enemies) < ENEMY_MAX:
            g.enemy_timer = ENEMY_INTERVAL
            spawn_enemy()
    for e in enemies[:]:
        e.step(dt)
        can_hit = e.rest <= 0 and (e.move == 'hop' or e.mode == 'dash')
        if can_hit and distance(e.position, player.position + Vec3(0, 0.9, 0)) < 0.9:
            hurt('enemy')
            away = e.position - player.position
            e.kb = Vec3(away.x, 0.5, away.z).normalized() * 6
            e.rest = ENEMY_REST
            e.mode = 'chase'
        if e.y < g.lava_y or distance(e.position, player.position) > 30:
            enemies.remove(e)                           # 溶岩に 落ちた・遠すぎる 敵は 消す
            destroy(e)

    # 剣を ふる 動き
    g.swing_wait = max(0, g.swing_wait - dt)
    if g.swing > 0:
        g.swing -= dt
        sword.rotation_x = 25 + math.sin((1 - g.swing / 0.25) * math.pi) * 75
    else:
        sword.rotation_x = 25

    # 回復の実
    for b in berries[:]:
        b.rotation_y += 90 * dt
        if distance(b.position, player.position + Vec3(0, 0.8, 0)) < 1.0:
            g.hp = min(MAX_HP, g.hp + 1)
            berries.remove(b)
            destroy(b)
            sfx('heal')
            say('回復の実で HP +1')

    # ジェット機（足の下から 炎が 出る）
    if g.jet > 0:
        g.jet -= dt
        player.y += JET_SPEED * dt
        if random.random() < 0.6:
            burst(player.position + Vec3(0, -0.3, 0), color.hex('#ffb040'), 1)
        if g.jet <= 0:
            end_jet()

    # 真下に 積む（Q を おしつづける / 真下を 見て 右クリックを おしつづける）
    g.pillar_wait = max(0, g.pillar_wait - dt)
    if g.lift is not None:
        update_lift(dt)
    elif held_keys['q'] or (held_keys['right mouse'] and player.camera_pivot.rotation_x > 55):
        pillar()

    # ねらっている ブロックに 印
    t = aimed_block()
    highlight.enabled = t is not None
    if t:
        highlight.position = t.key

    # ほる: 左クリックを おしつづけると 進む。かたい ブロックほど 時間が かかる
    if held_keys['left mouse'] and t is not None and t.kind not in UNBREAKABLE and not enemy_in_aim():
        if t is not g.mine_block:                       # ちがう ブロックに 変えたら 最初から
            g.mine_block, g.mine_t = t, 0
        before = g.mine_t
        g.mine_t += dt
        if int(before / 0.25) != int(g.mine_t / 0.25):
            sfx('tick')
        rate = min(1, g.mine_t / HARDNESS[t.kind])
        show_mining(True, t, rate)
        highlight.alpha = 0.25 + rate * 0.5             # ほるほど 印が こくなる（ひびの かわり）
        highlight.color = lerp(color.white, color.black, rate * 0.6)
        hand.rotation_x = 10 + math.sin(g.time * 25) * 20   # 手を ふる
        if rate >= 1:
            mine(t)
            g.mine_block = None
    else:
        g.mine_block, g.mine_t = None, 0
        show_mining(False)
        highlight.alpha = 0.25
        highlight.color = color.white
        hand.rotation_x = 10

    # 手に 持っている ブロック（えらんだ 材料の テクスチャ。歩くと ゆれる）
    hand.texture = TEXTURES[MATERIALS[g.mat]]
    moving = held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']
    hand.y = -0.5 + (math.sin(g.time * 10) * 0.02 if moving else 0)

    # エリアが かわったら 知らせる
    idx = AREAS.index(area)
    if idx > g.area_idx:                                # はじめて 上の エリアに 入った
        g.area_idx = idx
        sfx('heal')
        say(f'{area[0]}m  {area[1]}の エリアに 入った！', 3)

    # 画面の 文字
    g.invincible = max(0, g.invincible - dt)
    hurt_flash.alpha = max(0, hurt_flash.alpha - dt)
    height_text.text = f'{height()} m / {GOAL} m   {area[1]}'
    hp_text.text = '♥' * g.hp + '♡' * (MAX_HP - g.hp) + ('  ◆シールド' if g.shield else '')
    item_text.text = '   '.join(('▶' if i == g.mat else '  ') + f'{NAME[m]} {g.items[m]}' for i, m in enumerate(MATERIALS))
    ok = g.free_jet > 0 or all(g.items[k] >= v for k, v in JET_COST.items())
    jet_text.text = 'ジェット機: C で 発進！' if ok else f'ジェット機: 石{JET_COST["stone"]}・鉄{JET_COST["iron"]} で 乗れる'
    coin_text.text = f'コイン {g.coins}  (B ショップ)   鍵 ' + '●' * g.keys + '○' * (3 - g.keys)
    if g.radar > 0:
        g.radar -= dt
        radar_text.text = key_direction()
    else:
        radar_text.text = ''
        for e in enemies:                               # 見えない 所の 敵を 知らせる
            d = e.position - camera.world_position
            if d.length() < 5 and d.normalized().dot(camera.forward) < 0.3:
                radar_text.text = '後ろに 敵！'
                break
    gap = player.y - g.lava_y
    if g.lava_stop > 0:
        lava_text.text = f' 溶岩ストップ中 あと {int(g.lava_stop) + 1} 秒 '
    elif g.time < delay:
        lava_text.text = f' 溶岩が 動きだすまで あと {int(delay - g.time) + 1} 秒 '
    else:
        lava_text.text = f' 溶岩まで {max(0, int(gap))} m '
    lava_text.color = color.hex('#ff7850') if gap < 6 else color.white
    lava_glow.alpha = max(0, min(0.35, (6 - gap) / 15))
    bar_fill.scale_y = max(0.001, 0.6 * min(1, height() / GOAL))
    bar_lava.y = -0.3 + 0.6 * max(0, min(1, g.lava_y / GOAL))
    g.message_time -= dt
    message_text.enabled = g.message_time > 0

    if DEBUG:
        update_debug_text()

    # 勝ち・負け
    if height() >= GOAL:
        finish('clear')
    elif g.god and player.y < g.lava_y:                 # デバッグの 無敵: 溶岩の 上に もどす
        warp(int(g.lava_y) + 3)
    elif player.y < g.lava_y or g.hp <= 0:
        finish('over')


new_game()
app.run()
