# Oracle Cloud (OCI) GPU Instance Setup Guide & AI Production Pipeline

Diese Anleitung führt dich Schritt für Schritt durch die Erstellung einer GPU-Instanz in der Oracle Cloud Infrastructure (OCI), die Installation der reparierten Skripte und die vollautomatische Generierung von Videos mit Alibaba Wan 2.1 / 3.0 und Sprachsynthese (TTS).

---

## 1. Oracle Cloud Instanz erstellen (VM.GPU.A10.1)

1. **Einloggen in die Oracle Cloud Console:**
   - Navigiere zu `https://cloud.oracle.com` und melde dich an.

2. **Instanz-Erstellungsmenü öffnen:**
   - Klicke oben links auf das Hauptmenü `☰` -> **Compute** -> **Instances**.
   - Klicke auf den Button **Create Instance**.

3. **Instanz-Konfiguration wählen:**
   - **Name:** `ai-video-studio`
   - **Image (Betriebssystem):** Klicke auf **Change image** -> Wähle **Canonical Ubuntu 22.04 LTS** oder **24.04 LTS**.
   - **Shape (Hardware):** Klicke auf **Change shape**:
     - Instanz-Typ: **Specialty and Previous Generation** oder **GPU**.
     - Wähle: **VM.GPU.A10.1** (1x NVIDIA A10 GPU, 24 GB VRAM, 15 vCPUs, 240 GB RAM).
     - *Hinweis zum Preis:* Ca. $2.00 / Stunde (On-Demand) oder ca. $1.00 / Stunde (Preemptible/Spot).

4. **Netzwerk & SSH-Schlüssel:**
   - **Networking:** Standard VCN & Subnet auswählen.
   - **Assign a public IPv4 address:** **Ja** (Hook / Checkbox aktivieren).
   - **Add SSH keys:** Wähle **Generate a key pair for me** (Lade den privaten Schlüssel `ssh-key-xxxx.key` auf deinen PC herunter) ODER lade deinen eigenen öffentlichen SSH-Key hoch.

5. **Boot Volume / Speicherplatz:**
   - Aktiviere **Specify a custom boot volume size**.
   - Empfohlen: Mindestens **150 GB bis 250 GB** (da AI-Modelle wie Wan 2.1 / Wan 3.0 einige Gigabyte groß sind).

6. **Instanz starten:**
   - Klicke ganz unten auf **Create**.
   - Warte 2–3 Minuten, bis der Status auf grün **Running** wechselt. Notiere dir die **Public IP Address** der Instanz.

---

## 2. Ingress-Regeln / Security List in Oracle Cloud (Netzwerk-Sicherheit)

Damit du dich per SSH verbinden kannst, muss Port 22 in der OCI Security List offen sein (standardmäßig ist das der Fall):

1. Gehe in OCI auf deiner Instanz-Detailseite auf das verknüpfte **Subnet**.
2. Klicke auf die **Default Security List**.
3. Ingress Rule überprüfen:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** `TCP`
   - **Destination Port Range:** `22`

---

## 3. Erstmaliges Verbinden & Einrichten der Instanz

Öffne dein Terminal (macOS/Linux) oder PowerShell/CMD (Windows) auf deinem lokalen PC und verbinde dich mit deiner Instanz:

```bash
# Rechte des SSH-Keys anpassen (Linux/macOS)
chmod 400 ~/Downloads/ssh-key-xxxx.key

# Verbindung herstellen
ssh -i ~/Downloads/ssh-key-xxxx.key ubuntu@<DEINE_OCI_IP>
```

### Schritt A: Repository / Skripte auf den Server kopieren

Erstelle den Zielordner und kopiere die Reparierten Skripte auf deine OCI-Instanz:

```bash
# Auf dem Server:
mkdir -p ~/oci_ai_pipeline
```

Von deinem **lokalen PC** aus führst du folgenden Befehl aus, um die Ordnerinhalte hochzuladen:

```bash
scp -i ~/Downloads/ssh-key-xxxx.key -r ./oci_ai_pipeline/* ubuntu@<DEINE_OCI_IP>:~/oci_ai_pipeline/
```

### Schritt B: Auto-Installer ausführen

Wechsle auf dem Server in den Ordner und starte die Installation:

```bash
cd ~/oci_ai_pipeline
sudo bash install_oci_ai.sh
```

*(Das Skript installiert NVIDIA-Treiber, Docker, PyTorch, ComfyUI, F5-TTS und richtet `/opt/ai-studio` ein.)*

**WICHTIGER HINWEIS:** Falls Treiber neu installiert wurden, starte den Server kurz neu:
```bash
sudo reboot
```
Warte 1 Minute und verbinde dich wieder per SSH.

### Schritt C: Sicherheit & Hintergrund-Daemon einrichten

Führe das Sicherheits- und Service-Skript aus:

```bash
cd ~/oci_ai_pipeline
sudo bash setup_secure_pipeline.sh
```

Kopiere das Python-Daemon-Skript in den System-Ordner:

```bash
cp worker.py /opt/ai-studio/scripts/worker.py
chmod +x /opt/ai-studio/scripts/worker.py
```

Starte den Hintergrund-Dienst:

```bash
sudo systemctl start ai-worker
sudo systemctl enable ai-worker

# Status überprüfen:
sudo systemctl status ai-worker
```

---

## 4. Nutzung: Drehbücher füttern & Videos generieren

Das System arbeitet vollautomatisch im Hintergrund.

### 1. Drehbuch hochladen (Vom lokalen PC aus):

Erstelle oder passe deine `drehbuch.json` an und sende sie an die Cloud:

```bash
scp -i ~/Downloads/ssh-key-xxxx.key ./example_drehbuch.json ubuntu@<DEINE_OCI_IP>:/opt/ai-studio/inputs/
```

Sobald die Datei im Ordner `/opt/ai-studio/inputs/` landet, erkennt der Worker sie automatisch, verarbeitet Szene für Szene (30-Sekunden-Clips), fügt Ton und Video zusammen, fügt am Ende alle Szenen zu einem **Master-Video** zusammen und löscht die JSON-Datei.

### 2. Fertige Videos herunterladen (Auf deinen lokalen PC):

Hole dir alle fertig gerenderten MP4-Videos ab:

```bash
rsync -avz -e "ssh -i ~/Downloads/ssh-key-xxxx.key" ubuntu@<DEINE_OCI_IP>:/opt/ai-studio/outputs/ ./lokale_ergebnisse/
```

Du findest dort Dateien wie:
- `cyberpunk_commercial_01_scene_1_final.mp4`
- `cyberpunk_commercial_01_scene_2_final.mp4`
- **`cyberpunk_commercial_01_MASTER_FINAL.mp4`** (Das komplett zusammengefügte Gesamtvideo!)

---

## 5. SSH Tunneling für ComfyUI Web-Interface (Optional)

Solltest du das grafische ComfyUI Web-UI in deinem Browser öffnen wollen, musst du dank der Firewalleinstellungen keinen öffentlichen Port freigeben, sondern nutzt einen verschlüsselten SSH-Tunnel:

Führe auf deinem **lokalen PC** aus:

```bash
ssh -i ~/Downloads/ssh-key-xxxx.key -L 8188:127.0.0.1:8188 ubuntu@<DEINE_OCI_IP>
```

Öffne jetzt einfach deinen Browser auf deinem Rechner:
👉 **`http://localhost:8188`**

---

## 6. Notfall & Troubleshooting (Innerhalb von Minuten behebbar via SSH)

- **Worker Logs prüfen:**
  ```bash
  tail -f ~/ai_pipeline_worker.log
  # Oder via systemctl:
  sudo journalctl -u ai-worker -f
  ```

- **GPU Status prüfen:**
  ```bash
  nvidia-smi
  ```

- **Worker manuell im Vordergrund testen:**
  ```bash
  sudo systemctl stop ai-worker
  /opt/ai-studio/venv/bin/python3 /opt/ai-studio/scripts/worker.py
  ```

- **Server nach Renderjob automatisch herunterfahren zur Kostenersparnis:**
  Setze in deiner `drehbuch.json` das Feld `"auto_shutdown": true`.
  Sobald alle Clips gerendert und zusammengefügt sind, fährt sich die OCI-Instanz automatisch herunter!
