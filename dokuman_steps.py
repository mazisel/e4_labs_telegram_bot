"""Doküman (Sendikal kılavuz PDF) akışının soru adımları ve girdi doğrulama."""
import io
import re
from urllib.parse import urlparse

from PIL import Image

MAX_LOGO_BYTES = 5 * 1024 * 1024

# (anahtar, soru metni)
STEPS = [
    ("sendika_adi", "1/4 — Sendikanın *tam adı* nedir?\nÖrn: Koruma Güvenlik ve Büro Çalışanları Sendikası"),
    ("logo", "2/4 — Sendika *logosunu* gönderin.\nŞeffaflığın korunması için fotoğraf yerine *dosya* (belge) olarak gönderin; PNG önerilir."),
    ("web_url", "3/4 — *Web sitesi* adresi nedir?\nÖrn: https://sendikaniz.org.tr"),
    ("panel_url", "4/4 — *Yönetim paneli* adresi nedir?\nÖrn: sendikaniz.org.tr/admin"),
]


class ValidationError(ValueError):
    pass


def validate_name(text: str) -> str:
    name = " ".join(text.split())
    if not 3 <= len(name) <= 120:
        raise ValidationError("Sendika adı 3-120 karakter olmalı.")
    return name


def normalize_url(text: str) -> str:
    raw = text.strip()
    if not raw or " " in raw:
        raise ValidationError("Geçerli bir adres yazın (boşluk içermemeli).")
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    if not re.match(r"^([a-z0-9ğüşıöç-]+\.)+[a-z]{2,}$", host, re.I):
        raise ValidationError("Adres geçerli bir alan adı içermiyor (örn. sendikaniz.org.tr).")
    return raw.rstrip("/")


def _ton_uzeri_ton(img: Image.Image) -> Image.Image | None:
    """Açık gri/beyaz zemin üstüne beyaz çizilmiş logo (zeminden sadece birkaç ton farklı).

    Zeminden farkı şeffaflığa çevirir ve logoyu saf beyaz yapar. Kontrastlı logolarda None döner.
    """
    gri = img.convert("L")
    w, h = gri.size
    zemin = sorted(gri.getpixel(p) for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)])[1]
    hist = gri.histogram()
    fark = [0] * 256  # |L - zemin| dağılımı
    for v, n in enumerate(hist):
        fark[abs(v - zemin)] += n
    toplam = w * h
    aykiri = sum(fark[61:])  # zeminden 60+ ton farklı pikseller: kontrastlı logo
    if aykiri > 0.01 * toplam:
        return None  # kontrastlı logo: normal yola bırak
    # zemin dışındaki piksellerde "tam görünür" eşiği (gürültü tabanı üstünde)
    taban = 2
    kalan = sum(fark[taban + 1:])
    if kalan < 0.002 * toplam:
        return None  # logo yok denecek kadar az
    ust = 0
    for d in range(255, taban, -1):
        ust += fark[d]
        if ust >= 0.002 * toplam:
            ref = d
            break
    tam = max(taban + 2, int(ref * 0.6))
    tablo = [0 if abs(v - zemin) <= taban else min(255, int((abs(v - zemin) - taban) * 255 / (tam - taban)))
             for v in range(256)]
    alfa = gri.point(tablo)
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(alfa)
    return out


def _beyaz_zemini_sil(img: Image.Image) -> Image.Image:
    """Kenarlardan erişilen opak beyaz zemini şeffaf yapar (iç kısımdaki beyazlara dokunmaz)."""
    from PIL import ImageDraw

    w, h = img.size
    px = img.load()
    kose = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    if not all(a > 250 and min(r, g, b) > 200 for r, g, b, a in kose):
        return img  # zaten şeffaf ya da açık renkli olmayan zemin
    ton = _ton_uzeri_ton(img)  # açık gri zeminde beyaz logo (zemin 200+ tonlarda olabilir)
    if ton is not None:
        return ton
    if not all(min(r, g, b) > 235 for r, g, b, a in kose):
        return img  # gri zeminli kontrastlı logo: dokunma
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        ImageDraw.floodfill(img, xy, (255, 255, 255, 0), thresh=40)
    return img


def validate_logo(data: bytes) -> bytes:
    """Görseli doğrular ve PNG olarak (şeffaflık korunarak) döndürür."""
    if len(data) > MAX_LOGO_BYTES:
        raise ValidationError("Logo 5 MB'dan büyük olamaz.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise ValidationError("Bu dosya bir görsel gibi görünmüyor. PNG veya JPG gönderin.")
    img = img.convert("RGBA")
    img.thumbnail((1200, 1200))
    img = _beyaz_zemini_sil(img)
    alfa = img.getchannel("A").histogram()
    if sum(alfa[128:]) < 0.003 * img.width * img.height:
        raise ValidationError(
            "Logo zeminden ayırt edilemedi (görsel boş görünüyor). Logoyu açık gri zeminde "
            "ya da şeffaf zeminli PNG olarak, *dosya* şeklinde gönderin."
        )
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()
