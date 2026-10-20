# ============================================================
#  LAVA CRAFT 3D（～ 天国まで逃げろ！ ～）  Ursina 版
#
#  たてに長い「たて穴」の中で、下から 溶岩が 上がってくる。
#  かべや 浮き島の ブロックを ほって 資材を あつめ、
#  ブロックを 置いて 足場を 作りながら 上へ 上へ にげる。
#  高さ 120m の 天国に 着いたら クリア！
#
#  操作:
#    WASD     … 移動          マウス … 見回す       Space … ジャンプ
#    左クリック … ブロックを ほる（資材が 手に入る）
#    右クリック … ブロックを 置く（ジャンプ中に 足の下に 置くと 上に のぼれる）
#    1 / 2 / 3 … 置く 材料を えらぶ（木・石・鉄）
#    C        … ジェット機（石と鉄を 使って 一気に 上へ）
#    Esc      … メニュー（もどる / やめる）
#
#  プログラムの つくり（上から 順番に 読めば わかるように 並べてある）
#    ① 準備        … Ursina を 起動して、日本語の フォントを 使えるようにする
#    ② 設定        … ゲームの 数字（速さ・高さ など）を まとめた所
#    ③ ブロック    … Block クラスと、たて穴を 作る 関数
#    ④ プレイヤーと 画面の 文字
#    ⑤ 落石・回復の実・ジェット機
#    ⑥ ゲームの 流れ（スタート・ゲームオーバー・メニュー）
#    ⑦ input()  … キー・マウスを おしたとき（Ursina が 自動で よぶ）
#    ⑧ update() … 毎フレーム（1秒に 約60回）よばれる
# ============================================================
import math
import os
import random

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import basic_lighting_shader      # 光の 向きで 面の 明るさを 変える（立体に 見える）


# ============================================================
# ① 準備
# ============================================================
app = Ursina(title='LAVA CRAFT 3D')
window.exit_button.visible = False
window.fps_counter.enabled = True

# 日本語が 出る フォント
#   Ursina は「このファイルと 同じ フォルダ」から フォントを さがすので、
#   Windows の メイリオを ここに コピーしてから 使う（2回目からは コピー済みの ものを 使う）
import shutil
HERE = os.path.dirname(os.path.abspath(__file__))
for name in ('meiryo.ttc', 'YuGothM.ttc', 'msgothic.ttc'):
    src = os.path.join(r'C:\Windows\Fonts', name)
    dst = os.path.join(HERE, name)
    if not os.path.exists(dst) and os.path.exists(src):
        shutil.copy(src, dst)
    if os.path.exists(dst):
        Text.default_font = name
        break


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
}
NAME = {'wood': '木', 'stone': '石', 'iron': '鉄'}
MATERIALS = ['wood', 'stone', 'iron']


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


# たて穴の 外に 出られないように する 見えない かべ
for x, z, sx, sz in ((HALF + 1, 0, 1, HALF * 2 + 3), (-HALF - 1, 0, 1, HALF * 2 + 3),
                     (0, HALF + 1, HALF * 2 + 3, 1), (0, -HALF - 1, HALF * 2 + 3, 1)):
    Entity(model='cube', position=(x, 500, z), scale=(sx, 1000, sz), collider='box', visible=False)


# ============================================================
# ④ プレイヤーと 画面の 文字
# ============================================================
player = FirstPersonController(position=(0, 1, 0), speed=6, jump_height=2.2)
player.enabled = False

lava = Entity(model='cube', color=color.hex('#ff5a14'), scale=(HALF * 2 + 3, 60, HALF * 2 + 3))
LAVA_COLORS = (color.hex('#ff4a10'), color.hex('#ffa030'))           # 溶岩の 色（2色の あいだで ゆらめく）
highlight = Entity(model='cube', color=color.white, scale=1.02)      # ねらっている ブロックの 印
highlight.alpha = 0.25

height_text = Text(position=(-0.86, 0.47), scale=1.6)
hp_text = Text(position=(-0.86, 0.41), scale=1.4, color=color.hex('#ff6a80'))
item_text = Text(position=(0.38, 0.47), scale=1.3)
lava_text = Text(position=(0, -0.42), origin=(0, 0), scale=1.6)
message_text = Text(position=(0, -0.34), origin=(0, 0), scale=1.2)
warn_text = Text(text='溶岩の 波が 来る！ 上へ にげろ！', position=(0, 0.25), origin=(0, 0),
                 scale=2.5, color=color.hex('#ff5028'), enabled=False)
panel = Entity(parent=camera.ui, model='quad', scale=(1.3, 0.62), position=(0, 0.1), color=color.black)
panel.alpha = 0.6                                                     # 文字の うしろの 黒い 板
big_text = Text(position=(0, 0.2), origin=(0, 0), scale=3)
sub_text = Text(position=(0, 0.05), origin=(0, 0), scale=1.4)
hurt_flash = Entity(parent=camera.ui, model='quad', scale=(2, 1), color=color.red)
hurt_flash.alpha = 0


class State:
    """ゲームの 状態を まとめた 箱"""
    pass


g = State()


def say(text, time=2.5):
    message_text.text = text
    g.message_time = time


# ============================================================
# ⑤ 落石・回復の実・ジェット機
# ============================================================
rocks = []
berries = []


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
            destroy(self.shadow)
            return True
        return False


def hurt():
    if g.invincible > 0:
        return
    g.hp -= 1
    g.invincible = 1.0
    hurt_flash.alpha = 0.45


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
# ⑥ ゲームの 流れ
# ============================================================
def new_game():
    """世界を 作りなおして、はじめから"""
    for pos in list(blocks):
        remove_block(pos)
    for e in rocks + berries:
        destroy(e)
        if isinstance(e, Rock):
            destroy(e.shadow)
    rocks.clear()
    berries.clear()
    g.state = 'title'
    g.time = 0
    g.hp = MAX_HP
    g.invincible = 0
    g.items = {'wood': 6, 'stone': 6, 'iron': 0}
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
    player.position = (0, 1, 0)
    player.gravity = 1
    generate()
    big_text.text = 'LAVA CRAFT 3D'
    big_text.color = color.hex('#ffc850')
    sub_text.text = '～ 天国まで 逃げろ！ ～\n\nクリック か Enter で スタート'
    camera.background_color = AREAS[0][2]
    big_text.enabled = sub_text.enabled = panel.enabled = True


def start():
    g.state = 'play'
    big_text.enabled = sub_text.enabled = panel.enabled = False
    player.enabled = True
    mouse.locked = True


def generate():
    """プレイヤーの 少し上まで だんを 作り、溶岩に しずんだ だんは 消す（軽くするため）"""
    while g.top_layer < player.y + 16:
        g.top_layer += 1
        make_layer(g.top_layer)
    for pos in [p for p in blocks if p[1] < g.lava_y - 4]:
        remove_block(pos)
    for b in [b for b in berries if b.y < g.lava_y]:
        berries.remove(b)
        destroy(b)


def height():
    return max(0, round(player.y - 0.5))


def finish(result):
    g.state = result
    player.enabled = False
    mouse.locked = False
    score = int(g.time) + g.best * 10 + g.placed * 2 + (500 if result == 'clear' else 0)
    if result == 'clear':
        big_text.text = '天国に 着いた！'
        big_text.color = color.hex('#ffe678')
    else:
        big_text.text = 'ゲームオーバー'
        big_text.color = color.hex('#ff5a46')
    sub_text.text = (f'時間 {int(g.time)}点 + 高さ {g.best}m×10 + 置いた数 {g.placed}×2'
                     + (' + 天国 500' if result == 'clear' else '')
                     + f'\n\nスコア  {score}\n\nR で もう一度')
    big_text.enabled = sub_text.enabled = panel.enabled = True


# Esc の メニュー（授業の サンプルと 同じ しくみ）
menu_open = False
resume_button = Button(text='もどる', color=color.gray, scale=(0.3, 0.1), position=(0, 0.07), enabled=False)
quit_button = Button(text='やめる', color=color.red, scale=(0.3, 0.1), position=(0, -0.07), enabled=False)
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
# ⑦ input(): キー・マウスを おした しゅんかんに よばれる
# ============================================================
def input(key):
    if key == 'escape':
        close_menu() if menu_open else open_menu()
        return
    if menu_open:
        return
    if g.state == 'title' and key in ('left mouse down', 'enter'):
        start()
        return
    if g.state in ('over', 'clear') and key == 'r':
        new_game()
        start()
        return
    if g.state != 'play':
        return

    if key in ('1', '2', '3'):
        g.mat = int(key) - 1
        say(f'材料: {NAME[MATERIALS[g.mat]]}')
    if key == 'c':
        ride_jet()

    if key not in ('left mouse down', 'right mouse down'):
        return
    target = aimed_block()
    if target is None:
        return
    if key == 'left mouse down':                        # ほる
        if target.kind in ('ground', 'cloud'):
            return
        g.items[target.kind] += 1
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


# ============================================================
# ⑧ update(): 毎フレーム よばれる
# ============================================================
def update():
    lava.y = g.lava_y - 30                              # 溶岩の 箱の 上の面 = g.lava_y
    lava.color = lerp(LAVA_COLORS[0], LAVA_COLORS[1], (math.sin(time.time() * 3) + 1) / 4)
    if g.state != 'play' or menu_open:
        return
    dt = time.dt
    g.time += dt
    g.best = max(g.best, height())
    generate()

    # 溶岩が 上がる（時間が たつほど 速い。ときどき 波）
    if g.time > LAVA_DELAY:
        speed = min(LAVA_START_SPEED + LAVA_ACCEL * (g.time - LAVA_DELAY), LAVA_MAX_SPEED)
        g.wave_timer -= dt
        if g.wave is None and g.wave_timer <= 0:
            g.wave, g.wave_t = 'warn', WAVE_WARNING
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

    # 溶岩の 近くの 置いた 木は 燃える
    for pos in [p for p, b in blocks.items() if b.placed and b.kind == 'wood' and p[1] - g.lava_y < WOOD_BURN]:
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
            say('回復の実で HP +1')

    # ジェット機
    if g.jet > 0:
        g.jet -= dt
        player.y += JET_SPEED * dt
        if g.jet <= 0:
            end_jet()

    # ねらっている ブロックに 印
    t = aimed_block()
    highlight.enabled = t is not None
    if t:
        highlight.position = t.key

    # 空の 色（エリアごと）
    camera.background_color = area_at(height())[2]

    # 画面の 文字
    g.invincible = max(0, g.invincible - dt)
    hurt_flash.alpha = max(0, hurt_flash.alpha - dt)
    height_text.text = f'{height()} m / {GOAL} m   {area_at(height())[1]}'
    hp_text.text = '♥' * g.hp + '♡' * (MAX_HP - g.hp)
    item_text.text = '   '.join(('▶' if i == g.mat else '  ') + f'{NAME[m]} {g.items[m]}' for i, m in enumerate(MATERIALS))
    gap = player.y - g.lava_y
    if g.time < LAVA_DELAY:
        lava_text.text = f' 溶岩が 動きだすまで あと {int(LAVA_DELAY - g.time) + 1} 秒 '
    else:
        lava_text.text = f' 溶岩まで {max(0, int(gap))} m '
    lava_text.color = color.hex('#ff7850') if gap < 6 else color.white
    g.message_time -= dt
    message_text.enabled = g.message_time > 0

    # 勝ち・負け
    if height() >= GOAL:
        finish('clear')
    elif player.y < g.lava_y or g.hp <= 0:
        finish('over')


new_game()
app.run()
