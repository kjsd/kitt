import cyberpi
import urequests
import json
import time
import _thread
import gc

cyberpi.speech.set_recognition_address(url = "{NAVIGATEURL}")
cyberpi.speech.set_access_token(token = "{ACCESSTOKEN}")
cyberpi.driver.cloud_translate.TRANS_URL = "{TRANSURL}"
cyberpi.driver.cloud_translate.set_token("{ACCESSTOKEN}")
cyberpi.driver.cloud_translate.TTS_URL = "{TTSURL}"
cyberpi.driver.cloud_translate.set_token("{ACCESSTOKEN}")

led_t = 0

def led_task():
    global led_t
    while True:
        if led_t == 1:
            cyberpi.led.play('rainbow')
        elif led_t == 2:
            cyberpi.led.play('meteor_blue')
        elif led_t == 3:
            cyberpi.led.play('meteor_green')

        time.sleep(0.1)

# ==========================================
# Wi-Fi接続
# ==========================================
def connect_wifi():
    cyberpi.console.print("Wi-Fi...")
    cyberpi.led.on(50, 0, 0)
    
    cyberpi.wifi.connect(WIFI_SSID, WIFI_PASS)
    while not cyberpi.wifi.is_connected():
        time.sleep(1)
        
    cyberpi.console.println("OK!")
    cyberpi.led.on(0, 50, 0)
    time.sleep(1)

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
        res = urequests.post(AGENT_URL + "/talk", headers=headers, data=json_bytes)
        
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

# ==========================================
# メイン処理
# ==========================================
cyberpi.console.clear()
connect_wifi()

cyberpi.console.println("Press B to Speak")

_thread.start_new_thread(led_task, ())

while True:
    cyberpi.led.on(0, 0, 50) # 青色
    # Bボタンで音声認識開始
    if cyberpi.controller.is_press('b'):
        gc.collect()
        led_t = 2
        
        try:
            cyberpi.cloud.listen('japanese', 5)
            user_voice_text = cyberpi.cloud.listen_result()
        except:
            user_voice_text = ""
    
        # 2. 結果の確認
        if user_voice_text:
            led_t = 1
            print("Recognized:", user_voice_text) # PCログ用
            cyberpi.console.println("You: " + user_voice_text)
            
            res = talk(user_voice_text)
            replies = res.get("message", "No reply").split('\n')
            
            led_t = 3
            for x in replies:
                cyberpi.console.clear()
                cyberpi.console.println(x)
                en = cyberpi.cloud.translate("english", x)
            
                cyberpi.cloud.tts("zh", en)
        else:
            cyberpi.console.print(".")
        
        led_t = 0
        time.sleep(1)
