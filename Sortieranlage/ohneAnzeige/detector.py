from jetson_inference import detectNet
from jetson_utils import videoSource, videoOutput
import time

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

def detect_n_frames(n=5):
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

    if not all_detections:
        return 4  # kein Objekt erkannt

    # Extrahiere meist vorkommendes Ergebnis
    result = max(set(all_detections), key=all_detections.count)

    if result == "steckdose":
        return 1
    elif result == "unterputzdose":
        return 2
    elif result == "schraube_fehlt":
        return 3
    else:
        return 4  # unbekanntes Objekt
