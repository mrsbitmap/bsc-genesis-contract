import os
import re
import urllib.parse
import urllib.request
import time

CHARACTERS = [
    (1, "Tralalero Tralala", "Drei-beiniger Hai mit Nike-Sneakers"),
    (2, "Cappuccino Assassino", "Kaffeebecher als Ninja mit Schwertern"),
    (3, "Chimpanzini Bananini", "Schimpanse mit Bananen-Körper"),
    (4, "Brr Brr Patapim", "Affen-/Waldwesen mit Blättern und großen Füßen"),
    (5, "Lirilì Larilà", "Elefant-Kaktus-Hybrid mit Sandalen"),
    (6, "Trippi Troppi", "Katze + Garnele"),
    (7, "Boneca Ambalabu", "Frosch auf einem Reifen"),
    (8, "Bombombini Gusini", "Gans + Kampfjet"),
    (9, "La Vaca Saturno Saturnita", "Kuh im Orbit von Saturn"),
    (10, "Frigo Camello", "Kamel + Kühlschrank"),
    (11, "Burbaloni Luliloli", "Capybara in einer Kokosnuss"),
    (12, "Glorbo Fruttodrillo", "Frucht-Krokodil-Hybrid"),
    (13, "Bananita Dolphinita", "Delfin + Banane"),
    (14, "Cocofanto Elefanto", "Elefant + Kokosnuss"),
    (15, "Bobrito Bandito", "Biber als Gangster"),
    (16, "Frulli Frulla", "Pinguin mit Mixer-Elementen"),
    (17, "Giraffa Celeste", "Himmlische Giraffe"),
    (18, "Orcalero Orcala", "Orca-Variante im Brainrot-Stil"),
    (19, "Trulimero Trulicina", "Fisch-Katzen-Hybrid"),
    (20, "Noobini Pizzanini", "Klassischer Noob + Pizza"),
    (21, "Tim Cheese", "Käse-Figur"),
    (22, "Gangster Footera", "Fuß/Gangster-Hybrid"),
    (23, "Chef Crabracadabra", "Zauberer-Krabbe"),
    (24, "Lionel Cactuseli", "Kaktus + Fußballer-Anspielung"),
    (25, "Blueberrini Octopusini", "Blaubeere + Oktopus"),
    (26, "Strawberelli Flamingelli", "Erdbeere + Flamingo"),
    (27, "Pandaccini Bananini", "Panda + Banane"),
    (28, "Pot Hotspot", "Topf / Hotspot-Meme-Figur"),
    (29, "Chicleteira Bicicleteira", "Kaugummi + Fahrrad"),
    (30, "Job Job Job Sahur", "Variante der Sahur-Reihe"),
    (31, "Ta Ta Ta Ta Sahur", "Weitere Sahur-Variation"),
    (32, "Nuclearo Dinossauro", "Nuklearer Dinosaurier"),
    (33, "Los Tralaleritos", "Die Kinder von Tralalero Tralala"),
    (34, "Espressona Signora", "Dunkle Kaffee-Dame"),
    (35, "Burbaloni Loliloli", "Capybara-Variante"),
    (36, "Glorbo Fruttodrillo", "Frucht-Drache/Krokodil"),
    (37, "Avocadini Guffo", "Avocado + Eule"),
    (38, "Salamino Penguino", "Salami + Pinguin"),
    (39, "Bambini Crostini", "Kind + Crostini"),
    (40, "Perochello Lemonchello", "Zitrone / Limoncello-Figur"),
    (41, "Brri Brri Bicus Dicus Bombicus", "Absurde Bombicus-Variante"),
    (42, "Pipi Avocado", "Avocado-Figur"),
    (43, "Talpa di Ferro", "Maulwurf in Eisenrüstung"),
    (44, "Jimothy the Raccoon", "Realer Waschbär aus Seattle mit kurzem Körper"),
    (45, "Rumpelstiltskin (Tip Toein' In My Jordans)", "AI-generierter kleiner Imp, der zu Riff Raff tanzt"),
    (46, "Biddy Blas / Scrib Doon", "Alien-Rennfahrer aus dem Spiel Star Wars: Galactic Racer"),
    (47, "Remember November 2026 Polar Bear", "Singender AI-Eisbär, der vor dem November 2026 warnt"),
    (48, "Black Cat Clapping", "AI-Katze mit Menschenhänden, die langsam klatscht"),
    (49, "Flobby Samuel Insect", "Absurdes Insekten-Meme"),
    (50, "Boneca Ambalabu", "Indonesischer Einfluss"),
    (51, "Tralalero Tralala", "Der originale Hai mit Sneakers"),
    (52, "Trippi Troppi", "Katze + Garnele"),
    (53, "Brr Brr Patapim", "Wald-/Affenwesen"),
    (54, "La Vaca Saturno Saturnita", "Kuh im Orbit"),
    (55, "Cappuccino Assassino", "Kaffeebecher als Ninja"),
    (56, "Chimpanzini Bananini", "Schimpanse mit Bananen-Körper"),
]

OUT_DIR = "meme_characters"
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def clean_filename(name):
    clean = re.sub(r'[^\w\-_.]', '_', name)
    return clean

def fetch_image_urls(query):
    # Search Bing Images
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        content = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+)&quot;', content)
        return murls
    except Exception as e:
        print(f"Error querying {query}: {e}")
        return []

def download_image(num, name, desc):
    safe_name = clean_filename(f"{num:02d}_{name}")
    # Check if already downloaded
    for ext in [".jpg", ".png", ".webp", ".jpeg"]:
        target_path = os.path.join(OUT_DIR, safe_name + ext)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
            print(f"[{num}/56] Already downloaded: {target_path}")
            return True

    queries = [
        f'"{name}" meme',
        f'{name} meme',
        f'"{name}" Italian brainrot',
        f'{name} {desc}',
        name
    ]

    for q in queries:
        image_urls = fetch_image_urls(q)
        for img_url in image_urls[:5]:
            try:
                # determine ext
                ext = ".jpg"
                lower_url = img_url.lower()
                if ".png" in lower_url:
                    ext = ".png"
                elif ".webp" in lower_url:
                    ext = ".webp"
                elif ".jpeg" in lower_url:
                    ext = ".jpeg"

                target_path = os.path.join(OUT_DIR, safe_name + ext)
                req = urllib.request.Request(img_url, headers=HEADERS)
                data = urllib.request.urlopen(req, timeout=10).read()
                if len(data) > 1000:
                    with open(target_path, "wb") as f:
                        f.write(data)
                    print(f"[{num}/56] Saved: {target_path} ({len(data)} bytes) from {img_url[:60]}...")
                    return True
            except Exception as e:
                continue
        time.sleep(0.5)

    print(f"[{num}/56] Failed to download image for: {name}")
    return False

if __name__ == "__main__":
    success = 0
    for num, name, desc in CHARACTERS:
        if download_image(num, name, desc):
            success += 1
    print(f"\nDone: {success}/{len(CHARACTERS)} downloaded.")
