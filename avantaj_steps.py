"""
/avantaj akışında botun sırayla sorduğu adımlar ve girdi doğrulamaları.
Önce görseller (1. girdi), sonra metin (2. girdi) istenir.
Metin adımlarında parse(text, entities) ya ("value", değer) ya ("error", mesaj) döner.
"""
import os
import re

COLORS = [
    ("Turuncu (varsayılan)", "#DE6D21"),
    ("Kırmızı", "#D32F2F"),
    ("Mavi", "#005FD7"),
    ("Yeşil", "#2E7D32"),
    ("Lacivert", "#1A237E"),
    ("Siyah", "#222222"),
]

FILE_TIP = '\n\n💡 Kalite (ve logolarda şeffaf arka plan) için resmi "Dosya" olarak göndermeniz önerilir.'


# ---- Açıklama metni: *yıldız* ya da Telegram kalın biçimlendirmesi → [{"text", "bold"}] ----

def parse_stars(text):
    parts = []
    last = 0
    for m in re.finditer(r"\*([^*]+)\*", text):
        if m.start() > last:
            parts.append({"text": text[last:m.start()], "bold": False})
        parts.append({"text": m.group(1), "bold": True})
        last = m.end()
    if last < len(text):
        parts.append({"text": text[last:], "bold": False})
    return _trim_parts(parts)


def _trim_parts(parts):
    """Baştaki/sondaki boşlukları parçalardan temizler, boş kalan parçaları atar."""
    if parts:
        parts[0]["text"] = parts[0]["text"].lstrip()
        parts[-1]["text"] = parts[-1]["text"].rstrip()
    return [p for p in parts if p["text"]]


def from_telegram(text, entities=()):
    # Telegram entity offset/length değerleri UTF-16 birimindedir; emoji gibi karakterler 2 birim sayılır.
    bold_ranges = [(e.offset, e.offset + e.length) for e in entities or () if e.type == "bold"]
    if not bold_ranges:
        return parse_stars(text)

    parts = []
    utf16 = 0
    for ch in text:
        bold = any(a <= utf16 < b for a, b in bold_ranges)
        if not parts or parts[-1]["bold"] != bold:
            parts.append({"text": "", "bold": bold})
        parts[-1]["text"] += ch
        utf16 += 2 if ord(ch) > 0xFFFF else 1
    return _trim_parts(parts)


# ---- Doğrulamalar ----

def _discount(text, _):
    m = re.match(r"^%?\s*(\d{1,3})\s*%?$", text.strip())
    n = int(m.group(1)) if m else 0
    if not 1 <= n <= 100:
        return "error", "Lütfen 1 ile 100 arasında bir sayı yazın (örn: 50)."
    return "value", n


def _description(text, entities):
    if len(text.strip()) < 3:
        return "error", "Açıklama çok kısa."
    if len(text) > 400:
        return "error", f"Açıklama en fazla 400 karakter olabilir (şu an {len(text)})."
    return "value", from_telegram(text, entities)


def _phone(text, _):
    t = text.strip()
    if not re.search(r"\d", t) or len(t) > 40:
        return "error", "Geçerli bir telefon numarası yazın."
    return "value", t


def _business(text, _):
    t = text.strip()
    if not t:
        return "error", "İşletme adı boş olamaz."
    if len(t) > 90:
        return "error", "İşletme adı en fazla 90 karakter olabilir."
    return "value", t


def _ig_username(text, _):
    t = text.strip()
    t = re.sub(r"^@", "", t)
    t = re.sub(r"^https?://(www\.)?instagram\.com/", "", t, flags=re.I)
    t = re.sub(r"/.*$", "", t)
    if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", t):
        return "error", "Geçerli bir Instagram kullanıcı adı yazın (harf, rakam, nokta, alt çizgi; en fazla 30 karakter)."
    return "value", t


def _sendika_url(text, _):
    t = re.sub(r"^https?://", "", text.strip(), flags=re.I).rstrip("/")
    if not re.fullmatch(r"[^\s/]+\.[^\s]{2,}", t) or len(t) > 60:
        return "error", "Geçerli bir site adresi yazın (örn: sendika.org.tr)."
    return "value", t


def _url_color(text, _):
    for label, hex_ in COLORS:
        if text.strip() == label:
            return "value", hex_
    m = re.fullmatch(r"#?([0-9a-f]{6})", text.strip(), re.I)
    if not m:
        return "error", "Renk #RRGGBB biçiminde olmalı (örn: #DE6D21) ya da butonlardan seçin."
    return "value", "#" + m.group(1).upper()


# Tek sendika (Bağımsız Yerel Hak-Sen) için kullanıldığından bu alanlar sorulmaz.
DEFAULTS = {
    "sendika_logo": os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "avantaj", "sendika_logo.png"),
    "sendika_url": "bagimsizyerelhaksen.org.tr",
    "url_color": "#005FD7",
}


class _Entity:
    type = "bold"

    def __init__(self, offset, length):
        self.offset, self.length = offset, length


def _all_texts(text, entities):
    """Tek mesajda: 1. satır indirim, son 3 satır telefon/işletme/Instagram, aradakiler açıklama."""
    stripped = text.strip()
    lines = stripped.split("\n")
    if len(lines) < 5:
        return "error", (
            f"En az 5 satır bekleniyor (şu an {len(lines)}): indirim, açıklama, telefon, işletme, "
            "Instagram kullanıcı adı. Her biri ayrı satırda olmalı."
        )

    # Kalın biçimlendirme offset'leri tüm metne göre olduğundan açıklamaya göre kaydırılır.
    desc_start = len(lines[0]) + 1
    desc_end = len(stripped) - len("\n".join(lines[-3:])) - 1
    desc_text = stripped[desc_start:desc_end]
    shift = len(text) - len(text.lstrip()) + desc_start
    bold = [_Entity(e.offset - shift, e.length) for e in entities or () if e.type == "bold" and e.offset >= shift]

    out = {}
    for key, parse, value, ents in (
        ("discount", _discount, lines[0], ()),
        ("description", _description, desc_text, bold),
        ("phone", _phone, lines[-3], ()),
        ("business", _business, lines[-2], ()),
        ("ig_username", _ig_username, lines[-1], ()),
    ):
        result, parsed = parse(value, ents)
        if result == "error":
            return "error", parsed
        out[key] = parsed
    return "value", out


STEPS = [
    {"key": "ig_avatar", "kind": "image",
     "prompt": "🏷 AVANTAJ GÖRSELİ\n\n"
               "ADIM 1 — Önce 3 görsel göndermeniz gerekiyor, şu SIRAYLA:\n"
               "  1️⃣ Instagram profil fotoğrafı\n"
               "  2️⃣ Instagram gönderi fotoğrafı\n"
               "  3️⃣ İşletme logosu\n\n"
               "Nasıl göndereceksiniz? İki yol var:\n"
               "🅰️ Hepsini tek seferde: 3 görseli birlikte seçip albüm olarak gönderin. "
               "Görseller seçtiğiniz sıraya göre yerleştirilir (1. seçtiğiniz profil, 2. gönderi, 3. logo).\n"
               "🅱️ Tek tek: önce sadece profil fotoğrafını gönderin; sonra bot sırayla gönderi fotoğrafını ve logoyu ister.\n\n"
               "💡 Kaliteyi korumak (ve logoda şeffaf arka plan için) görselleri \"Dosya\" olarak gönderin.\n"
               "Görsellerin hepsi gelince metin bilgilerini isteyeceğim.\n\n"
               "İptal: /cancel   |   Önceki adım: /geri"},
    {"key": "ig_post", "kind": "image",
     "prompt": "✅ Profil fotoğrafı alındı.\n\n"
               "ADIM 1 (2/3) — Şimdi Instagram GÖNDERİ fotoğrafını gönderin." + FILE_TIP},
    {"key": "business_logo", "kind": "image",
     "prompt": "✅ Gönderi fotoğrafı alındı.\n\n"
               "ADIM 1 (3/3) — Son olarak İŞLETME LOGOSUNU gönderin." + FILE_TIP},
    {"key": "discount", "kind": "text", "parse": _all_texts,
     "prompt": "ADIM 2 — Şimdi metni TEK mesajda gönderin. Her bilgi AYRI SATIRDA ve bu sırayla olmalı:\n"
               "  1. satır: İndirim yüzdesi (sadece sayı)\n"
               "  2. satır: Açıklama (en fazla 400 karakter). Kalın olacak kısmı *yıldız* arasına alın\n"
               "  3. satır: Telefon numarası\n"
               "  4. satır: İşletme adı ve konumu (\" -\" işaretinden sonrası alt satıra geçer)\n"
               "  5. satır: Instagram kullanıcı adı\n\n"
               "ÖRNEK:\n"
               "50\n"
               "*Sendikamıza üyemiz olsun olmasın* itfaiye personeline özel indirim.\n"
               "0 312 911 54 51\n"
               "Presa Di Finica Hotel -Antalya/Finike\n"
               "@leylacakirbeauty\n\n"
               "Gönderince görsel birkaç saniyede hazırlanır.\n"
               "İptal: /cancel   |   Önceki adım: /geri"},
]
