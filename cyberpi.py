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
LISTENING = 2
THINKING = 3
PLAYING = 4

led_t = NOT_READY

def state():
    global led_t
    return led_t
def fired(x):
    global led_t
    led_t = x
def state_loop():
    while True:
        x = state()
        if x == READY:
            cyberpi.led.on(0, 0, 50) # 青色
        elif x == LISTENING:
            cyberpi.led.play('meteor_blue')
        elif x == THINKING:
            cyberpi.led.play('rainbow')
        elif x == PLAYING:
            cyberpi.led.play('meteor_green')
        else:
            cyberpi.led.on(50, 0, 0)
        time.sleep(0.1)
    
# ==========================================
# メイン処理
# ==========================================
@event.start
def on_start():
    cyberpi.console.clear()
    fired(NOT_READY)

    cyberpi.speech.set_recognition_address(url = "{NAVIGATEURL}")
    cyberpi.speech.set_access_token(token = "{ACCESSTOKEN}")
    cyberpi.driver.cloud_translate.TRANS_URL = "{TRANSURL}"
    cyberpi.driver.cloud_translate.set_token("{ACCESSTOKEN}")
    cyberpi.driver.cloud_translate.TTS_URL = "{TTSURL}"
    cyberpi.driver.cloud_translate.set_token("{ACCESSTOKEN}")

    connect_wifi()

    fired(READY)
    cyberpi.console.println("Press B to Speak")

    state_loop()

# Bボタンで音声認識開始
@event.is_press('b')
def exec_talk():
    cyberpi.console.clear()
    cyberpi.console.println("Listening...")
    fired(LISTENING)
        
    gc.collect()
    try:
        cyberpi.cloud.listen('japanese', 5)
        user_voice_text = cyberpi.cloud.listen_result()
    except:
        user_voice_text = ""
            
    # 2. 結果の確認
    if user_voice_text:
        fired(THINKING)
        print("Recognized:", user_voice_text) # PCログ用
        cyberpi.console.clear()
        cyberpi.console.println("You: " + user_voice_text)
            
        res = talk(user_voice_text)
        replies = res.get("message", "No reply").split('\n')
            
        fired(PLAYING)
        for x in replies:
            cyberpi.console.clear()
            cyberpi.console.println(x)
            en = cyberpi.cloud.translate("english", x)
            
            cyberpi.cloud.tts("zh", en)
    else:
        cyberpi.console.print(".")
        
    fired(READY)

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

def talk(text):
    if not text:
        return {"message": "No Text"}

    data = {"text": text}
    
    try:
        # 日本語対応のためバイト列変換
        json_str = json.dumps(data)
        json_bytes = json_str.encode('utf-8')
        headers = {'Content-Type': 'application/json; charset=utf-8'}

        # 送信
        url = AGENT_URL + "/" + ID + "/talk"
        res = urequests.post(url, headers=headers, data=json_bytes)
        
        if res.status_code == 200:
            ret = res.json()
            return ret
        else:
            print(res.text)
            return {"message": "Err: " + str(res.status_code)}
            
        res.close()
        
    except Exception as e:
        print("Proxy Error:", e)
        return {"message": "Conn Fail"}

