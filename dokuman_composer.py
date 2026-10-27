"""Sendikal tanıtım/kullanım kılavuzu şablonlarını (templates/<belge>/tanitim.html) müşteriye özel PDF'e basar.

Kapak kenar boşluksuz, gövde kenar boşluklu ve sayfa numaralı basılıp tek PDF'te
birleştirilir (orijinal render.mjs ile aynı mantık).

Bağımsız test: python dokuman_composer.py  ->  temp/ornek.pdf
"""
import base64
import io
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

A4_GENISLIK, A4_YUKSEKLIK = 595.276, 841.89  # pt

BASE = Path(__file__).parent
# Belge türleri: komut -> (şablon klasörü, görünen ad, dosya adı eki).
# Yeni belge eklemek için templates/<klasor>/tanitim.html (+ stil.css, fonts/) koyup buraya bir satır ekleyin.
# "kenar" verilmezse KENAR kullanılır. Rol kılavuzlarında (hukuk, ilçe, iş yeri) orijinal PDF'lerden ölçülen
# kenar boşlukları geçer; üst değer px çünkü Chromium üst kenarı 1 px eksik uyguluyor (54px -> 39,75 pt).
ROL_KENAR = {"top": "54px", "right": "18mm", "bottom": "16mm", "left": "18mm"}
DOKUMANLAR = {
    "yonetim": {"klasor": "yonetim", "ad": "Yönetim kılavuzu", "ek": "yonetim-kilavuz",
                "alt": "Dijital Sendika Yönetim Sistemi — Tanıtım ve Kullanım Kılavuzu"},
    "hukuk": {"klasor": "hukuk", "ad": "Hukuk sorumlusu kılavuzu", "ek": "hukuk-sorumlusu-kilavuz",
              "alt": "Sendikal — Hukuk Sorumlusu Kullanım Kılavuzu", "kenar": ROL_KENAR},
    "ilce": {"klasor": "ilce", "ad": "İlçe temsilcisi kılavuzu", "ek": "ilce-temsilcisi-kilavuz",
             "alt": "Sendikal — İlçe Temsilcisi Kullanım Kılavuzu", "kenar": ROL_KENAR},
    "isyeri": {"klasor": "isyeri", "ad": "İş yeri temsilcisi kılavuzu", "ek": "is-yeri-temsilcisi-kilavuz",
               "alt": "Sendikal — İş Yeri Temsilcisi Kullanım Kılavuzu", "kenar": ROL_KENAR},
    "sube": {"klasor": "sube", "ad": "Şube yöneticisi kılavuzu", "ek": "sube-yoneticisi-kilavuz",
             "alt": "Sendikal — Şube Yöneticisi Kullanım Kılavuzu", "kenar": ROL_KENAR},
}

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

KENAR = {"top": "15mm", "right": "15mm", "bottom": "17mm", "left": "15mm"}

ALT_BILGI = """
<div style="width:100%; font-family:Helvetica,Arial,sans-serif; font-size:7.5pt;
            color:#94a3b8; padding:0 {pad}; display:flex;
            justify-content:space-between; align-items:center;">
  <span style="letter-spacing:.06em;">{alt}</span>
  <span><span class="pageNumber"></span></span>
</div>"""


def slugify(text: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    s = re.sub(r"[^a-z0-9]+", "-", text.translate(tr).lower()).strip("-")
    return s[:60] or "sendika"


def _display(url: str) -> str:
    p = urlparse(url)
    return (p.netloc + p.path).rstrip("/")


def _logo_koyu_mu(png: bytes) -> bool:
    """Koyu/renkli logo mu? Öyleyse kapakta açık zeminli rozete konur."""
    from PIL import Image

    img = Image.open(io.BytesIO(png)).convert("RGBA").resize((64, 64))
    toplam = agirlik = 0.0
    for r, g, b, a in img.getdata():
        toplam += (0.299 * r + 0.587 * g + 0.114 * b) / 255 * a
        agirlik += a
    return agirlik == 0 or toplam / agirlik < 0.75


def ayarlar(sendika_adi: str, logo_png: bytes | None, web_url: str, panel_url: str) -> dict:
    today = date.today()
    return {
        "sendikaAdi": sendika_adi,
        "logoDosyasi": "data:image/png;base64," + base64.b64encode(logo_png).decode() if logo_png else "",
        "logoRozet": False,  # logo doğrudan kapakta durur, beyaz zemin yok
        "markaRengi": "#1e40af",
        "webSitesi": _display(web_url),
        "panelAdresi": _display(panel_url),
        "tarih": f"{AYLAR[today.month - 1]} {today.year}",  # oluşturulduğu günün ay ve yılı
    }


def render_pdf(belge: str, sendika_adi: str, logo_png: bytes | None, web_url: str, panel_url: str) -> bytes:
    from playwright.sync_api import sync_playwright

    init = "window.AYARLAR = " + json.dumps(ayarlar(sendika_adi, logo_png, web_url, panel_url)) + ";"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.add_init_script(init)
        page.goto((BASE / "templates" / DOKUMANLAR[belge]["klasor"] / "tanitim.html").as_uri(), wait_until="networkidle")
        page.wait_for_timeout(400)  # logo/renk uygulanana kadar bekle
        page.emulate_media(media="print")

        def bas(mod: str, **kw) -> bytes:
            page.evaluate("m => { document.body.dataset.mode = m }", mod)
            # mod değişince görünür olan metnin yazı tipleri yüklenmeden basılmasın
            page.evaluate("""() => Promise.all(['400', '500', '600', '700'].map(
                w => document.fonts.load(w + ' 20px Poppins'))).then(() => document.fonts.ready)""")
            return page.pdf(width="210mm", height="297mm", print_background=True, **kw)

        kapak = bas("cover", margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, page_ranges="1")
        kenar = DOKUMANLAR[belge].get("kenar", KENAR)
        govde = bas("body", margin=kenar, display_header_footer=True,
                    header_template="<div></div>",
                    footer_template=ALT_BILGI.replace("{alt}", DOKUMANLAR[belge]["alt"]).replace("{pad}", kenar["left"]))
        browser.close()

    out = PdfWriter()
    for parca in (kapak, govde):
        for pg in PdfReader(io.BytesIO(parca)).pages:
            # Chromium sayfayı 210 mm'den birkaç yüzde mm geniş üretir; içerik sol-üste yaslanır ve
            # sağ/altta beyaz şerit kalır. Tam A4'e (595.276 x 841.89 pt) kırp.
            ust = float(pg.mediabox.top)
            kutu = RectangleObject((0, ust - A4_YUKSEKLIK, A4_GENISLIK, ust))
            pg.mediabox = pg.cropbox = pg.trimbox = pg.bleedbox = pg.artbox = kutu
            out.add_page(pg)
    out.add_metadata({
        "/Title": f"{sendika_adi} — Dijital Sendika Yönetim Sistemi Kılavuzu",
        "/Subject": "Sendika dijital yönetim sisteminin modülleri ve kullanımı",
        "/Creator": "Sendikal",
    })
    buf = io.BytesIO()
    out.write(buf)
    return buf.getvalue()


def _sample_logo() -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((20, 20, 380, 380), fill="#1e40af")
    d.ellipse((60, 60, 340, 340), outline="white", width=8)
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


if __name__ == "__main__":
    out = BASE / "temp"
    out.mkdir(exist_ok=True)
    pdf = render_pdf(
        "yonetim",
        "Örnek Kamu Çalışanları Sendikası",
        _sample_logo(),
        "https://ornek-sendika.org.tr",
        "https://ornek-sendika.org.tr/admin",
    )
    (out / "ornek.pdf").write_bytes(pdf)
    print("temp/ornek.pdf yazıldı", len(pdf), "bayt")
