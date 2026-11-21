"""Wake word test (openWakeWord 0.4.0). Say 'hey jarvis'. Prints scores above 0.3.

Usage: python wake_test.py [input_device_number]
"""
import sys
import time

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

FRAME = 1280  # 80 ms at 16 kHz
SECONDS = 20

import os
import openwakeword

model_file = os.path.join(
    os.path.dirname(openwakeword.__file__), "resources", "models", "hey_jarvis_v0.1.onnx"
)
if not os.path.isfile(model_file):
    raise SystemExit(f"model file not found: {model_file}")
paths = [model_file]

try:
    model = Model(wakeword_model_paths=paths)
except TypeError as err:
    print(f"plain load failed ({err}); retrying with inference_framework='onnx'")
    model = Model(wakeword_model_paths=paths, inference_framework="onnx")

device = int(sys.argv[1]) if len(sys.argv) > 1 else None
info = sd.query_devices(device if device is not None else sd.default.device[0])
print(f"mic: {info['name']}")

def open_stream(rate):
    return sd.InputStream(samplerate=rate, channels=1, dtype="int16",
                          blocksize=FRAME * (rate // 16000), device=device)

try:
    stream, factor = open_stream(16000), 1
    stream.start()
except Exception as err:
    print(f"16 kHz capture not available ({err}); using 48 kHz and averaging down")
    stream, factor = open_stream(48000), 3
    stream.start()

print(f"Listening for {SECONDS} seconds... say 'hey jarvis'")
peak = 0.0
end = time.time() + SECONDS
try:
    while time.time() < end:
        data, _ = stream.read(FRAME * factor)
        audio = data[:, 0]
        if factor > 1:
            audio = audio.reshape(-1, factor).astype(np.float32).mean(axis=1).astype(np.int16)
        scores = model.predict(audio)
        name, score = max(scores.items(), key=lambda kv: kv[1])
        peak = max(peak, score)
        if score > 0.3:
            print(f"{time.strftime('%H:%M:%S')}  {name} score={score:.2f}")
finally:
    stream.stop()
    stream.close()
print(f"done. highest score: {peak:.2f}")
