import cyberpi
import urequests
import json
import event
import time
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
            cyberpi.led.play('rainbow')
        elif x == PLAYING:
            cyberpi.led.play('meteor_blue')
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
        exec(content)
        complete(content)

        time.sleep(0.1)

def exec(content):
    if not content: return

    actions = content.get("system_actions", [])
    
    for x in actions:
        action = x.get("action")
        param = x.get("parameter")
        p = None
        u = None
        
        if action == "MoveForward":
            if param.endswith("s"):
                p = float(param.replace("s", ""))
                u = "s"
            elif param.endswith("cm"):
                p = float(param.replace("cm", ""))
                u = "cm"

            hdl_move_forward(p, u)
            
        elif action == "MoveBackward":
            if param.endswith("s"):
                p = float(param.replace("s", ""))
                u = "s"
            elif param.endswith("cm"):
                p = float(param.replace("cm", "")) 
                u = "s"

            hdl_move_backward(p, u)
        
        elif action == "TurnLeft":
            if param.endswith("s"):
                p = float(param.replace("s", "")) 
                u = "s"
            elif param.endswith("deg"):
                p = float(param.replace("deg", "")) 
                u = "deg"

            hdl_turn_left(p, u)
        
        elif action == "TurnRight":
            if param.endswith("s"):
                p = float(param.replace("s", "")) 
                u = "s"
            elif param.endswith("deg"):
                p = float(param.replace("deg", "")) 
                u = "deg"

            hdl_turn_right(p, u)
        
        elif action == "Stop":
            hdl_stop()


def hdl_move_forward(param, unit):
    cyberpi.console.println("MoveFoward: " + str(param) + str(unit))
    fired(PLAYING)

def hdl_move_backward(param, unit):
    cyberpi.console.println("MoveBackard: " + str(param) + str(unit))
    fired(PLAYING)

def hdl_turn_left(param, unit):
    cyberpi.console.println("TurnLeft: " + str(param) + str(unit))
    fired(PLAYING)

def hdl_turn_right(param, unit):
    cyberpi.console.println("TurnRight: " + str(param) + str(unit))
    fired(PLAYING)

def hdl_stop():
    cyberpi.console.println("Stop")
    fired(PLAYING)

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

def complete(content):
    if not content: return

    try:
        headers = {'Content-Type': 'application/json; charset=utf-8'}

        # 送信
        url = AGENT_URL + "/" + ID + "/actions/" + str(content["id"]) + "/complete"
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
