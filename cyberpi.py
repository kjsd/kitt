import cyberpi
import mbot2
import mbuild
import urequests
import json
import event
import time
import random
import gc

WIFI_SSID = "Your WiFi SSID"
WIFI_PASS = "Your Wifi passwd"
AGENT_URL = "kitt_agent server URL"
ID = "ID of this device provided by kitt_agent"

# ==========================================
# メイン処理
# ==========================================
@event.start
def on_start():
    connect_wifi()

    cyberpi.console.clear()
    cyberpi.led.off('all')

    while True:
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
    "random": random
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
    cyberpi.console.print("Wi-Fi...")
    
    cyberpi.wifi.connect(WIFI_SSID, WIFI_PASS)
    while not cyberpi.wifi.is_connected():
        cyberpi.console.print(".")
        time.sleep(1)
        
    cyberpi.console.println("OK!")
