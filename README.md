# Telegram Görsel Botu

Bu bot, kullanıcıdan aldığı bilgiler ve fotoğraflar ile sosyal medya şablonları üzerinde hazır görseller üretir.

## Komutlar ve Şablonlar

* **`/katilim`** : Yeni üye / katılım şablonu. Kullanıcıdan sırasıyla **Şehir**, **Belediye** ve **Fotoğraf** alarak görsel oluşturur.
* **`/ziyaret`** : Ziyaret şablonu. Kullanıcıdan sırasıyla **Ziyaret Açıklama Metni** ve **Fotoğraf** alarak görsel oluşturur.
* **`/start`** : Karşılama mesajı ve mevcut komut listesini gösterir.
* **`/cancel`** : Devam eden işlemi iptal eder.

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

