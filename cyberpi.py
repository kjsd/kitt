import cyberpi
import mbot2
import mbuild
import urequests
import json
import event
import time
import random
import gc

# 接続先Wi-Fiリスト: (SSID, パスワード) のタプルを優先順に記述
WIFI_LIST = [
    ("Your WiFi SSID 1", "Your Wifi passwd 1"),
    ("Your WiFi SSID 2", "Your Wifi passwd 2"),
]
WIFI_TIMEOUT = 10  # 1つのSSIDあたりの接続試行秒数
AGENT_URL = "kitt_agent server URL"
ID = "ID of this device provided by kitt_agent"

# ==========================================
# センサー初期化・床キャリブレーション
# ==========================================
BG_GRAY = 50  # 床の基準明度 (0-100)

def calibrate_sensors():
    global BG_GRAY
    try:
        # クアッドRGBセンサーの補助LEDを標準の白に初期化
        mbuild.quad_rgb_sensor.set_led("white", 1)
        time.sleep(0.2)

        # 起動時に置かれている床のグレースケール明度 (0-100) をサンプリング
        samples = []
        for _ in range(5):
            for ch in ("l1", "r1"):
                g = mbuild.quad_rgb_sensor.get_gray(ch, 1)
                if g is not None and g >= 0:
                    samples.append(g)
            time.sleep(0.05)

        if samples:
            avg = sum(samples) // len(samples)
            # 持ち上げられている場合 (極端に暗い場合) はデフォルト値50を維持
            BG_GRAY = avg if avg >= 10 else 50
            EXEC_ENV["BG_GRAY"] = BG_GRAY
            cyberpi.console.println("BG_GRAY: " + str(BG_GRAY))
    except Exception as e:
        print("Sensor init err:", e)

def is_black_line(ch="any", index=1):
    threshold = min(35, max(10, int(BG_GRAY * 0.65)))
    channels = ("l2", "l1", "r1", "r2") if ch == "any" else (ch,)
    for c in channels:
        if mbuild.quad_rgb_sensor.get_gray(c, index) < threshold:
            return True
    return False

def is_white_line(ch="any", index=1):
    threshold = max(60, min(92, int(BG_GRAY + max(15, (100 - BG_GRAY) * 0.4))))
    channels = ("l2", "l1", "r1", "r2") if ch == "any" else (ch,)
    for c in channels:
        if mbuild.quad_rgb_sensor.get_gray(c, index) > threshold:
            return True
    return False

# ==========================================
# メイン処理
# ==========================================
@event.start
def on_start():
    connect_wifi()

    cyberpi.console.clear()
    cyberpi.led.off('all')
    calibrate_sensors()

    while True:
        if not cyberpi.wifi.is_connected():
            connect_wifi()

        content = get_content()
        res = process(content)
        result(content, res)

        time.sleep(0.1)

# 実行用の基本環境（グローバルで使い回してメモリ節約）
EXEC_ENV = {
    "mbot2": mbot2,
    "mbuild": mbuild,
    "cyberpi": cyberpi,
    "time": time,
    "urequests": urequests,
    "json": json,
    "random": random,
    "BG_GRAY": BG_GRAY,
    "calibrate_sensors": calibrate_sensors,
    "is_black_line": is_black_line,
    "is_white_line": is_white_line
}

def process(content):
    if not content: return False
    if content.get("action") != "SystemAction": return False

    gc.collect() # 実行前GC
            
    res = True
    try:
        # EXEC_ENVを直接使い回す
        exec(content["parameter"], EXEC_ENV, EXEC_ENV)
    except Exception as e:
        print("Execution error:", e)
        cyberpi.console.println(e)
        res = False
                
    gc.collect() # 実行後GC
    return res

def get_content():
    try:
        # 送信
        url = AGENT_URL + "/kitts/" + ID + "/actions/pending"
        res = urequests.get(url)
        
        if res.status_code == 200:
            data = res.json()
            res.close()
            gc.collect() # JSONパース後のゴミ掃除
            return data
        else:
            print(res.text)
            res.close()
            time.sleep(1)
            return None
        
    except Exception as e:
        print("Err: ", e)
        cyberpi.console.println(e)
        time.sleep(1)
        return None

def result(content, success=True):
    if not content: return

    try:
        headers = {"Content-Type": "application/json; charset=utf-8"}

        if success:
            ep = "/complete"
        else:
            ep = "/fail"

        url = AGENT_URL + "/kitts/" + ID + "/actions/" + str(content["id"]) + ep
        res = urequests.post(url, headers=headers)
        
        if res.status_code == 200:
            data = res.json()
            res.close()
            gc.collect() # JSONパース後のゴミ掃除
            return data
        else:
            print(res.text)
            res.close()
            time.sleep(1)
            return None
        
    except Exception as e:
        print("Err: ", e)
        cyberpi.console.println(e)
        time.sleep(1)
        return None

# ==========================================
# Wi-Fi接続
# ==========================================
def connect_wifi():
    while not cyberpi.wifi.is_connected():
        for ssid, passwd in WIFI_LIST:
            cyberpi.console.println("Wi-Fi: " + ssid)
            cyberpi.wifi.connect(ssid, passwd)

            for _ in range(WIFI_TIMEOUT):
                if cyberpi.wifi.is_connected():
                    cyberpi.console.println("OK!")
                    return
                cyberpi.console.print(".")
                time.sleep(1)

            cyberpi.console.println("")
