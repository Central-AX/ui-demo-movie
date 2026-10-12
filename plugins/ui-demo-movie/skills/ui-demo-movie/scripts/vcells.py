# -*- coding: utf-8 -*-
"""「空のスプレッドシート」と「全行入ったスプレッドシート」の2枚から、
行とセルの位置を差分で割り出す共通部品。

Googleスプレッドシートの罫線は薄すぎて拾えない（2026-10-02 実測）。
代わりに **2枚の差分＝データが入った場所** を見る。背景色（勤怠のピンク）も差分に出るので、
空の状態から見せたいセルだけ貼り足していけば、色つきの行も自然に「あとから点く」。
"""
import numpy as np


def _blocks(idx, gap):
    out, s = [], idx[0]
    for i in range(1, len(idx)):
        if idx[i] - idx[i - 1] > gap:
            out.append((s, idx[i - 1])); s = idx[i]
    out.append((s, idx[-1]))
    return out


def cells(empty, full, row_top, row_h, n_rows, col_gap=14, col_min=1, pad=3):
    """[(row_box, [cell_box, ...]), ...] を上から順に返す。box は (x0, y0, x1, y1)。

    行は**等間隔のグリッド**で切る。差分の切れ目で切ると、行の高さいっぱいに背景色が付いた行
    （勤怠のピンク）が隣とつながって2行が1行になる（2026-10-02 実測）。
    row_top / row_h は動画ごとに実測する（fit() の仕方が違うので共通化できない）。

    col_gap … これ以上 x が空いたら別のセル（セル内の字間より大きく、セル間の余白より小さく）
    pad     … 塗り残し防止に各 box を外へ広げる画素数
    """
    e = np.asarray(empty).astype(int)
    f = np.asarray(full).astype(int)
    assert e.shape == f.shape, (e.shape, f.shape)
    diff = np.abs(e - f).mean(axis=2) > 12

    out = []
    for i in range(n_rows):
        ry0 = int(round(row_top + i * row_h))
        ry1 = int(round(row_top + (i + 1) * row_h)) - 1
        xs = np.where(diff[ry0:ry1 + 1].sum(axis=0) > col_min)[0]
        if not len(xs):
            continue
        cs = [(int(a) - pad, ry0, int(b) + pad, ry1 + 1) for a, b in _blocks(list(xs), col_gap)]
        out.append(((int(xs.min()) - pad, ry0, int(xs.max()) + pad, ry1 + 1), cs))
    return out


def columns(rows, right_pad=8):
    """行ごとのセル位置から、全行で共通の列の境目を割り出す。

    背景に色が付いた行（勤怠のピンク）は差分が行全体につながってセルに割れないので、
    **割れた行の多数派から列を決めて、全行にその列を当てる**。
    """
    from statistics import median
    k = max({len(cs) for _, cs in rows}, key=lambda n: sum(len(cs) == n for _, cs in rows))
    sel = [cs for _, cs in rows if len(cs) == k]
    st = [median(cs[i][0] for cs in sel) for i in range(k)]
    en = [median(cs[i][2] for cs in sel) for i in range(k)]
    right = max(rb[2] for rb, _ in rows) + right_pad          # 長い文言（⚠…）まで入れる
    b = [st[0] - right_pad]
    b += [(en[i] + st[i + 1]) / 2 for i in range(k - 1)]
    b += [right]
    return [(int(b[i]), int(b[i + 1])) for i in range(k)]


def grid(empty, full, row_top, row_h, n_rows, cols):
    """(row_box, [cell_box…]) を、共通の列を当てた形で返す"""
    out = []
    for i in range(n_rows):
        y0 = int(round(row_top + i * row_h))
        y1 = int(round(row_top + (i + 1) * row_h))
        out.append(((cols[0][0], y0, cols[-1][1], y1),
                    [(c0, y0, c1, y1) for c0, c1 in cols]))
    return out


def state(empty, full, visible):
    """空の画面に、visible（box の一覧）だけ全行版から貼り足した画像を返す"""
    im = empty.copy()
    for b in visible:
        im.paste(full.crop(b), (b[0], b[1]))
    return im
