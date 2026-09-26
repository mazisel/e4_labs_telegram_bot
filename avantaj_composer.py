"""
Avantaj kampanyası şablonu (1080x1350 PNG).

Koordinatlar "Klasik İndirim.psd" dosyasından alınmıştır. Instagram kartının sabit kısımları
(gölge, çerçeve, ikonlar) assets/avantaj/sablon.png içine önceden işlenmiştir; burada sadece
metinler ve kullanıcının gönderdiği resimler yerleştirilir.

Test için:  python avantaj_composer.py   →  temp/avantaj_ornek.png ve temp/avantaj_ornek_uzun.png
"""
import io
import os
import re
from functools import lru_cache

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageOps

ASSETS = "assets"
TEMPLATE_PATH = os.path.join(ASSETS, "avantaj", "sablon.png")
GLOBE_MASK_PATH = os.path.join(ASSETS, "avantaj", "globe_mask.png")

FONT_PATHS = {
    "light": os.path.join(ASSETS, "Poppins-Light.ttf"),
    "medium": os.path.join(ASSETS, "Poppins-Medium.ttf"),
    "bold": os.path.join(ASSETS, "Poppins-Bold.ttf"),
    # Instagram arayüzü için Arial ile aynı ölçülere sahip Arimo
    "ui_regular": os.path.join(ASSETS, "Arimo-Regular.ttf"),
    "ui_bold": os.path.join(ASSETS, "Arimo-Bold.ttf"),
}

BLUE = (0, 95, 215)
DEFAULT_URL_COLOR = "#DE6D21"

# Poppins: ascender 1050, descender 350 (em=1000)
POPPINS_ASC = 1.05
POPPINS_LINE = 1.4

CARD = {"x": 47, "y": 360, "w": 806, "h": 774}


# ---- Font yardımcıları -------------------------------------------------------

@lru_cache(maxsize=None)
def _charset(key):
    return set(TTFont(FONT_PATHS[key]).getBestCmap())


@lru_cache(maxsize=512)
def _font(key, size):
    return ImageFont.truetype(FONT_PATHS[key], size)


def sanitize(key, text):
    """Fontta karşılığı olmayan karakterleri (emoji vb.) atar; aksi halde boş kutu çizilir."""
    chars = _charset(key)
    return "".join(ch for ch in str(text or "") if ch == " " or ord(ch) in chars)


def measure(key, text, size, letter_spacing=0):
    clean = sanitize(key, text)
    return _font(key, size).getlength(clean) + letter_spacing * len(clean)


def draw_text(draw, key, text, x, y, size, fill, letter_spacing=0):
    """(x, y) sol-taban çizgisi noktasıdır."""
    clean = sanitize(key, text)
    font = _font(key, size)
    if not letter_spacing:
        draw.text((x, y), clean, font=font, fill=fill, anchor="ls")
        return
    for ch in clean:
        draw.text((x, y), ch, font=font, fill=fill, anchor="ls")
        x += font.getlength(ch) + letter_spacing


def layout_rich(parts, max_width, size, normal="light", bold="bold"):
    """
    Kalın/ince parçalardan oluşan metni verilen genişliğe göre satırlara böler.
    parts: [{"text": str, "bold": bool}]
    Döner: (lines, width) — lines: [[{"text", "bold", "x"}]], x satır başına göredir.
    """
    font_of = lambda b: bold if b else normal

    # Kelimelere ayır: her kelime bir veya daha fazla (kalın/ince) parçadan oluşabilir.
    words = []
    current = None
    pending_break = None  # None | "space" | "newline"
    space_bold = False
    for part in parts:
        for token in re.split(r"(\s+)", part["text"]):
            if not token:
                continue
            if token.isspace():
                current = None
                if "\n" in token:
                    pending_break = "newline"
                elif pending_break != "newline":
                    pending_break = "space"
                space_bold = part["bold"]
                continue
            if current is None:
                current = {"segs": [], "break": pending_break if words else None, "space_bold": space_bold}
                words.append(current)
                pending_break = None
            current["segs"].append({"text": token, "bold": part["bold"]})

    lines = [[]]
    cursor = 0
    widest = 0
    for word in words:
        word_width = sum(measure(font_of(s["bold"]), s["text"], size) for s in word["segs"])
        line = lines[-1]
        space_width = measure(font_of(word["space_bold"]), " ", size) if line else 0

        if word["break"] == "newline" or (line and cursor + space_width + word_width > max_width):
            lines.append([])
            cursor = 0
        else:
            cursor += space_width

        for seg in word["segs"]:
            lines[-1].append({"text": seg["text"], "bold": seg["bold"], "x": cursor})
            cursor += measure(font_of(seg["bold"]), seg["text"], size)
        widest = max(widest, cursor)

    return [l for l in lines if l], widest


def fit_size(start, minimum, fits):
    """Büyük boyuttan başlayıp fits(size) doğru olana kadar 0.5px adımlarla küçültür."""
    size = start
    while size > minimum and not fits(size):
        size -= 0.5
    return size, not fits(size)


def normalize_color(value):
    m = re.match(r"^#?([0-9a-f]{6})$", str(value or "").strip(), re.I)
    return f"#{m.group(1).upper()}" if m else DEFAULT_URL_COLOR


def split_business(name):
    """"Presa Di Finica Hotel -Antalya/Finike" → PSD'deki gibi " -" öncesinden iki satıra böl."""
    text = str(name).strip()
    if "\n" in text:
        return [l.strip() for l in text.split("\n") if l.strip()][:2]
    m = re.match(r"^(.*\S)\s+(-\s*\S.*)$", text)
    return [m.group(1), m.group(2)] if m else None


# ---- Metin blokları (her biri taşma bilgisini döner) --------------------------

def _discount(draw, discount):
    text = f"EK %{discount}"
    size, overflow = fit_size(107.3, 50, lambda s: measure("bold", text, s) <= 380)
    draw_text(draw, "bold", text, 66, 226, size, BLUE)
    return overflow


def _description(draw, parts):
    baseline, max_width, max_bottom, line_height = 135, 462, 292, 1.228
    first_line_top = lambda s: baseline - ((line_height - POPPINS_LINE) / 2 + POPPINS_ASC) * s

    def fits(s):
        lines, width = layout_rich(parts, max_width, s)
        return width <= max_width and first_line_top(s) + len(lines) * line_height * s <= max_bottom

    size, overflow = fit_size(25.3, 14, fits)
    lines, _ = layout_rich(parts, max_width, size)
    for i, line in enumerate(lines):
        for seg in line:
            key = "bold" if seg["bold"] else "light"
            draw_text(draw, key, seg["text"], 470 + seg["x"], baseline + i * line_height * size, size, BLUE)
    return overflow


def _phone(draw, phone):
    start = 33.33
    size, overflow = fit_size(start, 18, lambda s: measure("bold", phone, s) <= 345)
    # küçülen numarayı soldaki telefon ikonuyla dikeyde ortalı tut (büyük harf yüksekliği ~0.7em)
    y = 341 - (start - size) * 0.35
    draw_text(draw, "bold", phone, 629, y, size, BLUE)
    return overflow


def _business(draw, name):
    max_width, line_height = 375, 1.2
    explicit = split_business(name)

    def layout(s):
        if explicit:
            return explicit, max(measure("bold", l, s) for l in explicit)
        lines, width = layout_rich([{"text": str(name).strip(), "bold": True}], max_width, s)
        return [" ".join(seg["text"] for seg in l) for l in lines], width

    def fits(s):
        lines, width = layout(s)
        return width <= max_width and len(lines) <= 2

    size, overflow = fit_size(33.33, 18, fits)
    lines, _ = layout(size)
    first = 1258 if len(lines) == 1 else 1238
    for i, line in enumerate(lines[:2]):
        draw_text(draw, "bold", line, 45, first + i * line_height * size, size, (255, 255, 255))
    return overflow


def _url(canvas, draw, url, color):
    size, overflow = fit_size(17.2, 9, lambda s: measure("medium", url, s) <= 265)
    # 31px yüksekliğindeki dünya ikonuyla dikeyde ortalı
    y = 1292 + (31 - POPPINS_LINE * size) / 2 + POPPINS_ASC * size
    mask = Image.open(GLOBE_MASK_PATH).getchannel("A")
    globe = Image.new("RGBA", mask.size, color)
    globe.putalpha(mask)
    canvas.alpha_composite(globe, (406, 1292))
    draw_text(draw, "medium", url, 441, y, size, color)
    return overflow


def _aa_circle(canvas, cx, cy, r, fill, scale=4):
    """Kenarları yumuşatılmış daire çizer."""
    box = int(r * 2 + 4)
    left, top = int(cx - r) - 2, int(cy - r) - 2
    mask = Image.new("L", (box * scale, box * scale), 0)
    ox, oy = (cx - left) * scale, (cy - top) * scale
    ImageDraw.Draw(mask).ellipse((ox - r * scale, oy - r * scale, ox + r * scale, oy + r * scale), fill=255)
    layer = Image.new("RGBA", (box, box), fill)
    layer.putalpha(mask.resize((box, box), Image.Resampling.LANCZOS))
    canvas.alpha_composite(layer, (left, top))


def _instagram_header(canvas, draw, username):
    """Kullanıcı adı + "● Takip Ediliyor"; sığmazsa birlikte küçülür."""
    x, y = CARD["x"], CARD["y"]
    arimo_asc, arimo_line = 0.905, 1.117

    user_w = lambda k: measure("ui_bold", username, 21 * k)
    follow_w = lambda k: measure("ui_regular", "Takip Ediliyor", 17 * k, 1.4 * k)
    total = lambda k: user_w(k) + (1 + 9 + 2) * k + follow_w(k)
    k = min(1, 665 / total(1))

    head_top, head_h = y + 36, 30
    base_of = lambda size: head_top + (head_h - arimo_line * size) / 2 + arimo_asc * size
    user_x = x + 87
    follow_base = base_of(17 * k)
    dot_x = user_x + user_w(k) + 1 * k
    dot_r = 4.5 * k

    draw_text(draw, "ui_bold", username, user_x, base_of(21 * k), 21 * k, (17, 17, 17))
    _aa_circle(canvas, dot_x + dot_r, follow_base - 1 * k - dot_r, dot_r, (17, 17, 17))
    draw_text(draw, "ui_regular", "Takip Ediliyor", dot_x + (9 + 2) * k, follow_base, 17 * k, (17, 17, 17), 1.4 * k)


# ---- Resimler ----------------------------------------------------------------

def _open(source):
    """Dosya yolu ya da bytes kabul eder; telefon fotoğraflarının EXIF yönünü düzeltir."""
    img = Image.open(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source)
    return ImageOps.exif_transpose(img).convert("RGBA")


def _cover(source, w, h):
    return ImageOps.fit(_open(source), (w, h), Image.Resampling.LANCZOS)


def _contain(source, w, h):
    img = ImageOps.contain(_open(source), (w, h), Image.Resampling.LANCZOS)
    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    box.alpha_composite(img, ((w - img.width) // 2, (h - img.height) // 2))
    return box


def _circle(source, size, scale=4):
    img = _cover(source, size, size)
    mask = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * scale - 1, size * scale - 1), fill=255)
    img.putalpha(mask.resize((size, size), Image.Resampling.LANCZOS))
    return img


# ---- Ana fonksiyon -----------------------------------------------------------

def compose_avantaj(data, debug=False):
    """
    data anahtarları:
      discount (int), description ([{"text", "bold"}]), phone, business, ig_username, sendika_url,
      url_color ("#RRGGBB", opsiyonel)
      ig_avatar, ig_post, business_logo, sendika_logo: dosya yolu ya da bytes
    Döner: (png_bytes, overflow) — overflow True ise bazı metinler alana tam sığmamıştır.
    """
    canvas = Image.open(TEMPLATE_PATH).convert("RGBA")

    canvas.alpha_composite(_cover(data["ig_post"], 763, 587), (CARD["x"] + 21, CARD["y"] + 102))
    canvas.alpha_composite(_circle(data["ig_avatar"], 48), (CARD["x"] + 26, CARD["y"] + 26))
    canvas.alpha_composite(_contain(data["business_logo"], 135, 136), (886, 1172))
    canvas.alpha_composite(_contain(data["sendika_logo"], 134, 133), (719, 1172))

    draw = ImageDraw.Draw(canvas)
    username = str(data["ig_username"]).strip().lstrip("@")
    _instagram_header(canvas, draw, username)

    overflow = any([
        _discount(draw, data["discount"]),
        _description(draw, data["description"]),
        _phone(draw, str(data["phone"]).strip()),
        _business(draw, data["business"]),
        _url(canvas, draw, str(data["sendika_url"]).strip(), normalize_color(data.get("url_color"))),
    ])

    if debug:
        for box in [(66, 145, 446, 235), (470, 100, 932, 292), (629, 305, 974, 350),
                    (45, 1200, 420, 1300), (441, 1292, 706, 1323)]:
            draw.rectangle(box, outline="red", width=2)

    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue(), overflow


# ---- Örnek veriler (test ve /debug_avantaj için) ------------------------------

def _ornek(file):
    return os.path.join(ASSETS, "avantaj", "ornek", file)


def sample_data(long=False):
    from avantaj_steps import parse_stars

    data = {
        "discount": 7,
        "description": parse_stars(
            "*Sendikamıza üyemiz olsun olmasın* itfaiye personeline ve *itfaiye şehit ailelerine* "
            "özel KAMPANYA fiyatına Ek%7 indirim."
        ),
        "phone": "0 312 911 54 51",
        "business": "Presa Di Finica Hotel -Antalya/Finike",
        "ig_avatar": _ornek("ig_profil.jpg"),
        "ig_username": "presadifinicahotelandsuites",
        "ig_post": _ornek("ig_gonderi.jpg"),
        "business_logo": _ornek("isletme_logo.png"),
        "sendika_logo": _ornek("sendika_logo.png"),
        "sendika_url": "bagimsizyerelhaksen.org.tr",
        "url_color": DEFAULT_URL_COLOR,
    }
    if long:
        data.update({
            "discount": 100,
            "description": parse_stars(
                "*Sendikamıza üyemiz olsun olmasın* tüm kamu çalışanlarına, itfaiye personeline, emeklilere ve "
                "*itfaiye şehit ailelerine* özel KAMPANYA fiyatına ek olarak yüzde yüz indirim fırsatı sizleri "
                "bekliyor. Rezervasyon için hemen arayın!"
            ),
            "phone": "+90 (312) 911 54 51 / 0532 000 00 00",
            "business": "Presa Di Finica Hotel And Suites Resort Spa Antalya Finike Merkez",
            "ig_username": "presadifinicahotelandsuites_rs",
            "sendika_url": "www.bagimsizyerelyonetimcalisanlarihaksen.org.tr",
        })
    return data


if __name__ == "__main__":
    os.makedirs("temp", exist_ok=True)
    for long, name in [(False, "temp/avantaj_ornek.png"), (True, "temp/avantaj_ornek_uzun.png")]:
        png, overflow = compose_avantaj(sample_data(long))
        with open(name, "wb") as f:
            f.write(png)
        print(f"{name} (taşma: {overflow})")
