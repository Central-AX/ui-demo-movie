# ui-demo-movie

業務AIの「実演動画」を、実画面のスクショから作る Claude Code skill です。録画は要りません。
スプレッドシートに1行ずつ書き込まれる・メール文面が打たれる・人が送信を押す、といった動きを 1920x1080 の MP4 にします。

## インストール

Claude Code で次の2行を実行します。

```
/plugin marketplace add Central-AX/ui-demo-movie
/plugin install ui-demo-movie@ui-demo-movie
```

## 使い方

- Claude Code に「実演動画を作って」と頼むと起動します
- 実画面のスクショ（空の状態と完成した状態の2枚）を渡すと、AIが書き込んでいるように動く動画になります
- 「ui-demo-movie のサンプル動画を作って」と頼むと、架空データのサンプル（約15秒）を作って動作を確認できます

## 必要なもの

- Python 3（Pillow・numpy）
- ffmpeg（Mac: `brew install ffmpeg` ／ Windows: `winget install ffmpeg` ／ どちらでも: `pip install imageio-ffmpeg`）

詳しい手順は [SKILL.md](plugins/ui-demo-movie/skills/ui-demo-movie/SKILL.md) を参照してください。

## 更新

```
/plugin marketplace update ui-demo-movie
```
