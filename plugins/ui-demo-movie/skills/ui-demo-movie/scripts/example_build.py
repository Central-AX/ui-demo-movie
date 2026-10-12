# -*- coding: utf-8 -*-
"""ひな形 兼 動作確認。素材が無くても動くように、架空の「レシート」「台帳（空・完成）」「メール下書き」
をその場で描いて、実演動画を1本作る。

  python example_build.py            → example_out/example.mp4 と example_out/preview.png

本番では「素材を描く」部分を消して、実画面のスクショ（空の状態・完成の状態）を読み込むだけにする。
座標（ROW_TOP など）は measure.py で取る。ここでは描いた本人なので座標が分かっているが、
本番のスクショでは必ず measure.py の出力を貼る。
"""
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from PIL import Image, ImageDraw

import vlib, scenes, measure

OUT = HERE / "example_out"
OUT.mkdir(exist_ok=True)

# ════════ 架空の素材を描く（本番ではここが実画面のスクショになる） ════════
F = vlib.font(22, bold=False)
FB = vlib.font(22)
ROWS = [  # 日付, 支払先, 科目, 金額, 税区分（全部架空）
    ("9/02", "サンプル文具店", "消耗品費", "3,300", "課税10%"),
    ("9/04", "みどり珈琲", "会議費", "1,540", "軽減8%"),
    ("9/05", "サンプル交通", "旅費交通費", "2,860", "課税10%"),
    ("9/09", "あおば書店", "新聞図書費", "2,420", "課税10%"),
    ("9/11", "サンプル電機", "消耗品費", "8,980", "課税10%"),
    ("9/12", "みどり珈琲", "会議費", "990", "軽減8%"),
    ("9/16", "サンプル交通", "旅費交通費", "1,320", "課税10%"),
    ("9/18", "ひかり印刷", "広告宣伝費", "16,500", "課税10%"),
    ("9/22", "サンプル文具店", "消耗品費", "770", "課税10%"),
    ("9/25", "あおば書店", "新聞図書費", "1,980", "課税10%"),
]
COLX = [80, 200, 470, 690, 850]
SW, SH = 1100, 120 + 34 * (len(ROWS) + 1)
ROW_TOP0, ROW_H0 = 114, 34


def sheet(filled):
    im = Image.new("RGB", (SW, SH), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, SW, 40], fill=(241, 243, 244))
    d.text((16, 8), "仕訳帳_2026年9月（架空データ）", fill=(60, 64, 67), font=FB)
    d.rectangle([0, 80, SW, ROW_TOP0], fill=(232, 240, 254))
    for x, h in zip(COLX, ["日付", "支払先", "科目", "金額", "税区分"]):
        d.text((x, 86), h, fill=(32, 33, 36), font=FB)
    for i in range(len(ROWS) + 1):
        y = ROW_TOP0 + i * ROW_H0
        d.line([0, y, SW, y], fill=(218, 220, 224))
        if i < len(ROWS):
            d.text((20, y + 7), str(i + 1), fill=(128, 134, 139), font=F)
    d.line([60, 80, 60, SH], fill=(218, 220, 224))
    if filled:
        for i, r in enumerate(ROWS):
            for x, v in zip(COLX, r):
                d.text((x, ROW_TOP0 + i * ROW_H0 + 7), v, fill=(32, 33, 36), font=F)
    return im


def receipts_pile():
    im = Image.new("RGB", (520, 640), (214, 210, 202))
    d = ImageDraw.Draw(im)
    for k, r in enumerate(ROWS[:4]):
        x, y = 40 + k * 18, 40 + k * 26
        d.rectangle([x, y, x + 380, y + 520], fill="white", outline=(200, 200, 200))
        d.text((x + 30, y + 30), r[1], fill=(30, 30, 30), font=FB)
        d.text((x + 30, y + 80), f"2026/{r[0]}", fill=(80, 80, 80), font=F)
        d.text((x + 30, y + 420), f"合計  ¥{r[3]}", fill=(30, 30, 30), font=FB)
    return im


def mail():
    im = Image.new("RGB", (1100, 560), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1100, 44], fill=(242, 246, 252))
    d.text((20, 10), "新規メッセージ", fill=(32, 33, 36), font=FB)
    lines = ["宛先  keiri@example.com", "件名  9月分の経費精算（10件）",
             "経理ご担当者様", "", "9月分の経費精算を、仕訳帳の形でお送りします。",
             "件数は10件、合計は 40,660円 です。", "レシートの写真は共有ドライブに入れてあります。", "",
             "どうぞよろしくお願いいたします。"]
    y = 64
    for ln in lines:
        d.text((24, y), ln, fill=(32, 33, 36), font=F); y += 38
    d.rounded_rectangle([24, 420, 380, 460], radius=6, outline=(218, 220, 224), fill=(248, 249, 250))
    d.text((40, 428), "仕訳帳_2026年9月.csv", fill=(32, 33, 36), font=F)
    d.rounded_rectangle([24, 490, 140, 536], radius=22, fill=(11, 87, 208))
    d.text((56, 500), "送信", fill="white", font=FB)
    return im


EMPTY, FULL = sheet(False), sheet(True)
MAIL = mail()
for name, im in [("empty", EMPTY), ("full", FULL), ("receipts", receipts_pile()), ("mail", MAIL)]:
    im.save(OUT / f"{name}.png")

# ════════ 座標を画素から取る（本番も同じ手順） ════════
rows, _ = measure.diff_rows(OUT / "empty.png", OUT / "full.png")
assert len(rows) == len(ROWS), rows                 # 10行ぶんの差分が出ること
mail_lines = measure.text_rows(OUT / "mail.png", 20, 1080, 50, 400)
ay0, ay1 = measure.text_rows(OUT / "mail.png", 30, 400, 418, 462)[0]
attach = (ay0 - 18, ay1 + 8)                        # 文字の行＋添付の枠線ぶん広げる（枠が残ったら広げる）

# ════════ 場面を組む ════════
receipts = Image.open(OUT / "receipts.png").convert("RGB")


class Still(scenes.Scene):
    """入口の画像をそのまま置く（左側用）"""
    def __init__(self, img, seconds):
        self.img, self.seconds = img, seconds

    def screen(self, t):
        return self.img


fill = scenes.FillScene(EMPTY, FULL, "", row_top=ROW_TOP0, row_h=ROW_H0, n_rows=len(ROWS),
                        gutter_x=4, alerts=(7,), speedup=1.12)
S = [
    scenes.SideBySide(Still(receipts, fill.seconds), fill, "AIがレシートを読んで、仕訳帳に書き込む", ratio=0.32),
    scenes.TypingScene(MAIL, "AIが送り状を書いて、仕訳帳を添付する", mail_lines, (20, 1080),
                       attach=attach, per_line=0.2),
    scenes.ClickScene(MAIL, "人は確かめて、送信を押すだけ", (900, 300), (24, 490, 140, 536),
                      pressed_fill=(8, 48, 120)),
]
scenes.preview(S, OUT / "preview.png")
scenes.render(S, OUT / "example.mp4")
