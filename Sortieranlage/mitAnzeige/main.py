from detectorWithDisplay import detect_n_frames
from servermbtcp2 import start_modbus_server

def classify_callback():
    print("Trigger erhalten. Starte Detection ...")
    detection = detect_n_frames(n=5)
    print("Erkanntes Objekt:", detection)
    return detection

if __name__ == "__main__":
    print("Starte Modbus-Server mit Klassifikation bei Trigger ...")
    start_modbus_server(classify_callback)
