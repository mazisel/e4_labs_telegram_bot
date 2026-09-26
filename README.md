# Telegram Görsel Botu

Bu bot, kullanıcıdan aldığı bilgiler ve fotoğraflar ile sosyal medya şablonları üzerinde hazır görseller üretir.

## Komutlar ve Şablonlar

* **`/katilim`** : Yeni üye / katılım şablonu. Kullanıcıdan sırasıyla **Şehir**, **Belediye** ve **Fotoğraf** alarak görsel oluşturur.
* **`/ziyaret`** : Ziyaret şablonu. Kullanıcıdan sırasıyla **Ziyaret Açıklama Metni** ve **Fotoğraf** alarak görsel oluşturur.
* **`/avantaj`** : Sendika avantaj kampanyası şablonu (1080x1350 PNG). 11 soru sorar (aşağıya bakın), sonunda önizleme + sıkıştırılmamış PNG dosyası gönderir.
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

## Kurulum

1.  **Gereksinimler**:
    *   Python 3.8+
    *   Sanal ortam (Opsiyonel ama önerilir)

2.  **Bağımlılıkları Yükleme**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Bot Token Ayarlama**:
    *   `.env` dosyasını açıp `TELEGRAM_BOT_TOKEN=...` kısmına bot tokeninizi girin.

## Çalıştırma

```bash
python main.py
```

