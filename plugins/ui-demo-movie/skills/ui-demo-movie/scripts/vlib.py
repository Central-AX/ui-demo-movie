# -*- coding: utf-8 -*-
"""実演動画の共通部品（1920x1080・30fps・無音・H.264）。

画面の考え方：
  上に灰色の1行ラベル（何をしている場面か）＋細い下線、下に実画面の切り出しを全幅で置く。
  最下部に紺の細い帯。字幕は付けない（話し手の声と二重になるため）。
"""
import os, pathlib, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

W, H, FPS = 1920, 1080, 30
NAVY = (0, 51, 131)
RED = (228, 60, 89)
GRAY = (90, 90, 90)
LINE = (222, 222, 222)
LABEL_GRAY = (120, 126, 134)
TOP, BOTTOM = 152, H - 36          # 実画面を置ける上下の範囲

# ── フォント：環境変数 UIDEMO_FONT があればそれ、無ければ OS ごとの日本語フォントを順に探す
_FONT_CANDIDATES = [
    os.environ.get("UIDEMO_FONT", ""),
    str(pathlib.Path.home() / "Library/Fonts/NotoSansJP-VF.ttf"),
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]
FONT = next((p for p in _FONT_CANDIDATES if p and pathlib.Path(p).exists()), None)


def font(px, bold=True):
    if FONT is None:
        raise SystemExit("日本語フォントが見つかりません。UIDEMO_FONT にフォントのパスを入れてください")
    f = ImageFont.truetype(FONT, px)
    try:
        f.set_variation_by_name("Bold" if bold else "Regular")   # 可変フォントのときだけ効く
    except Exception:
        pass
    return f


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise SystemExit("ffmpeg が見つかりません（Mac: brew install ffmpeg ／ Windows: winget install ffmpeg "
                         "／ どちらでも: pip install imageio-ffmpeg）")


# ── 動き
def ss(x):
    """smoothstep：ゆっくり動き出して、ゆっくり止まる"""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ── 画面
def base():
    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, H - 10, W, H], fill=NAVY)
    return im, dr


def label(dr, text):
    """上の灰色ラベル。1行・短く（何をしている場面か、だけ）"""
    if not text:
        return
    f = font(42)
    dr.text((96, 58), text, fill=LABEL_GRAY, font=f)
    dr.rectangle([96, 112, 96 + dr.textlength(text, font=f), 117], fill=(226, 229, 234))


def place(canvas, dr, src, crop=None, top=TOP, bottom=BOTTOM, left=0, right=W):
    """実画面の切り出しを、指定の枠に収まる最大サイズで中央に置く。(x, y, 倍率) を返す"""
    im = src.crop(crop) if crop else src
    aw, ah = right - left, bottom - top
    sc = min(aw / im.width, ah / im.height)
    th = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
    ix, iy = left + (aw - th.width) // 2, top + max(0, (ah - th.height) // 2)
    dr.rectangle([ix - 2, iy - 2, ix + th.width + 2, iy + th.height + 2], outline=LINE, width=2)
    canvas.paste(th, (ix, iy))
    return ix, iy, sc


# ── 実画面を読む（座標は目で読まない。必ず画素から取る）
def bg_of(im, box):
    """その領域でいちばん多い色＝地の色。消すときはこの色で塗る（行の地色が白でも淡い黄でも合う）"""
    a = np.asarray(im.crop(box).convert("RGB")).reshape(-1, 3)
    c, n = np.unique(a, axis=0, return_counts=True)
    return tuple(int(v) for v in c[n.argmax()])


def text_span(im, y0, y1, x0, x1, dark=150):
    """その行で文字が載っている x の範囲（タイプ打ちの終点）"""
    a = np.asarray(im.crop((x0, y0, x1, y1)).convert("L"))
    cols = np.where((a < dark).sum(axis=0) > 0)[0]
    return (x0 + int(cols.min()), x0 + int(cols.max()) + 6) if len(cols) else (x0, x0)


# ── AIの姿
def ai_chip(d, row_box, gutter_x, gutter_w=52, frame=True):
    """処理中の行：行番号の欄を赤い「AI」チップに差し替え、行の上下に赤線を引く。
    row_box=(x0, y0, x1, y1) は実画面の座標。gutter_x は行番号欄の左端"""
    x0, y0, x1, y1 = row_box
    d.rectangle([gutter_x, y0 + 1, gutter_x + gutter_w, y1 - 1], fill=RED)
    fh = max(12, int((y1 - y0) * 0.62))
    f = font(fh)
    tw = d.textlength("AI", font=f)
    d.text((gutter_x + (gutter_w - tw) / 2, (y0 + y1) / 2), "AI", fill="white", font=f, anchor="lm")
    if frame:
        d.rectangle([gutter_x + gutter_w, y0, x1, y0 + 2], fill=RED)
        d.rectangle([gutter_x + gutter_w, y1 - 2, x1, y1], fill=RED)


def cursor(d, x, y, s=1.6):
    p = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 23), (26, 23)]
    pts = [(x + a * s, y + b * s) for a, b in p]
    d.polygon(pts, fill="white", outline=(30, 30, 30))
    d.line(pts + [pts[0]], fill=(30, 30, 30), width=3)


def ripple(d, x, y, age, dur=0.6):
    """クリックの波紋。age=押してからの秒"""
    if 0 <= age < dur:
        r = 18 + age / dur * 44
        d.ellipse([x - r, y - r, x + r, y + r], outline=RED, width=5)


# ── 書き出し
def write_mp4(frame_fn, seconds, out, fps=FPS):
    """frame_fn(t) -> 1920x1080 の PIL 画像。ffmpeg に生フレームを流し込む（一時ファイルを作らない）"""
    out = pathlib.Path(out)
    n = int(round(seconds * fps))
    p = subprocess.Popen([ffmpeg(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out)],
                         stdin=subprocess.PIPE)
    for k in range(n):
        im = frame_fn(k / fps)
        assert im.size == (W, H), im.size
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg が失敗しました")
    print(f"{out}  {n}コマ / {n / fps:.1f}秒 / {out.stat().st_size / 1e6:.1f}MB")
    return out
