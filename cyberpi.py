import cyberpi
import mbot2
import urequests
import json
import event
import time
import random
import _thread
import gc

WIFI_SSID = "Your WiFi SSID"
WIFI_PASS = "Your Wifi passwd"
AGENT_URL = "kitt_agent server URL"
ID = "ID of this device provided by kitt_agent"

NOT_READY = None
READY = 1
THINKING = 2
PLAYING = 3

led_t = NOT_READY

def state():
    global led_t
    return led_t
def fired(x):
    global led_t
    led_t = x
def led_task():
    while True:
        x = state()
        if x == READY:
            cyberpi.led.on(0, 0, 50) # 青色
        elif x == THINKING:
            cyberpi.led.play("rainbow")
        elif x == PLAYING:
            cyberpi.led.play("meteor_blue")
        else:
            cyberpi.led.on(50, 0, 0)
        time.sleep(0.1)
    
# ==========================================
# メイン処理
# ==========================================
@event.start
def on_start():
    cyberpi.console.clear()
    _thread.start_new_thread(led_task, ())
    fired(NOT_READY)

    connect_wifi()
    cyberpi.console.println("Ready to action")

    while True:
        fired(READY)
        content = get_content()
        res = process(content)
        result(content, res)

        time.sleep(0.1)

def process(content):
    if not content: return False

    fired(PLAYING)
    actions = content.get("system_actions", [])
    res = True
    
    # 実行用の基本環境（サンドボックス）
    base_env = {
        "mbot2": mbot2,
        "cyberpi": cyberpi,
        "time": time,
        "event": event,
        "urequests": urequests,
        "json": json,
        "random": random
    }

    for x in actions:
        if x["action"] == "ExecuteCode":
            cyberpi.console.println(x["parameter"])
            gc.collect() # 実行前GC
            
            # アクションごとに環境をコピーして汚染を防ぐ
            exec_env = base_env.copy()
            
            try:
                exec(x["parameter"], exec_env, exec_env)
            except Exception as e:
                print("Execution error:", e)
                cyberpi.console.println(e)
                res = False
            
            # メモリ解放
            exec_env = None
            gc.collect() 
        else:
            res = False

    return res

def get_content():
    fired(THINKING)

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
