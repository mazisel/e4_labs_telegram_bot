# Telegram Görsel Botu

Bu bot, kullanıcıdan aldığı bilgiler ve fotoğraflar ile sosyal medya şablonları üzerinde hazır görseller üretir.

## Komutlar ve Şablonlar

* **`/katilim`** : Yeni üye / katılım şablonu. Kullanıcıdan sırasıyla **Şehir**, **Belediye** ve **Fotoğraf** alarak görsel oluşturur.
* **`/ziyaret`** : Ziyaret şablonu. Kullanıcıdan sırasıyla **Ziyaret Açıklama Metni** ve **Fotoğraf** alarak görsel oluşturur.
* **`/avantaj`** : Sendika avantaj kampanyası şablonu (1080x1350 PNG). 11 soru sorar (aşağıya bakın), sonunda önizleme + sıkıştırılmamış PNG dosyası gönderir.
* **`/yonetim`, `/hukuk`, `/ilce`, `/isyeri`, `/sube`, `/tumu`** : Sendikal tanıtım ve kullanım kılavuzunu müşteriye özel PDF olarak hazırlar (aşağıya bakın). `/kilavuz` = `/yonetim`.
* **`/start`** : Karşılama mesajı ve mevcut komut listesini gösterir.
* **`/cancel`** : Devam eden işlemi iptal eder.

### `/avantaj` şablonu

Sırasıyla sorulanlar: indirim yüzdesi → açıklama → telefon → işletme adı + konum → Instagram profil fotoğrafı →
Instagram kullanıcı adı → Instagram gönderi fotoğrafı → işletme logosu → sendika logosu → sendika site adresi →
site adresi rengi (butonla seçilir, varsayılan turuncu).

* `/geri` bir önceki soruya döner.
* Açıklamada `*yıldız*` arasındaki kısımlar kalın yazılır (Telegram'ın kalın biçimlendirmesi de çalışır).
* İşletme adında ` -` işaretinden sonrası ikinci satıra geçer (örn. `Presa Di Finica Hotel -Antalya/Finike`).
* Resimler fotoğraf ya da dosya olarak gönderilebilir; logolarda dosya olarak göndermek şeffaflığı korur.
* Uzun metinler alanına sığacak şekilde otomatik küçültülür; sığmazsa bot uyarır.
* `/debug_avantaj` örnek verilerle, metin alanları işaretli bir görsel üretir.

Dosyalar: `avantaj_steps.py` (sorular ve doğrulamalar), `avantaj_composer.py` (görsel üretimi; koordinatlar
"Klasik İndirim.psd"den). `assets/avantaj/sablon.png` arka plan ile Instagram kartının sabit kısımlarını
(gölge, ikonlar) içerir. Botsuz test için `python avantaj_composer.py` → `temp/avantaj_ornek.png`.
Arimo ve Poppins fontları SIL Open Font License ile dağıtılır (`assets/*-OFL.txt`).

### Kılavuz PDF komutları (`/yonetim`, `/hukuk`, `/ilce`, `/isyeri`, `/sube`, `/tumu`)

"Dijital Sendika Yönetim Sistemi" tanıtım ve kullanım kılavuzunu sendikaya özel PDF olarak üretir.
Komut hangi belgeyse onu hazırlar; `/tumu` beş kılavuzu tek seferde gönderir. Sırasıyla sorulanlar:

1. Sendika adı → kapak
2. Logo (şeffaflığın korunması için *dosya* olarak, PNG önerilir) → kapak. Beyaz/açık gri zemin otomatik şeffaf yapılır.
3. Web sitesi → kapak alt şeridi ve son sayfa
4. Yönetim paneli adresi → "Panele ilk giriş" adımı ve son sayfa

* `/geri` bir önceki soruya döner (özet ekranında da çalışır), `/cancel` iptal eder.
* Özet ekranındaki **PDF'i hazırla** düğmesi üretimi başlatır. Belge tarihi (ay/yıl) üretim gününden alınır.
* `ALLOWED_USER_IDS` doluysa bu komutları yalnızca listedeki Telegram ID'leri kullanabilir; yetkisiz kullanıcıya
  ID'si gösterilir. Boşsa herkese açıktır. Diğer komutlar bu listeden etkilenmez.

Dosyalar: `dokuman_steps.py` (sorular, URL/logo doğrulama), `dokuman_composer.py` (şablona ayarları verip Chromium
ile PDF basar; kapak kenar boşluksuz, gövde sayfa numaralı basılıp birleştirilir). Şablonlar
`templates/<belge>/tanitim.html` + `stil.css` + `fonts/`; yeni belge için klasör ekleyip `dokuman_composer.DOKUMANLAR`
sözlüğüne bir satır eklemek yeterlidir (komut otomatik tanınır). Şablonlarda `window.AYARLAR` yoktur, sayfa
yüklenmeden önce `dokuman_composer.py` verir. Kapaktaki "S" işareti şablona gömülü SVG'dir; yeniden çıkarmak için
`tools/s_isareti_cikar.py` (OpenCV, yalnızca geliştirme amaçlı) kullanılır.

Botsuz test: `python dokuman_composer.py` → `temp/ornek.pdf` (yerelde önce `playwright install chromium` gerekir).
Docker'da: `docker compose run --rm telegram-bot python dokuman_composer.py`.

## Kurulum

1.  **Gereksinimler**:
    *   Python 3.10+
    *   Sanal ortam (Opsiyonel ama önerilir)

2.  **Bağımlılıkları Yükleme**:
    ```bash
    pip install -r requirements.txt
    playwright install chromium   # kılavuz PDF komutları için
    ```

3.  **Bot Token Ayarlama**:
    *   `.env.example` dosyasını `.env` olarak kopyalayıp `TELEGRAM_BOT_TOKEN=...` kısmına bot tokeninizi girin.
    *   İsteğe bağlı: `ALLOWED_USER_IDS` ile kılavuz komutlarını belirli Telegram ID'leriyle sınırlayın.

## Çalıştırma

```bash
python main.py
```

