# Kitt Client for mBot2

Makeblock mBot2 (CyberPi) 用のクライアントプログラムです。[KittAgent](https://github.com/ditsmod/kitt_agent) の `SystemActions` キューから物理的な動作命令を受け取り、実行します。

## 機能概要

* **Wi-Fi 接続**: 起動時に設定された Wi-Fi アクセスポイントへ自動接続します。
* **ポーリング実行**: 定期的に KittAgent サーバーへ問い合わせ (`GET /<ID>/actions/pending`)、未実行のアクションを取得します。
* **動的コード実行**: サーバーから受信した MicroPython コード (`SystemAction`) をデバイス上で動的に実行 (`exec`) します。
* **結果通知**: 実行の成功/失敗をサーバーへ通知 (`POST /complete` or `/fail`) します。

## ファイル構成

* `cyberpi.py`: CyberPi 上で動作する MicroPython のメインスクリプト。
* `kitt.mblock`: mBlock IDE 用のプロジェクトファイル（内容は `cyberpi.py` と同等）。

## セットアップ手順

### 1. 構成変数の設定

`cyberpi.py` の先頭にある以下の変数を環境に合わせて書き換えてください。

```python
WIFI_SSID = "Your WiFi SSID"   # Wi-FiのSSID
WIFI_PASS = "Your Wifi passwd" # Wi-Fiのパスワード
AGENT_URL = "http://192.168.1.10:4000/api/devices" # KittAgentサーバーのAPIエンドポイント
ID = "mbot-01"                 # KittAgent側で登録したこのデバイスのID
```

> **注意**: `AGENT_URL` は KittAgent サーバーのベースURLに合わせてください。例: `http://<server-ip>:4000/api/devices`

### 2. デバイスへの書き込み

#### mBlock IDE を使用する場合
1. `kitt.mblock` を mBlock (PC版またはWeb版) で開きます。
2. Pythonエディタモードに切り替え、コードが `cyberpi.py` の内容と一致しているか確認・更新します。
3. mBot2 (CyberPi) をPCに接続し、「アップロード」を実行します。

#### 直接転送する場合
CyberPi のファイルシステムへアクセスできるツールを使用し、`cyberpi.py` を `main.py` として、または適切なブートシーケンスで読み込まれるように転送してください。

## 動作の仕組み

1. **起動**: コンソール画面がクリアされ、LEDが消灯します。Wi-Fi接続を試行し、接続状況をコンソールに表示します。
2. **待機ループ**:
   - サーバーから JSON 形式のアクションを取得します。
   - `action` タイプが `"SystemAction"` の場合、`parameter` に含まれる Python コード文字列を取り出します。
   - サンドボックス環境（`mbot2`, `cyberpi` モジュールなどが利用可能）でコードを `exec()` します。
   - 実行前後にガベージコレクション (`gc.collect()`) を行い、メモリ不足を防ぎます。
3. **エラーハンドリング**:
   - ネットワークエラーやコード実行エラーが発生した場合、コンソールにエラー内容を表示し、サーバーへ失敗を通知します。

## 開発者向け情報

### 利用可能なモジュール
受信したコード内で以下のモジュールが利用可能です：
- `mbot2`
- `mbuild`
- `cyberpi`
- `urequests`
- `json`
- `event`
- `time`
- `random`

### メモリ管理
CyberPi はメモリリソースが限られているため、大きなアクションを実行するとメモリ不足（MemoryError）になる可能性があります。スクリプトでは実行ごとに `gc.collect()` を呼び出して対策しています。
