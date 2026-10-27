#!/usr/bin/env python3
"""
Kleinanzeigen-Tracker v3: durchsucht kleinanzeigen.de in einem festen Intervall
und meldet neue Anzeigen. Optional mit Preisfilter, Prüfung der Beschreibung,
Alarmton, optischem Alarm (blinkendes Fenster im Vordergrund) und ntfy-Push.

Installation:
    pip install requests beautifulsoup4

Beispiele:
    python kleinanzeigen_tracker_v3.py -k "aktenvernichter" --max-preis 20 --muss-enthalten p7 --muss-enthalten p-7 --alarm-ton --alarm-optisch
    python kleinanzeigen_tracker_v3.py -k fahrrad --nur-gratis --alarm-optisch
    python kleinanzeigen_tracker_v3.py --alarm-test --alarm-ton --alarm-optisch
"""
import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.kleinanzeigen.de"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9",
}
SEEN_FILE = Path("gesehen.json")
POPUP_DAUER_SEKUNDEN = 60


# ---------- Suche ----------

def suche_url(keyword: str) -> str:
    slug = re.sub(r"\s+", "-", keyword.strip().lower())
    return f"{BASE}/s-{slug}/k0"


def parse_preis(text: str):
    """Gibt (preis_in_euro, ist_gratis) zurück. Preis ist None, wenn nicht lesbar (z. B. nur 'VB')."""
    t = text.strip().lower()
    if "verschenken" in t:
        return 0.0, True
    m = re.search(r"(\d[\d.]*)(?:,(\d+))?", t)
    if not m:
        return None, False
    zahl = float(m.group(1).replace(".", "") + "." + (m.group(2) or "0"))
    return zahl, zahl == 0


def lade_anzeigen(keyword: str):
    r = requests.get(suche_url(keyword), headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    for art in soup.select("article[data-adid], article.aditem"):
        ad_id = art.get("data-adid")
        if not ad_id:
            continue

        # Relative/Absolute URL der Anzeige ermitteln
        rel_url = art.get("data-href")
        if not rel_url:
            link_el = art.select_one('a[href*="/s-anzeige/"]') or art.select_one("span[data-url]") or art.select_one("a.ellipsis")
            if link_el:
                rel_url = link_el.get("href") or link_el.get("data-url")

        if not rel_url:
            continue

        if not rel_url.startswith("http"):
            if not rel_url.startswith("/"):
                rel_url = "/" + rel_url
            full_url = BASE + rel_url
        else:
            full_url = rel_url

        # Titel ermitteln
        h3 = art.select_one("h3")
        titel = h3.get_text(strip=True) if h3 else ""
        if not titel:
            link_el = art.select_one("a.ellipsis") or art.select_one('a[href*="/s-anzeige/"]')
            if link_el:
                titel = link_el.get_text(strip=True)

        if not titel:
            titel = "Ohne Titel"

        # Preis ermitteln
        preis_el = (
            art.select_one(".aditem-main--middle--price-shipping--price") or
            art.select_one("p.text-title3") or
            art.select_one('[class*="price"]')
        )
        preis_txt = preis_el.get_text(strip=True) if preis_el else ""
        if not preis_txt:
            for p in art.find_all(["p", "div", "span"]):
                txt = p.get_text(strip=True)
                if "€" in txt or "verschenken" in txt.lower() or "vb" in txt.lower():
                    if len(txt) < 30:
                        preis_txt = txt
                        break

        yield {
            "id": ad_id,
            "titel": titel,
            "preis_txt": preis_txt,
            "url": full_url,
        }


def lade_beschreibung(url: str):
    """Lädt die Detailseite und gibt den Beschreibungstext zurück (oder None)."""
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    el = (
        soup.select_one("#viewad-description-text") or
        soup.select_one(".aditem-main--middle--description") or
        soup.select_one('[id*="description"]') or
        soup.select_one('[class*="description"]')
    )
    return el.get_text(" ", strip=True) if el else None


def passt_preis(ad: dict, args) -> bool:
    preis, gratis = parse_preis(ad["preis_txt"])
    if args.nur_gratis:
        return gratis
    if args.max_preis is not None:
        return gratis or (preis is not None and preis <= args.max_preis)
    return True


def normalisiere(text: str) -> str:
    """Kleinschreibung, alles außer Buchstaben/Zahlen entfernt: 'P-7', 'p 7', 'P7' -> 'p7'."""
    return re.sub(r"[^a-z0-9äöüß]", "", text.lower())


def passt_text(ad: dict, args) -> bool:
    if not args.muss_enthalten:
        return True
    text = normalisiere(ad["titel"] + " " + (ad.get("beschreibung") or ""))
    return any(normalisiere(begriff) in text for begriff in args.muss_enthalten)


# ---------- Alarme ----------

def spiele_ton():
    """Spielt 3 Signaltöne in einem Hintergrund-Thread ab (blockiert nicht)."""
    def run():
        try:
            if sys.platform == "win32":
                import winsound
                for _ in range(3):
                    winsound.Beep(1200, 300)
                    time.sleep(0.1)
            elif sys.platform == "darwin":
                for _ in range(3):
                    subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
            else:
                sound = "/usr/share/sounds/freedesktop/stereo/complete.oga"
                for _ in range(3):
                    if shutil.which("paplay") and os.path.exists(sound):
                        subprocess.run(["paplay", sound], check=False)
                    else:
                        print("\a", end="", flush=True)
                    time.sleep(0.2)
        except Exception:
            print("\a", end="", flush=True)

    threading.Thread(target=run, daemon=True).start()


def starte_popup(text: str):
    """Startet das blinkende Fenster als eigenen Prozess, damit der Tracker weiterläuft."""
    try:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--_popup", text])
    except Exception as e:
        print(f"Optischer Alarm fehlgeschlagen: {e}", flush=True)


def zeige_popup(text: str):
    """Läuft im eigenen Prozess: rotes/weißes Blinken, immer oben, Klick schließt."""
    import tkinter as tk

    root = tk.Tk()
    root.title("Kleinanzeigen-Treffer!")
    root.attributes("-topmost", True)
    root.geometry("560x220+200+200")

    label = tk.Label(root, text=text, wraplength=520,
                     font=("Segoe UI", 13, "bold"), bg="#ff3b30", fg="white")
    label.pack(expand=True, fill="both", padx=12, pady=12)

    hinweis = tk.Label(root, text="(Klick zum Schließen)", font=("Segoe UI", 9),
                       bg="#ff3b30", fg="white")
    hinweis.pack(pady=(0, 8))

    for widget in (root, label, hinweis):
        widget.bind("<Button-1>", lambda e: root.destroy())

    root.after(POPUP_DAUER_SEKUNDEN * 1000, root.destroy)

    def blink(i=0):
        bg, fg = ("#ff3b30", "white") if i % 2 == 0 else ("white", "#111111")
        for w in (root, label, hinweis):
            w.configure(bg=bg)
        label.configure(fg=fg)
        hinweis.configure(fg=fg)
        root.after(400, blink, i + 1)

    blink()
    root.lift()
    root.focus_force()
    root.mainloop()


def alarm(text: str, args):
    if args.alarm_ton:
        spiele_ton()
    if args.alarm_optisch:
        starte_popup(text)


# ---------- Ausgabe ----------

def melde(keyword: str, ad: dict, args):
    zeile = f"[{datetime.now():%d.%m. %H:%M}] '{keyword}': {ad['titel']} | {ad['preis_txt']} | {ad['url']}"
    print(zeile, flush=True)

    if args.alarm_ton or args.alarm_optisch:
        alarm(f"{keyword}: {ad['titel']}\n{ad['preis_txt']}", args)

    if args.ntfy:
        try:
            requests.post(
                f"https://ntfy.sh/{args.ntfy}",
                data=zeile.encode("utf-8"),
                headers={"Title": "Kleinanzeige gefunden", "Click": ad["url"]},
                timeout=10,
            )
        except requests.RequestException as e:
            print(f"ntfy-Fehler: {e}", flush=True)


# ---------- Hauptprogramm ----------

def main():
    # Interner Aufruf für das Popup-Fenster (eigener Prozess)
    if len(sys.argv) == 3 and sys.argv[1] == "--_popup":
        zeige_popup(sys.argv[2])
        return

    p = argparse.ArgumentParser(description="Kleinanzeigen-Tracker v3")
    p.add_argument("-k", "--keyword", action="append",
                   help="Suchbegriff (mehrfach angeben möglich)")
    preis = p.add_mutually_exclusive_group()
    preis.add_argument("--max-preis", type=float, default=None,
                       help="Maximalpreis in Euro (Gratisangebote sind immer dabei)")
    preis.add_argument("--nur-gratis", action="store_true",
                       help="Nur 'Zu verschenken'-Angebote")
    p.add_argument("--muss-enthalten", action="append", metavar="BEGRIFF",
                   help="Titel ODER Beschreibung muss diesen Begriff enthalten "
                        "(mehrfach = ODER-Verknüpfung; 'P-7' und 'p7' gelten als gleich)")
    p.add_argument("--intervall", type=int, default=900,
                   help="Sekunden zwischen den Suchläufen (Standard: 900, nicht unter 300 empfohlen)")
    p.add_argument("--ntfy", metavar="TOPIC",
                   help="Optional: Push-Benachrichtigung über ntfy.sh an dieses Topic")
    p.add_argument("--alarm-ton", action="store_true", help="Alarmton bei Treffern")
    p.add_argument("--alarm-optisch", action="store_true",
                   help="Blinkendes Fenster im Vordergrund bei Treffern")
    p.add_argument("--alarm-test", action="store_true",
                   help="Nur die aktivierten Alarme einmal testen und beenden")
    args = p.parse_args()

    if args.alarm_test:
        print("Alarm-Test ...", flush=True)
        alarm("Testalarm: Kleinanzeigen-Tracker funktioniert!", args)
        time.sleep(3)
        return

    if not args.keyword:
        p.error("mindestens ein Suchbegriff mit -k angeben (oder --alarm-test verwenden)")

    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    print(f"Tracker gestartet für: {', '.join(args.keyword)}", flush=True)
    if args.muss_enthalten:
        print(f"Beschreibung wird geprüft auf: {', '.join(args.muss_enthalten)}", flush=True)

    while True:
        for kw in args.keyword:
            try:
                for ad in lade_anzeigen(kw):
                    if ad["id"] in seen:
                        continue

                    # Günstige Prüfung zuerst: Preis
                    if not passt_preis(ad, args):
                        seen.add(ad["id"])
                        continue

                    # Teure Prüfung nur für Anzeigen, die den Preisfilter bestanden haben
                    if args.muss_enthalten:
                        ad["beschreibung"] = lade_beschreibung(ad["url"])
                        time.sleep(random.uniform(2, 4))
                        if ad["beschreibung"] is None:
                            print(f"Hinweis: Beschreibung nicht gefunden bei {ad['url']} (nur Titel geprüft)", flush=True)

                    seen.add(ad["id"])
                    if passt_text(ad, args):
                        melde(kw, ad, args)
            except Exception as e:
                # Nicht als gesehen markieren -> wird beim nächsten Lauf erneut geprüft
                print(f"[{datetime.now():%H:%M}] Fehler bei '{kw}': {e}", flush=True)
            time.sleep(random.uniform(3, 8))

        SEEN_FILE.write_text(json.dumps(sorted(seen)))
        time.sleep(args.intervall + random.uniform(0, args.intervall * 0.2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTracker beendet.")
