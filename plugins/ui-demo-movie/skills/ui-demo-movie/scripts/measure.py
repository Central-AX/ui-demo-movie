# -*- coding: utf-8 -*-
"""座標を画素から取る道具。**スクショにルーラーを重ねて目で読まない**（行が2/3行・列が200pxずれた実例あり）。

使い方：
  python measure.py diff  empty.png full.png        … 空と完成の差分から「データが入った行」を出す → FillScene の row_top/row_h/n_rows
  python measure.py lines img.png X0 X1 [Y0 Y1]      … その x 範囲で文字が載っている行の (y0, y1) → TypingScene / StackScene の行
  python measure.py hlines img.png X0 X1 [Y0 Y1]     … 横罫線の y（罫線が見える表のとき）
  python measure.py bands img.png                    … 地の色が変わる帯（一覧の行・メッセージの区切りの目安）
  python measure.py size img.png

出た座標は必ず `python measure.py` の後に preview（check.py）で、消える場所が合っているか目で確かめる。
"""
import sys
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def _gray(path):
    return np.asarray(Image.open(path).convert("L")).astype(int)


def _runs(idx, gap=1):
    if not len(idx):
        return []
    out, s, p = [], idx[0], idx[0]
    for v in idx[1:]:
        if v - p > gap:
            out.append((int(s), int(p))); s = v
        p = v
    out.append((int(s), int(p)))
    return out


def diff_rows(empty, full, thresh=12, min_px=2):
    e = np.asarray(Image.open(empty).convert("RGB")).astype(int)
    f = np.asarray(Image.open(full).convert("RGB")).astype(int)
    assert e.shape == f.shape, f"2枚の大きさが違います {e.shape} {f.shape}（同じ位置・同じ倍率で撮り直す）"
    d = np.abs(e - f).mean(axis=2) > thresh
    ys = np.where(d.sum(axis=1) >= min_px)[0]
    return _runs(ys, gap=2), d


def text_rows(img, x0, x1, y0=0, y1=None, dark=150, gap=3):
    g = _gray(img)
    y1 = y1 or g.shape[0]
    ys = np.where((g[y0:y1, x0:x1] < dark).sum(axis=1) > 0)[0] + y0
    return _runs(ys, gap=gap)


def hlines(img, x0, x1, y0=0, y1=None, dark=232, ratio=0.85):
    g = _gray(img)
    y1 = y1 or g.shape[0]
    need = int((x1 - x0) * ratio)
    return [y for y in range(y0, y1) if (g[y, x0:x1] < dark).sum() >= need]


def bands(img, x=None):
    a = np.asarray(Image.open(img).convert("RGB")).astype(int)
    x = x if x is not None else a.shape[1] // 2
    col = a[:, max(0, x - 10):x + 10].mean(axis=1)
    out, s = [], 0
    for y in range(1, len(col)):
        if np.abs(col[y] - col[y - 1]).sum() > 18:
            out.append((s, y - 1)); s = y
    out.append((s, len(col) - 1))
    return [(a_, b_) for a_, b_ in out if b_ - a_ >= 6]


def main(argv):
    if len(argv) < 2:
        print(__doc__); return
    cmd, *rest = argv[1:]
    if cmd == "size":
        print(Image.open(rest[0]).size)
    elif cmd == "diff":
        rows, d = diff_rows(rest[0], rest[1])
        print(f"差分の帯 {len(rows)}本（上端, 下端, 高さ）")
        for r in rows:
            xs = np.where(d[r[0]:r[1] + 1].any(axis=0))[0]
            print(f"  {r[0]:5d} – {r[1]:5d}  h={r[1] - r[0] + 1:3d}   x={xs.min()}–{xs.max()}")
        if len(rows) >= 2:
            tops = [r[0] for r in rows]
            steps = np.diff(tops)
            h = float(np.median(steps))
            print(f"\n→ 行の間隔（中央値） row_h ≈ {h:.2f}")
            print(f"→ row_top は1行目の帯の上端から、行の上の罫線までさかのぼった値（目安 {tops[0] - h * 0.2:.0f}）")
            print(f"→ n_rows = {len(rows)}（色付きの行が隣とつながって本数が少ないときは、高さ h の倍数で割る）")
    elif cmd == "lines":
        x0, x1 = int(rest[1]), int(rest[2])
        y0 = int(rest[3]) if len(rest) > 3 else 0
        y1 = int(rest[4]) if len(rest) > 4 else None
        rows = text_rows(rest[0], x0, x1, y0, y1)
        print(f"文字の行 {len(rows)}本 (y0, y1)")
        print(rows)
    elif cmd == "hlines":
        x0, x1 = int(rest[1]), int(rest[2])
        y0 = int(rest[3]) if len(rest) > 3 else 0
        y1 = int(rest[4]) if len(rest) > 4 else None
        print(hlines(rest[0], x0, x1, y0, y1))
    elif cmd == "bands":
        for b in bands(rest[0]):
            print(b)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
