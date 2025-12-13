# Telegram Görsel Botu

Bu bot, kullanıcıdan aldığı şehir, belediye ismi ve fotoğrafı kullanarak önceden belirlenmiş bir şablon üzerine yerleştirir ve sosyal medya görseli oluşturur.

## Kurulum

1.  **Gereksinimler**:
    *   Python 3.8+
    *   Sanal ortam (Opsiyonel ama önerilir)

2.  **Dosyaları Hazırlama**:
    *   `assets` klasörüne gerekli dosyaları ekleyin:
        *   `template_frame.png` (Transparan şablon, 1080x1080 px önerilir)
        *   `font_bold.ttf` (Belediye ismi fontu)
        *   `font_light.ttf` (Şehir ismi fontu)
    
3.  **Bağımlılıkları Yükleme**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Bot Token Ayarlama**:
    *   `.env.example` dosyasının adını `.env` olarak değiştirin.
    *   Dosyayı açıp `TELEGRAM_BOT_TOKEN=...` kısmına BotFather'dan aldığınız tokeni yapıştırın.

## Çalıştırma

```bash
python main.py
```

## Kullanım

1.  Telegram'da botunuzu başlatın (`/start`).
2.  Bot size sırasıyla şehir ismini, belediye ismini ve fotoğrafı soracaktır.
3.  Bilgileri girdikten sonra görseliniz oluşturulup size gönderilecektir.

## Notlar

*   Kordinatlar (`image_composer.py` içinde `municipality_pos` ve `city_pos`) Photoshop dosyanızın tasarımına göre ayarlanmalıdır. Test ettikten sonra bu değerleri güncelleyebilirsiniz.
