import websocket
import json

AUDIO_OUTPUT = "radio_audio_stream.raw"

def on_message(ws, message):
    if isinstance(message, bytes):
        print(f"[+] Received {len(message)} bytes of audio data")
        with open(AUDIO_OUTPUT, "ab") as f:
            f.write(message)
    else:
        print(f"[i] Text message: {message}")

def on_open(ws):
    print("[*] WebSocket connected, tuning...")
    ws.send("SERVER DE CLIENT client=openwebrx.js type=receiver")

    # Optional: noise reduction
    ws.send(json.dumps({
        "type": "connectionproperties",
        "params": {"nr_enabled": True}
    }))

    # Select a profile if needed
    # ws.send(json.dumps({
    #     "type": "selectprofile",
    #     "params": {"profile": "417be9c6-cb3f-48..."} 
    # }))

    # Set DSP filter
    ws.send(json.dumps({
        "type": "dspcontrol",
        "params": {"low_cut": -4000, "high_cut": 4000}
    }))

    # Apply frequency offset
    ws.send(json.dumps({
        "type": "dspcontrol",
        "params": {"offset_freq": -2200000}
    }))

    # Start DSP
    ws.send(json.dumps({
        "type": "dspcontrol",
        "action": "start"
    }))


def on_error(ws, error):
    print(f"[!] WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"[*] WebSocket closed: {close_status_code}, {close_msg}")

if __name__ == "__main__":
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(
        "ws://mayzus.ddns.net:8073/ws/",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    print("[*] Connecting to radio stream...")
    ws.run_forever()
