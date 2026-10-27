# ============================================================
#  LAVA CRAFT 3D（～ 天国まで逃げろ！ ～）  Ursina 版
#
#  たてに長い「たて穴」の中で、下から 溶岩が 上がってくる。
#  かべや 浮き島の ブロックを ほって 資材を あつめ、
#  ブロックを 置いて 足場を 作りながら 上へ 上へ にげる。
#  高さ 120m の 天国の 門に 着いたら クリア！
#
#  操作:
#    WASD     … 移動          マウス … 見回す       Space … ジャンプ
#    左クリック … ブロックを ほる（資材が 手に入る）
#    右クリック … ブロックを 置く（真下を 向いて ジャンプ中に 置くと 上に のぼれる）
#    1 / 2 / 3 … 置く 材料を えらぶ（木・石・鉄）   ※タイトルでは むずかしさを えらぶ
#    C        … ジェット機（石と鉄を 使って 一気に 上へ）
#    Esc      … メニュー（もどる / やめる）
#
#  プログラムの つくり（上から 順番に 読めば わかるように 並べてある）
#    ① 準備        … Ursina を 起動して、日本語の フォントと 効果音を 用意する
#    ② 設定        … ゲームの 数字（速さ・高さ など）を まとめた所
#    ③ ブロック    … Block クラスと、たて穴を 作る 関数
#    ④ けしき      … エリアごとの かざり（結晶・木・雲・柱）と 天国の 門
#    ⑤ プレイヤーと 画面の 文字
#    ⑥ 落石・回復の実・ジェット機・小さな 演出
#    ⑦ ゲームの 流れ（タイトル・スタート・ゲームオーバー・メニュー）
#    ⑧ input()  … キー・マウスを おしたとき（Ursina が 自動で よぶ）
#    ⑨ update() … 毎フレーム（1秒に 約60回）よばれる
# ============================================================
import json
import math
import os
import random
import shutil
import struct
import wave

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import basic_lighting_shader      # 光の 向きで 面の 明るさを 変える（立体に 見える）


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


# ============================================================
# ② 設定（ここの 数字を 変えると むずかしさが 変わる）
# ============================================================
GOAL = 120                  # 天国の 高さ（m）。1ブロック = 1m
HALF = 5                    # たて穴の 広さ（まんなかから かべまで 5ブロック）
REACH = 6                   # ほる・置く ことが できる きょり（ブロック）
MAX_HP = 5

LAVA_DELAY = 20             # 溶岩が 動きだすまでの 時間（秒）
LAVA_START_SPEED = 0.15     # 溶岩の 最初の 速さ（m/秒）
LAVA_ACCEL = 0.004          # 1秒ごとに 速くなる 量
LAVA_MAX_SPEED = 1.2        # 溶岩の 最高速度
WAVE_INTERVAL = (35, 50)    # 溶岩の「波」が 来る 間かく（秒）
WAVE_WARNING = 3            # 警告から 波までの 時間（秒）
WAVE_TIME = 3               # 波が つづく 時間（秒）
WAVE_POWER = 4              # 波のあいだ 溶岩が 何倍 速くなるか
WOOD_BURN = 3               # 置いた 木は、溶岩から この高さまで 近づくと 燃える

ROCK_INTERVAL = 5           # 落石の 間かく（秒）
ROCK_START = 8              # この 高さ（m）より 上で 落石が はじまる

JET_COST = {'stone': 8, 'iron': 8}   # ジェット機の 材料
JET_TIME = 3                # ジェット機が 飛ぶ 時間（秒）
JET_SPEED = 10              # ジェット機の 上る 速さ（m/秒）→ 3秒で 30m

# むずかしさ: (名前, 溶岩の 速さの 倍率, 溶岩が 動きだすまでの 時間, 最初の 資材)
DIFFICULTIES = [
    ('やさしい',   0.7, 30, {'wood': 12, 'stone': 12, 'iron': 4}),
    ('ふつう',     1.0, 20, {'wood': 6, 'stone': 6, 'iron': 0}),
    ('むずかしい', 1.4, 12, {'wood': 3, 'stone': 3, 'iron': 0}),
]
BEST_FILE = os.path.join(HERE, 'lava_craft_3d_best.json')

# エリア: (はじまる 高さ m, 名前, 空の色, 資材の 出やすさ)
AREAS = [
    (0,  '洞窟', color.hex('#1c1424'), {'wood': 0.15, 'stone': 0.60, 'iron': 0.25}),
    (30, '森',   color.hex('#78b0dc'), {'wood': 0.60, 'stone': 0.25, 'iron': 0.15}),
    (60, '空',   color.hex('#5a8ee6'), {'wood': 0.20, 'stone': 0.35, 'iron': 0.45}),
    (90, '天国', color.hex('#ffe6c8'), {'wood': 0.15, 'stone': 0.30, 'iron': 0.55}),
]
BLOCK_COLOR = {
    'ground': color.hex('#5a5664'),     # 一番下の 地面（こわせない）
    'wood':   color.hex('#d08c4c'),
    'stone':  color.hex('#a8a8b4'),
    'iron':   color.hex('#eef1fa'),
    'cloud':  color.hex('#f4f6ff'),     # 雲（乗れるけど ほれない）
    'gold':   color.hex('#ffd24a'),     # 天国の 床（ほれない）
}
NAME = {'wood': '木', 'stone': '石', 'iron': '鉄'}
MATERIALS = ['wood', 'stone', 'iron']
UNBREAKABLE = ('ground', 'cloud', 'gold')


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


class Block(Entity):
    def __init__(self, position, kind, placed=False):
        c = lerp(BLOCK_COLOR[kind], color.black, random.uniform(0, 0.12))   # 少しずつ 色を 変えると 自然に 見える
        super().__init__(model='cube', texture='white_cube', position=position, color=c, collider='box',
                         shader=basic_lighting_shader)
        self.key = position                             # 辞書の キー (x, y, z)
        self.kind = kind
        self.placed = placed                            # 自分で 置いた ブロックなら True
        blocks[position] = self


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


def random_resource(height):
    """その 高さに 合った 資材を 1つ 決める（上に 行くほど 鉄が 多い）"""
    rate = area_at(height)[3]
    x = random.random()
    if x < rate['iron']:
        return 'iron'
    if x < rate['iron'] + rate['stone']:
        return 'stone'
    return 'wood'


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
                add_block(x, y, z, random_resource(y))
    # 3だんごとに 浮き島
    if y % 3 == 0:
        cx, cz = random.randint(-2, 2), random.randint(-2, 2)
        size = random.randint(1, 2)
        cloud = area_at(y)[1] == '空' and random.random() < 0.5
        for x in range(cx - size, cx + size):
            for z in range(cz - size, cz + size):
                add_block(x, y, z, 'cloud' if cloud else random_resource(y))
        if random.random() < 0.25:                      # ときどき 回復の実
            berries.append(Entity(model='sphere', color=color.hex('#e83c5a'), scale=0.45,
                                  position=(cx, y + 0.8, cz)))
    # 4だんごとに たて穴の 外の けしき
    if y % 4 == 0:
        make_scenery(y)


# たて穴の 外に 出られないように する 見えない かべ
for x, z, sx, sz in ((HALF + 1, 0, 1, HALF * 2 + 3), (-HALF - 1, 0, 1, HALF * 2 + 3),
                     (0, HALF + 1, HALF * 2 + 3, 1), (0, -HALF - 1, HALF * 2 + 3, 1)):
    Entity(model='cube', position=(x, 500, z), scale=(sx, 1000, sz), collider='box', visible=False)


# ============================================================
# ④ けしき（さわれない かざり。かべの すきまから 見える）
# ============================================================
scenery = []                                            # (高さ, かざり) の リスト。溶岩に しずんだら 消す


def deco(y, **kw):
    e = Entity(shader=basic_lighting_shader, **kw)
    scenery.append((y, e))
    return e


def make_scenery(y):
    area = area_at(y)[1]
    for _ in range(2):
        side = random.choice((-1, 1))
        d = random.uniform(HALF + 3, HALF + 9)          # たて穴から 少し はなれた 所
        a = random.uniform(-HALF - 6, HALF + 6)
        x, z = (side * d, a) if random.random() < 0.5 else (a, side * d)
        if area == '洞窟':                              # 光る 結晶
            c = random.choice(('#9b6bff', '#4fd6ff', '#ff6bd6'))
            deco(y, model='cube', color=color.hex(c), position=(x, y + 1, z),
                 scale=(0.6, random.uniform(1.5, 3), 0.6), rotation=(random.uniform(-20, 20), 0, random.uniform(-25, 25)))
        elif area == '森':                              # 木（みき と 葉っぱ）
            h = random.uniform(3, 5)
            deco(y, model='cube', color=color.hex('#6b4a2e'), position=(x, y + h / 2, z), scale=(0.6, h, 0.6))
            deco(y, model='cube', color=color.hex('#4f9a4a'), position=(x, y + h, z), scale=(2.4, 1.8, 2.4))
        elif area == '空':                              # 雲
            deco(y, model='cube', color=color.hex('#ffffff'), position=(x, y + 1, z),
                 scale=(random.uniform(3, 6), 0.8, random.uniform(2, 4)))
        else:                                           # 天国の 金の 柱
            deco(y, model='cube', color=color.hex('#ffe08a'), position=(x, y + 2, z), scale=(0.8, 4, 0.8))


def make_gate(y):
    """天国の 門（2本の 柱と 横の はり）"""
    for x in (-2, 2):
        deco(y, model='cube', color=color.hex('#ffd24a'), position=(x, y + 2.5, 0), scale=(0.6, 4, 0.6))
    deco(y, model='cube', color=color.hex('#fff1b8'), position=(0, y + 4.7, 0), scale=(5.2, 0.5, 0.8))
    deco(y, model='sphere', color=color.hex('#ffffff'), position=(0, y + 5.6, 0), scale=1.0)


# ============================================================
# ⑤ プレイヤーと 画面の 文字
# ============================================================
player = FirstPersonController(position=(0, 1, 0), speed=6, jump_height=2.2)
player.enabled = False

lava = Entity(model='cube', color=color.hex('#ff5a14'), scale=(HALF * 2 + 3, 60, HALF * 2 + 3))
LAVA_COLORS = (color.hex('#ff4a10'), color.hex('#ffa030'))           # 溶岩の 色（2色の あいだで ゆらめく）
highlight = Entity(model='cube', color=color.white, scale=1.02)      # ねらっている ブロックの 印
highlight.alpha = 0.25
hand = Entity(parent=camera, model='cube', texture='white_cube', position=(0.62, -0.5, 1.5),
              scale=0.22, rotation=(10, -25, 0), shader=basic_lighting_shader)   # 手に 持っている ブロック

height_text = Text(position=(-0.86, 0.47), scale=1.6)
hp_text = Text(position=(-0.86, 0.41), scale=1.4, color=color.hex('#ff6a80'))
item_text = Text(position=(0.3, 0.47), scale=1.3)
jet_text = Text(position=(0.3, 0.42), scale=1.0, color=color.hex('#bfe3ff'))
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
panel = Entity(parent=camera.ui, model='quad', scale=(1.35, 0.72), position=(0, 0.06), color=color.black)
panel.alpha = 0.6                                                     # 文字の うしろの 黒い 板
big_text = Text(position=(0, 0.25), origin=(0, 0), scale=3)
sub_text = Text(position=(0, 0.04), origin=(0, 0), scale=1.3)
hud = [height_text, hp_text, item_text, jet_text, lava_text, bar_back, bar_fill, bar_lava, hand]


class State:
    """ゲームの 状態を まとめた 箱"""
    pass


g = State()
g.diff = 1                                              # むずかしさ（DIFFICULTIES の 番号）


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
# ⑥ 落石・回復の実・ジェット機・小さな 演出
# ============================================================
rocks = []
berries = []
sparks = []                                             # こわした ときの かけら


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


def hurt():
    if g.invincible > 0:
        return
    g.hp -= 1
    g.invincible = 1.0
    hurt_flash.alpha = 0.45
    sfx('hurt')


def ride_jet():
    if g.jet > 0:
        return
    if any(g.items[k] < v for k, v in JET_COST.items()):
        say('ジェット機には 石 8 と 鉄 8 が いる')
        return
    for k, v in JET_COST.items():
        g.items[k] -= v
    g.jet = JET_TIME
    player.gravity = 0                                  # 重力を 切って 上へ
    g.placed += 10
    sfx('jet')
    say('ジェット機で 一気に 上へ！')


def end_jet():
    """ジェット機が 終わったら、ブロックの 中なら 上へ 出して、足の下に 石の 足場を 作る"""
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


# ============================================================
# ⑦ ゲームの 流れ
# ============================================================
def new_game():
    """世界を 作りなおして、タイトル画面に する"""
    for pos in list(blocks):
        remove_block(pos)
    for e in rocks + berries + sparks + [e for _, e in scenery]:
        if isinstance(e, Rock):
            destroy(e.shadow)
        destroy(e)
    rocks.clear()
    berries.clear()
    sparks.clear()
    scenery.clear()
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
    big_text.text = 'LAVA CRAFT 3D'
    big_text.color = color.hex('#ffc850')
    sub_text.text = ('～ 天国まで 逃げろ！ ～\n\n' + '\n'.join(lines) +
                     '\n\n1 / 2 / 3 で むずかしさを えらんで、クリック か Enter で スタート\n'
                     'WASD 移動 ・ 左クリック ほる ・ 右クリック 置く ・ C ジェット機')
    camera.background_color = AREAS[0][2]
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
    say(f'むずかしさ: {name}。溶岩が 動きだす 前に 資材を あつめよう！', 4)


def generate():
    """プレイヤーの 少し上まで だんを 作り、溶岩に しずんだ だんは 消す（軽くするため）"""
    while g.top_layer < min(player.y + 16, GOAL):
        g.top_layer += 1
        make_layer(g.top_layer)
    for pos in [p for p in blocks if p[1] < g.lava_y - 4]:
        remove_block(pos)
    for b in [b for b in berries if b.y < g.lava_y]:
        berries.remove(b)
        destroy(b)
    for item in [s for s in scenery if s[0] < g.lava_y - 6]:
        scenery.remove(item)
        destroy(item[1])


def height():
    return max(0, round(player.y - 0.5))


def finish(result):
    g.state = result
    player.enabled = False
    mouse.locked = False
    for e in hud:
        e.enabled = False
    warn_text.enabled = False
    lava_glow.alpha = 0
    name = DIFFICULTIES[g.diff][0]
    score = int(g.time) + g.best * 10 + g.placed * 2 + (500 if result == 'clear' else 0)
    best = load_best()
    record = score > best.get(name, 0)
    if record:
        best[name] = score
        save_best(best)
    if result == 'clear':
        big_text.text = '天国に 着いた！'
        big_text.color = color.hex('#ffe678')
        sfx('clear')
    else:
        big_text.text = 'ゲームオーバー'
        big_text.color = color.hex('#ff5a46')
        sfx('over')
    sub_text.text = (f'むずかしさ: {name}\n\n'
                     f'時間 {int(g.time)}点 + 高さ {g.best}m×10 + 置いた数 {g.placed}×2'
                     + (' + 天国 500' if result == 'clear' else '')
                     + f'\n\nスコア  {score}' + ('   ★ 新記録！' if record else f'   （ベスト {best.get(name, 0)}）')
                     + '\n\nR で もう一度   T で タイトルへ')
    big_text.enabled = sub_text.enabled = panel.enabled = True


# Esc の メニュー（授業の サンプルと 同じ しくみ）
menu_open = False
resume_button = Button(text='もどる', color=color.gray, scale=(0.3, 0.1), position=(0, -0.38), enabled=False)
quit_button = Button(text='やめる', color=color.red, scale=(0.3, 0.1), position=(0, -0.5), enabled=False)
quit_button.on_click = application.quit


def open_menu():
    global menu_open
    menu_open = True
    player.enabled = False
    mouse.locked = False
    resume_button.enabled = quit_button.enabled = True


def close_menu():
    global menu_open
    menu_open = False
    resume_button.enabled = quit_button.enabled = False
    if g.state == 'play':
        player.enabled = True
        mouse.locked = True


resume_button.on_click = close_menu


# ============================================================
# ⑧ input(): キー・マウスを おした しゅんかんに よばれる
# ============================================================
def input(key):
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
    if g.state in ('over', 'clear'):
        if key == 'r':
            new_game()
            start()
        elif key == 't':
            new_game()
        return

    if key in ('1', '2', '3'):
        g.mat = int(key) - 1
        sfx('pick')
        say(f'材料: {NAME[MATERIALS[g.mat]]}', 1.5)
    if key == 'scroll up' or key == 'scroll down':      # マウスホイールでも 材料を かえられる
        g.mat = (g.mat + (1 if key == 'scroll down' else -1)) % len(MATERIALS)
    if key == 'c':
        ride_jet()

    if key not in ('left mouse down', 'right mouse down'):
        return
    target = aimed_block()
    if target is None:
        return
    if key == 'left mouse down':                        # ほる
        if target.kind in UNBREAKABLE:
            return
        g.items[target.kind] += 1
        burst(target.key, target.color)
        sfx('mine')
        remove_block(target.key)
    if key == 'right mouse down':                       # 置く（ねらった 面の となり）
        n = mouse.normal
        pos = (target.key[0] + round(n.x), target.key[1] + round(n.y), target.key[2] + round(n.z))
        if pos in blocks or abs(pos[0]) > HALF or abs(pos[2]) > HALF:
            return
        # 自分の 体と 重なる 所には 置けない（ジャンプ中に 足の下なら OK）
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
    lava.y = g.lava_y - 30                              # 溶岩の 箱の 上の面 = g.lava_y
    lava.color = lerp(LAVA_COLORS[0], LAVA_COLORS[1], (math.sin(time.time() * 3) + 1) / 4)
    update_sparks(time.dt)
    if g.state != 'play' or menu_open:
        return
    dt = time.dt
    g.time += dt
    g.best = max(g.best, height())
    generate()
    name, mult, delay, items = DIFFICULTIES[g.diff]

    # 溶岩が 上がる（時間が たつほど 速い。ときどき 波）
    if g.time > delay:
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
            hurt()
            destroy(r.shadow)
            r.landed = True
        elif r.fall():
            r.landed = True
        if getattr(r, 'landed', False):
            rocks.remove(r)
            destroy(r)

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

    # ねらっている ブロックに 印
    t = aimed_block()
    highlight.enabled = t is not None
    if t:
        highlight.position = t.key

    # 手に 持っている ブロック（えらんだ 材料の 色。歩くと ゆれる）
    hand.color = BLOCK_COLOR[MATERIALS[g.mat]]
    moving = held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']
    hand.y = -0.5 + (math.sin(g.time * 10) * 0.02 if moving else 0)

    # エリアが かわったら 知らせる・空の 色を かえる
    area = area_at(height())
    camera.background_color = area[2]
    idx = AREAS.index(area)
    if idx > g.area_idx:                                # はじめて 上の エリアに 入った
        g.area_idx = idx
        sfx('heal')
        say(f'{area[0]}m  {area[1]}の エリアに 入った！', 3)

    # 画面の 文字
    g.invincible = max(0, g.invincible - dt)
    hurt_flash.alpha = max(0, hurt_flash.alpha - dt)
    height_text.text = f'{height()} m / {GOAL} m   {area[1]}'
    hp_text.text = '♥' * g.hp + '♡' * (MAX_HP - g.hp)
    item_text.text = '   '.join(('▶' if i == g.mat else '  ') + f'{NAME[m]} {g.items[m]}' for i, m in enumerate(MATERIALS))
    ok = all(g.items[k] >= v for k, v in JET_COST.items())
    jet_text.text = 'ジェット機: C で 発進！' if ok else f'ジェット機: 石{JET_COST["stone"]}・鉄{JET_COST["iron"]} で 乗れる'
    gap = player.y - g.lava_y
    if g.time < delay:
        lava_text.text = f' 溶岩が 動きだすまで あと {int(delay - g.time) + 1} 秒 '
    else:
        lava_text.text = f' 溶岩まで {max(0, int(gap))} m '
    lava_text.color = color.hex('#ff7850') if gap < 6 else color.white
    lava_glow.alpha = max(0, min(0.35, (6 - gap) / 15))
    bar_fill.scale_y = max(0.001, 0.6 * min(1, height() / GOAL))
    bar_lava.y = -0.3 + 0.6 * max(0, min(1, g.lava_y / GOAL))
    g.message_time -= dt
    message_text.enabled = g.message_time > 0

    # 勝ち・負け
    if height() >= GOAL:
        finish('clear')
    elif player.y < g.lava_y or g.hp <= 0:
        finish('over')


new_game()
app.run()
