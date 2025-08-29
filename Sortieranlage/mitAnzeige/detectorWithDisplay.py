from jetson_inference import detectNet
from jetson_utils import videoSource, videoOutput
import time
import threading

# Modell und Kamera initialisieren
net = detectNet(
    model="../models/Sortierungv1_3/ssd-mobilenet.onnx",
    labels="../models/Sortierungv1_3/labels.txt",
    input_blob="input_0",
    output_cvg="scores",
    output_bbox="boxes",
    threshold=0.9
)
camera = videoSource("/dev/video0")
display = videoOutput("display://0")

# Globale Flag
run_detection = False

def display_loop():
    """permanente Anzeige"""
    global run_detection
    while display.IsStreaming():
        img = camera.Capture()
        if img is None:
            continue

        if run_detection:  # nur wenn Erkennung gewünscht
            detections = net.Detect(img)
        display.Render(img)
        display.SetStatus("Objekterkennung: ON" if run_detection else "Objekterkennung: OFF")

def detect_n_frames(n=5):
    """Objekterkennung n Frames lang aktivieren"""
    global run_detection
    run_detection = True
    all_detections = []

    for _ in range(n):
        img = camera.Capture()
        if img is None:
            continue
        detections = net.Detect(img)
        for det in detections:
            class_desc = net.GetClassDesc(det.ClassID)
            all_detections.append(class_desc.lower())
        time.sleep(0.01)

    run_detection = False  # danach wieder nur Kamera-Stream

    if not all_detections:
        return 4

    result = max(set(all_detections), key=all_detections.count)
    if result == "steckdose":
        return 1
    elif result == "unterputzdose":
        return 2
    elif result == "schraube_fehlt":
        return 3
    else:
        return 4

# Starten der Display-Schleife in eigenem Thread
threading.Thread(target=display_loop, daemon=True).start()
