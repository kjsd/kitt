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
        # 超音波センサーの青色LEDを一旦消灯し、クアッドRGBセンサーの補助LEDを白に初期化
        mbuild.ultrasonic2.set_bri(0, 1)
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

# 発話中の正面超音波LED（＋本体赤LED）チカチカ点滅演出
def talk_led(sec=3.0):
    try:
        steps = max(1, int(sec / 0.25))
        for _ in range(steps):
            if stop_requested or is_manual_running:
                break
            mbuild.ultrasonic2.set_bri(100, 1)
            cyberpi.led.on(255, 0, 0)
            time.sleep(0.13)
            if stop_requested or is_manual_running:
                break
            mbuild.ultrasonic2.set_bri(10, 1)
            cyberpi.led.on(60, 0, 0)
            time.sleep(0.12)
        mbuild.ultrasonic2.set_bri(0, 1)
        cyberpi.led.off('all')
    except Exception as e:
        print("talk_led err:", e)

# ==========================================
# ボタン手動アクション（緊急入場 / 緊急停止）
# ==========================================
is_manual_running = False
stop_requested = False

# Bボタン: 緊急用の手動入場動作（障害物検知まで全速前進 → 右90度ドリフトターン停止）
@event.is_press('b')
def on_button_b():
    global is_manual_running, stop_requested
    if is_manual_running:
        return
    is_manual_running = True
    stop_requested = False
    try:
        cyberpi.led.on(255, 0, 0)
        cyberpi.console.println("STAGE IN: MAX SPEED")
        mbot2.drive_speed(200, -200)
        while True:
            if stop_requested or cyberpi.controller.is_press('a'):
                mbot2.drive_speed(0, 0)
                break
            dist = mbuild.ultrasonic2.get(1)
            if dist > 0 and dist < 50:
                cyberpi.led.on(255, 165, 0)
                cyberpi.console.println("DRIFT TURN!")
                mbot2.drive_speed(200, -40)
                time.sleep(0.15)
                mbot2.drive_speed(200, 200)
                time.sleep(0.15)
                mbot2.drive_speed(0, 0)
                break
            time.sleep(0.05)

        mbot2.drive_speed(0, 0)
        if not stop_requested:
            cyberpi.led.on(0, 0, 255)
            time.sleep(1)
        cyberpi.led.off('all')
    except Exception as e:
        print("Manual B err:", e)
        cyberpi.console.println(e)
    finally:
        mbot2.drive_speed(0, 0)
        is_manual_running = False

# Aボタン: 緊急停止 ＆ 床センサー再キャリブレーション
@event.is_press('a')
def on_button_a():
    global stop_requested
    stop_requested = True
    mbot2.drive_speed(0, 0)
    cyberpi.led.off('all')
    cyberpi.console.println("STOP & CALIBRATE")
    calibrate_sensors()

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
        if is_manual_running:
            time.sleep(0.1)
            continue

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
    "is_white_line": is_white_line,
    "talk_led": talk_led
}

def process(content):
    if not content: return False
    if content.get("action") != "SystemAction": return False

    gc.collect() # 実行前GC
            
    res = True
    try:
        try:
            mbuild.ultrasonic2.set_bri(100, 1)
        except Exception:
            pass
        # EXEC_ENVを直接使い回す
        exec(content["parameter"], EXEC_ENV, EXEC_ENV)
    except Exception as e:
        print("Execution error:", e)
        cyberpi.console.println(e)
        res = False
    finally:
        try:
            mbuild.ultrasonic2.set_bri(0, 1)
        except Exception:
            pass
                
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
            while is_manual_running:
                time.sleep(0.1)

            cyberpi.console.println("Wi-Fi: " + ssid)
            cyberpi.wifi.connect(ssid, passwd)

            for _ in range(WIFI_TIMEOUT):
                while is_manual_running:
                    time.sleep(0.1)
                if cyberpi.wifi.is_connected():
                    cyberpi.console.println("OK!")
                    return
                cyberpi.console.print(".")
                time.sleep(1)

            cyberpi.console.println("")
