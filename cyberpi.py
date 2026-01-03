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
    cyberpi.console.clear()
    cyberpi.led.off('all')

    connect_wifi()

    while True:
        content = get_content()
        res = process(content)
        result(content, res)

        time.sleep(0.1)

def process(content):
    if not content: return False
    if content["action"] != "SystemAction": return False

    # 実行用の基本環境（サンドボックス）
    base_env = {
        "mbot2": mbot2,
        "mbuild": mbuild,
        "cyberpi": cyberpi,
        "time": time,
        "urequests": urequests,
        "json": json,
        "random": random
    }

    cyberpi.console.println(content["parameter"])
    gc.collect() # 実行前GC
            
    # アクションごとに環境をコピーして汚染を防ぐ
    exec_env = base_env.copy()

    res = True
    try:
        exec(content["parameter"], exec_env, exec_env)
    except Exception as e:
        print("Execution error:", e)
        cyberpi.console.println(e)
        res = False
                
    # メモリ解放
    exec_env = None
    gc.collect() 

    return res

def get_content():
    try:
        # 送信
        url = AGENT_URL + "/" + ID + "/actions/pending"
        res = urequests.get(url)
        
        if res.status_code == 200:
            return res.json()
        else:
            print(res.text)
            #cyberpi.console.println("Err: " + str(res.status_code))
            time.sleep(1)

            return None
            
        res.close()
        
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

        url = AGENT_URL + "/" + ID + "/actions/" + str(content["id"]) + ep
        res = urequests.post(url, headers=headers)
        
        if res.status_code == 200:
            return res.json()
        else:
            print(res.text)
            cyberpi.console.println("Err: " + str(res.status_code))
            time.sleep(1)
            return None
            
        res.close()
        
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
