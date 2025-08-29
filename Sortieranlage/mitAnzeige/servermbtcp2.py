# StatusQuo 19.05.2025 korrigierte Version mit einfacherem Handshake
import logging
from pyModbusTCP.server import ModbusServer, DataBank
from time import sleep

# === Logging-Konfiguration ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler("modbus_server.log"),
        logging.StreamHandler()
    ]
)

# === Konfigurierbare Parameter ===
TIMEOUT_SECONDS = 30  # später ggf. anpassen
SLEEP_CYCLE = 0.05    # Abtastrate für Triggerprüfung

# === Register-Adressen ===
HR_CMD            = 0
HR_SEQ_NR_SPS     = 1
HR_STATE_SERVER   = 2
HR_SEQ_NR_SERVER  = 3
HR_RESULT         = 4

# === Status-Codes für state_server ===
STATUS_NOT_READY  = 0
STATUS_READY      = 1
STATUS_BUSY       = 2
STATUS_DONE       = 3
STATUS_ERROR      = 4


def wait_for_trigger(db: DataBank) -> bool:
    """Warte auf neuen Auftrag: cmd=1 und seq_nr_sps != seq_nr_server"""
    while True:
        cmd = db.get_holding_registers(HR_CMD, 1)
        seq_sps = db.get_holding_registers(HR_SEQ_NR_SPS, 1)
        seq_server = db.get_holding_registers(HR_SEQ_NR_SERVER, 1)

        # Sicherheit: alle Register müssen gültig sein
        if None in (cmd, seq_sps, seq_server):
            logging.warning("Fehler beim Lesen der Register. Wiederhole Leseversuch.")
            sleep(SLEEP_CYCLE)
            continue

        # Entpacke Werte
        cmd_val = cmd[0]
        seq_sps_val = seq_sps[0]
        seq_server_val = seq_server[0]

        # Bedingung für neuen Auftrag
        if cmd_val == 1 and seq_sps_val != seq_server_val:
            logging.info(f"Neuer Auftrag erkannt (seq_nr_sps = {seq_sps_val}).")
            #setze Ergebnis zurück
            db.set_holding_registers(HR_RESULT, [0])
            return True

        sleep(SLEEP_CYCLE)


def handle_classification(db: DataBank, classify_callback):
    """Verarbeite Klassifikation nach erkanntem Trigger"""
    db.set_holding_registers(HR_STATE_SERVER, [STATUS_BUSY])
    logging.info("Jetson: STATUS_BUSY. starte Klassifikation...")


    # Objektdetection anstossen
    try:
        result = classify_callback()
    except Exception as e:
        logging.exception("Fehler beim Klassifizieren:")
        result = -1

    # Fehlerbehandlung für None oder -1
    if result is None or result == -1:
        logging.error("Fehlerhafte Klassifikation: setze Ergebnis auf -1 und STATUS_ERROR.")
        db.set_holding_registers(HR_RESULT, [-1])
        db.set_holding_registers(HR_STATE_SERVER, [STATUS_ERROR])
        return

    # Ergebnis schreiben
    db.set_holding_registers(HR_RESULT, [result])
    logging.info(f"Ergebnis geschrieben: {result}")

    # Sequenznummer bestätigen
    seq_nr = db.get_holding_registers(HR_SEQ_NR_SPS, 1)
    if seq_nr:
        db.set_holding_registers(HR_SEQ_NR_SERVER, [seq_nr[0]])

    # STATUS_DONE setzen 
    db.set_holding_registers(HR_STATE_SERVER, [STATUS_DONE])
    logging.info("Jetson: STATUS_DONE: warte kurz, bevor auf READY zurückgesetzt wird.")

    # Kleine Pause, damit SPS Zeit hat, STATUS_DONE zu erkennen
    sleep(0.5)

    # Zurück auf READY
    db.set_holding_registers(HR_STATE_SERVER, [STATUS_READY])
    logging.info("Jetson: STATUS_READY: bereit für nächsten Auftrag.")


def start_modbus_server(classify_callback):
    # Initialisiere Datenbank & Server
    db = DataBank(coils_size=10, coils_default_value=False, h_regs_size=10, h_regs_default_value=0)
    server = ModbusServer(host="0.0.0.0", port=502, no_block=True, data_bank=db)

    try:
        logging.info("Starte Modbus TCP Server auf Port 502...")
        server.start()
        sleep(0.5)

        # Server ist bereit
        db.set_holding_registers(HR_STATE_SERVER, [STATUS_READY])
        logging.info("Server läuft:  STATUS_READY gesetzt.")

        # Hauptschleife: Aufträge abarbeiten
        while True:
            if wait_for_trigger(db):
                handle_classification(db, classify_callback)

    except KeyboardInterrupt:
        logging.info("Server wird beendet (KeyboardInterrupt)...")
        server.stop()
        logging.info("Server gestoppt.")
