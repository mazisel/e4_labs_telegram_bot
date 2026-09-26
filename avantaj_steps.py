"""
/avantaj akışında botun sırayla sorduğu adımlar ve girdi doğrulamaları.
Metin adımlarında parse(text, entities) ya ("value", değer) ya ("error", mesaj) döner.
"""
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


STEPS = [
    {"key": "discount", "kind": "text", "parse": _discount,
     "prompt": "1/11 — İndirim yüzdesi kaç? (örn: 50)"},
    {"key": "description", "kind": "text", "parse": _description,
     "prompt": "2/11 — Açıklama metnini yazın.\n\n"
               "Kalın olmasını istediğiniz kısımları *yıldız* arasına alın (veya Telegram'ın kalın biçimlendirmesini kullanın).\n"
               "Örn: *Sendikamıza üyemiz olsun olmasın* itfaiye personeline özel indirim."},
    {"key": "phone", "kind": "text", "parse": _phone,
     "prompt": "3/11 — Telefon numarası? (örn: 0 312 911 54 51)"},
    {"key": "business", "kind": "text", "parse": _business,
     "prompt": "4/11 — İşletme adı ve konumu? (örn: Presa Di Finica Hotel -Antalya/Finike)\n\n"
               '" -" işaretinden itibaren ikinci satıra geçer; isterseniz satırı kendiniz de bölebilirsiniz.'},
    {"key": "ig_avatar", "kind": "image",
     "prompt": "5/11 — Instagram profil fotoğrafını gönderin."},
    {"key": "ig_username", "kind": "text", "parse": _ig_username,
     "prompt": "6/11 — Instagram kullanıcı adı? (örn: leylacakirbeauty)"},
    {"key": "ig_post", "kind": "image",
     "prompt": "7/11 — Instagram gönderi fotoğrafını gönderin." + FILE_TIP},
    {"key": "business_logo", "kind": "image",
     "prompt": "8/11 — İşletme logosunu gönderin." + FILE_TIP},
    {"key": "sendika_logo", "kind": "image",
     "prompt": "9/11 — Sendika logosunu gönderin." + FILE_TIP},
    {"key": "sendika_url", "kind": "text", "parse": _sendika_url,
     "prompt": "10/11 — Sendikanın site adresi? (örn: bagimsizyerelhaksen.org.tr)"},
    {"key": "url_color", "kind": "color", "parse": _url_color,
     "prompt": "11/11 — Site adresi hangi renkte olsun? Aşağıdan seçin veya #RRGGBB biçiminde yazın."},
]
