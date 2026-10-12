# -*- coding: utf-8 -*-
"""場面（シーン）の部品。どれも「完成状態の実画面」を1枚（または空と完成の2枚）受け取り、
いったん消して、時間に合わせて出し直す。映る文字は実画面のまま。

  ScrollScene … 縦に長い画面を流す（「人がこれだけの量を見ていた」を見せる入口）
  FillScene   … 表のセルが1行ずつ埋まる。処理中の行に赤い「AI」（空と完成の2枚から差分で位置を取る）
  TypingScene … 文面が1行ずつ打たれる（キャレット付き）。最後に添付が付く
  StackScene  … 一覧に1件ずつ積まれる（古い＝下から）
  ClickScene  … カーソルがボタンへ動いて押す（人がやるのはここだけ、の場面）
  ChatScene   … チャットのメッセージが1つずつ出て、下へ送られる
  SideBySide  … 左に「渡すもの」、右に「記帳されたもの」を並べる（2つの場面を同時に動かす）

組み立ては render([scene, scene, ...], "out.mp4")。場面の切り替えは短いクロスフェード。
"""
import numpy as np
from PIL import Image, ImageDraw

import vcells
import vlib
from vlib import W, H, ss


class Scene:
    seconds = 3.0
    title = ""

    def screen(self, t):
        """実画面側（ラベル・枠の外側を含まない）を返す"""
        raise NotImplementedError

    def frame(self, t):
        im, dr = vlib.base()
        vlib.label(dr, self.title)
        vlib.place(im, dr, self.screen(t), getattr(self, "crop", None))
        return im


# ────────────────────────────────────────────
class ScrollScene(Scene):
    """縦長の画像を上から下へ流す。hold_start / hold_end 秒は止める"""

    def __init__(self, tall, title, seconds=5.2, hold_start=0.9, hold_end=0.5, view_aspect=None):
        self.tall, self.title, self.seconds = tall, title, seconds
        self.hold_start, self.hold_end = hold_start, hold_end
        aspect = view_aspect or (W / (vlib.BOTTOM - vlib.TOP))
        self.win = min(tall.height, int(tall.width / aspect))
        self.max_y = max(0, tall.height - self.win)

    def screen(self, t):
        span = self.seconds - self.hold_start - self.hold_end
        y = int(self.max_y * ss((t - self.hold_start) / max(0.01, span)))
        return self.tall.crop((0, y, self.tall.width, y + self.win))


# ────────────────────────────────────────────
class FillScene(Scene):
    """空の表（empty）と全部入った表（full）から、行とセルの位置を差分で割り出して1行ずつ埋める。

    row_top / row_h / n_rows … measure.py diff で取った値
    gutter_x … 赤い「AI」を出す行番号欄の左端（None なら表の左端から 58px 手前）
    alerts   … 最後に赤枠で囲む行の番号（0始まり）。例：残業45時間超の人
    speedup  … 1 より大きいと、後ろの行ほど速く埋まる（量が多いとき）
    """

    def __init__(self, empty, full, title, row_top, row_h, n_rows, crop=None,
                 start=0.45, per_row=0.52, per_cell=0.055, alerts=(), hold=1.6,
                 gutter_x=None, col_gap=14, speedup=1.0):
        self.empty, self.full, self.title, self.crop = empty, full, title, crop
        cols = vcells.columns(vcells.cells(empty, full, row_top, row_h, n_rows, col_gap=col_gap))
        self.rows = vcells.grid(empty, full, row_top, row_h, n_rows, cols)
        self.gutter_x = gutter_x if gutter_x is not None else cols[0][0] - 58
        self.alerts = alerts
        self.per_cell = per_cell
        # 行ごとの開始時刻（speedup>1 なら等比で詰める）
        self.t0, t, step = [], start, per_row
        for _ in self.rows:
            self.t0.append(t); t += step; step /= speedup
        self.fill_end = t + len(cols) * per_cell
        self.seconds = self.fill_end + (0.3 if alerts else 0) + hold

    def screen(self, t):
        vis, active = [], None
        for (rb, cs), t0 in zip(self.rows, self.t0):
            vis += [cb for k, cb in enumerate(cs) if t >= t0 + k * self.per_cell]
            if t0 <= t < t0 + len(cs) * self.per_cell + 0.18:
                active = rb
        im = vcells.state(self.empty, self.full, vis)
        d = ImageDraw.Draw(im)
        if active is not None:
            vlib.ai_chip(d, active, self.gutter_x)
        if t > self.fill_end + 0.2:
            for i in self.alerts:
                rb = self.rows[i][0]
                d.rectangle([self.gutter_x, rb[1] - 2, rb[2] + 4, rb[3] + 2], outline=vlib.RED, width=4)
        return im


# ────────────────────────────────────────────
class TypingScene(Scene):
    """完成した文面の画面（img）から、行を左→右に消しておき、順に打ち出す。

    lines  … 打つ順の行 [(y0, y1), ...]（measure.py lines で取る）
    x_range… 文字の載る x の範囲 (x0, x1)
    attach … 最後に出す添付の帯 (y0, y1)（無ければ None）
    """

    def __init__(self, img, title, lines, x_range, crop=None, per_line=0.17, start=0.5,
                 attach=None, hold=2.2, bg="white"):
        self.img, self.title, self.lines, self.crop = img, title, lines, crop
        self.x0, self.x1 = x_range
        self.per_line, self.start, self.attach, self.bg = per_line, start, attach, bg
        self.spans = [vlib.text_span(img, y0, y1, self.x0, self.x1) for y0, y1 in lines]
        self.type_end = start + len(lines) * per_line
        self.seconds = self.type_end + (0.9 if attach else 0) + hold

    def screen(self, t):
        im = self.img.copy()
        d = ImageDraw.Draw(im)
        for i, ((y0, y1), (tx0, tx1)) in enumerate(zip(self.lines, self.spans)):
            t0 = self.start + i * self.per_line
            frac = 0.0 if t <= t0 else min(1.0, (t - t0) / self.per_line)
            if frac < 1.0:
                cut = tx0 + (tx1 - tx0) * frac if frac > 0 else self.x0   # 打つ前は行ごと消す（文字の縁の薄い画素を残さない）
                d.rectangle([cut, y0 - 3, self.x1, y1 + 3], fill=self.bg)
                if frac > 0:
                    d.rectangle([cut + 1, y0 - 2, cut + 4, y1 + 2], fill=(60, 60, 60))
        if self.attach:
            ay0, ay1 = self.attach
            ta = self.type_end + 0.45
            if t < ta:
                d.rectangle([self.x0, ay0, self.x1, ay1], fill=self.bg)
            elif t < ta + 0.5:
                tx = vlib.text_span(self.img, ay0, ay1, self.x0, self.x1)[1]
                d.rounded_rectangle([self.x0 + 2, ay0 - 2, tx + 12, ay1 + 2], radius=8,
                                    outline=vlib.RED, width=4)
        return im


# ────────────────────────────────────────────
class StackScene(Scene):
    """一覧の行 rows=[(y0, y1), ...]（上から順）を、古い＝下から1件ずつ出す"""

    def __init__(self, img, title, rows, crop=None, start=0.55, step=0.62, hold=1.6,
                 from_bottom=True, bg="white"):
        self.img, self.title, self.rows, self.crop = img, title, rows, crop
        self.start, self.step, self.bg = start, step, bg
        self.order = list(reversed(rows)) if from_bottom else list(rows)
        self.seconds = start + len(rows) * step + hold

    def screen(self, t):
        im = self.img.copy()
        d = ImageDraw.Draw(im)
        for i, (y0, y1) in enumerate(self.order):
            if t < self.start + i * self.step:
                d.rectangle([0, y0, im.width, y1], fill=self.bg)
        return im


# ────────────────────────────────────────────
class ClickScene(Scene):
    """カーソルを start→button の中心へ運んで押す。pressed_fill を渡すとボタンを濃く塗り直す"""

    def __init__(self, img, title, start_xy, button_box, crop=None, move=(0.6, 2.2),
                 hold=1.6, pressed_fill=None):
        self.img, self.title, self.crop = img, title, crop
        self.sx, self.sy = start_xy
        self.btn = button_box
        self.ex, self.ey = (button_box[0] + button_box[2]) / 2, (button_box[1] + button_box[3]) / 2
        self.move, self.pressed_fill = move, pressed_fill
        self.seconds = move[1] + hold

    def screen(self, t):
        im = self.img.copy()
        d = ImageDraw.Draw(im)
        t0, t1 = self.move
        f = ss((t - t0) / (t1 - t0))
        cx, cy = self.sx + (self.ex - self.sx) * f, self.sy + (self.ey - self.sy) * f
        if self.pressed_fill and t > t1 + 0.25:
            # 押した後：ボタンの中身を残したまま、地の色だけ濃くする
            box = tuple(int(v) for v in self.btn)
            part = self.img.crop(box)
            a = np.asarray(part).astype(int)
            base = np.array(vlib.bg_of(self.img, box))
            mask = (np.abs(a - base).sum(axis=2) < 40)[..., None]
            a = np.where(mask, np.array(self.pressed_fill), a).astype(np.uint8)
            im.paste(Image.fromarray(a), box[:2])
        vlib.ripple(d, cx, cy, t - t1 - 0.25)
        vlib.cursor(d, cx, cy)
        return im


# ────────────────────────────────────────────
class ChatScene(Scene):
    """チャットの縦長スクショ tall と、各メッセージの上端 tops（+最後のメッセージの下端）を受け取り、
    times の時刻に1つずつ出す。新しいメッセージが下に来るよう自動でスクロールする。"""

    def __init__(self, tall, title, tops, times, seconds=None, panel_w=980, bg=None):
        assert len(tops) == len(times) + 1, "tops は メッセージ数+1（最後の下端）"
        self.tall, self.title, self.tops, self.times = tall, title, tops, times
        self.bg = bg or vlib.bg_of(tall, (0, tall.height - 20, tall.width, tall.height))
        self.pw = panel_w
        self.sc = panel_w / tall.width
        self.ph = vlib.BOTTOM - vlib.TOP
        self.view = int(self.ph / self.sc)
        self.seconds = seconds or times[-1] + 2.3
        self._cache = {}

    def _scroll(self, t):
        # 1/30秒刻みで追いかける（フレームを飛ばしても同じ位置になるよう、0から積分する）
        k = int(round(t * vlib.FPS))
        if k in self._cache:
            return self._cache[k]
        s = float(self.tops[0])
        for j in range(k + 1):
            shown = sum(1 for x in self.times if j / vlib.FPS >= x)
            bottom = self.tops[shown] if shown else self.tops[0]
            s += (max(self.tops[0], bottom + 30 - self.view) - s) * 0.25
        self._cache[k] = s
        return s

    def frame(self, t):
        T = self.tall
        shown = sum(1 for x in self.times if t >= x)
        bottom = self.tops[shown] if shown else self.tops[0]
        src = Image.new("RGB", (T.width, T.height + 400), self.bg)
        if shown:
            src.paste(T.crop((0, 0, T.width, bottom)), (0, 0))
            age = t - self.times[shown - 1]
            if age < 0.15:                           # 出たばかりのメッセージはふわっと出す
                top = self.tops[shown - 1]
                blend = Image.blend(Image.new("RGB", (T.width, bottom - top), self.bg),
                                    T.crop((0, top, T.width, bottom)), age / 0.15)
                src.paste(blend, (0, top))
        y = int(self._scroll(t))
        view = src.crop((0, y, T.width, y + self.view)).resize((self.pw, self.ph), Image.LANCZOS)
        im, dr = vlib.base()
        vlib.label(dr, self.title)
        px = (W - self.pw) // 2
        dr.rectangle([px - 2, vlib.TOP - 2, px + self.pw + 1, vlib.TOP + self.ph + 1], outline=vlib.LINE, width=2)
        im.paste(view, (px, vlib.TOP))
        return im


# ────────────────────────────────────────────
class SideBySide(Scene):
    """左に入口（名刺の写真・レシート・ドライブ等）、右に記帳先（表）。2つの場面を同じ時間で動かす。
    ratio … 左の幅の割合"""

    def __init__(self, left, right, title, ratio=0.4, gap=28):
        self.left, self.right, self.title = left, right, title
        self.ratio, self.gap = ratio, gap
        self.seconds = max(left.seconds, right.seconds)

    def frame(self, t):
        im, dr = vlib.base()
        vlib.label(dr, self.title)
        split = int(56 + (W - 112) * self.ratio)
        vlib.place(im, dr, self.left.screen(t), getattr(self.left, "crop", None), left=56, right=split - self.gap // 2)
        vlib.place(im, dr, self.right.screen(t), getattr(self.right, "crop", None), left=split + self.gap // 2, right=W - 56)
        return im


# ────────────────────────────────────────────
def render(scenes, out, xfade=0.45):
    """場面を順につなぐ。切り替えの xfade 秒は前後を重ねてクロスフェード"""
    starts, t = [], 0.0
    for s in scenes:
        starts.append(t); t += s.seconds
    total = t

    def frame(t):
        i = max(k for k, st in enumerate(starts) if t >= st)
        s, local = scenes[i], t - starts[i]
        im = s.frame(local)
        if i + 1 < len(scenes) and local > s.seconds - xfade:
            nxt = scenes[i + 1].frame(0.0)
            im = Image.blend(im, nxt, ss((local - (s.seconds - xfade)) / xfade))
        return im

    return vlib.write_mp4(frame, total, out)


def preview(scenes, out_png, per_scene=4):
    """書き出す前の確認用。各場面から per_scene コマを抜いて1枚に並べる（消す場所がずれていないかを見る）"""
    shots = []
    for s in scenes:
        for k in range(per_scene):
            shots.append(s.frame(s.seconds * (k + 0.5) / per_scene))
    tw, th = W // 4, H // 4
    sheet = Image.new("RGB", (tw * per_scene, th * len(scenes)), "white")
    for i, im in enumerate(shots):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), ((i % per_scene) * tw, (i // per_scene) * th))
    sheet.save(out_png)
    print(f"preview: {out_png}")
    return out_png
