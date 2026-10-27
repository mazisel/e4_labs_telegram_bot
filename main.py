import os
import io
import time
import asyncio
import logging
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import NetworkError, TelegramError, TimedOut
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from PIL import Image

from dotenv import load_dotenv
from image_composer import ImageComposer
from avantaj_composer import compose_avantaj, sample_data
from avantaj_steps import STEPS as AVANTAJ_STEPS, DEFAULTS as AVANTAJ_DEFAULTS
import dokuman_composer
import dokuman_steps

# Load env variables
load_dotenv()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# States
CITY, MUNICIPALITY, PHOTO = range(3)
ZIYARET_TEXT, ZIYARET_PHOTO = range(3, 5)
AVANTAJ = 5
DOKUMAN_ASK, DOKUMAN_CONFIRM = range(6, 8)

MAX_IMAGE_BYTES = 20 * 1024 * 1024  # Telegram getFile sınırı

# Doküman komutlarını kullanabilecek Telegram ID'leri; boşsa herkese açık
DOKUMAN_ALLOWED = {int(i) for i in os.getenv("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if i}

# Initialize Composer
composer = ImageComposer()

async def katilim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['debug'] = False
    await update.message.reply_text(
        "Katılım görseli oluşturma işlemi başlatıldı.\n\n"
        "Lütfen şehir ismini giriniz (Örn: İzmir):"
    )
    return CITY

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Merhaba! Görsel oluşturma botuna hoş geldiniz.\n\n"
        "Kullanabileceğiniz şablonlar:\n"
        "🔹 /katilim - Yeni katılım görseli oluştur\n"
        "🔹 /ziyaret - Ziyaret görseli oluştur\n"
        "🔹 /avantaj - Avantaj kampanyası görseli oluştur\n\n"
        "Sendikal kılavuz PDF'leri:\n"
        "📄 /yonetim - Yönetim kılavuzu\n"
        "📄 /hukuk - Hukuk sorumlusu kılavuzu\n"
        "📄 /ilce - İlçe temsilcisi kılavuzu\n"
        "📄 /isyeri - İş yeri temsilcisi kılavuzu\n"
        "📄 /sube - Şube yöneticisi kılavuzu\n"
        "📄 /tumu - Tüm kılavuzları tek seferde hazırla\n\n"
        "Bir önceki soruya dönmek için: /geri\n"
        "İşlemi iptal etmek için: /cancel"
    )
    return ConversationHandler.END

async def city_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    await update.message.reply_text(
        f"Şehir: {update.message.text}\n"
        "Şimdi lütfen belediye ismini giriniz (Örn: Konak Belediyesi):"
    )
    return MUNICIPALITY

async def municipality_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['municipality'] = update.message.text
    await update.message.reply_text(
        f"Belediye: {update.message.text}\n"
        "Son olarak, lütfen fotoğrafı gönderiniz:"
    )
    return PHOTO

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['debug'] = True
    await update.message.reply_text("Katılım Debug modu açıldı. Şimdi bir fotoğraf gönderin, kılavuz çizgileriyle gelecek.")
    return PHOTO

async def photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_photo = update.message.photo[-1] # Get largest size
    
    file_id = user_photo.file_id
    new_file = await context.bot.get_file(file_id)
    
    # Ensure temporary folder exists
    os.makedirs("temp", exist_ok=True)
    
    # Download User Photo
    user_photo_path = f"temp/{file_id}.jpg"
    await new_file.download_to_drive(user_photo_path)
    
    await update.message.reply_text("Fotoğraf alındı. İşleniyor, lütfen bekleyin...")
    
    # Process Image
    city = context.user_data.get('city', 'Debug City')
    municipality = context.user_data.get('municipality', 'Debug Municipality')
    
    if context.user_data.get('debug'):
        composer.enable_debug()
    else:
        composer.debug = False
        
    output_path = f"temp/output_{file_id}.jpg"
    
    result_path = composer.compose(user_photo_path, city, municipality, output_path)
    
    if result_path and os.path.exists(result_path):
        await update.message.reply_photo(photo=open(result_path, 'rb'))
        # Cleanup
        os.remove(result_path)

        # Instagram story (1080x1920) version
        story_path = f"temp/story_{file_id}.jpg"
        if composer.compose_katilim_story(user_photo_path, city, municipality, story_path):
            await update.message.reply_document(document=open(story_path, 'rb'), filename="katilim_story.jpg", caption="Instagram story boyutu (1080x1920)")
            os.remove(story_path)
    else:
        await update.message.reply_text("Bir hata oluştu, görsel oluşturulamadı.")
    
    # Clean input photo
    if os.path.exists(user_photo_path):
        os.remove(user_photo_path)
        
    await update.message.reply_text(
        "Görsel oluşturuldu! Yeni bir işlem için:\n"
        "🔹 /katilim - Yeni katılım görseli oluştur\n"
        "🔹 /ziyaret - Ziyaret görseli oluştur\n"
        "🔹 /avantaj - Avantaj kampanyası görseli oluştur"
    )
    return ConversationHandler.END

# --- ZİYARET ŞABLONU ---
async def ziyaret_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['debug'] = False
    await update.message.reply_text(
        "Ziyaret görseli oluşturma işlemi başlatıldı.\n\n"
        "Lütfen görsel üzerinde yer alacak açıklama metnini yazınız:"
    )
    return ZIYARET_TEXT

async def ziyaret_text_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ziyaret_text'] = update.message.text
    await update.message.reply_text(
        "Metin kaydedildi.\n\n"
        "Şimdi lütfen ziyaret fotoğrafını gönderiniz:"
    )
    return ZIYARET_PHOTO

async def debug_ziyaret_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['debug'] = True
    context.user_data['ziyaret_text'] = "Genel Başkanımız ve beraberindeki heyetimiz, belediye başkanlığını makamında ziyaret etti."
    await update.message.reply_text("Ziyaret Debug modu açıldı. Şimdi bir fotoğraf gönderin, kılavuz çizgileriyle gelecek.")
    return ZIYARET_PHOTO

async def ziyaret_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_photo = update.message.photo[-1]
    
    file_id = user_photo.file_id
    new_file = await context.bot.get_file(file_id)
    
    os.makedirs("temp", exist_ok=True)
    user_photo_path = f"temp/{file_id}.jpg"
    await new_file.download_to_drive(user_photo_path)
    
    await update.message.reply_text("Fotoğraf alındı. Ziyaret görseli hazırlanıyor, lütfen bekleyin...")
    
    text = context.user_data.get('ziyaret_text', '')
    
    if context.user_data.get('debug'):
        composer.enable_debug()
    else:
        composer.debug = False
        
    output_path = f"temp/output_ziyaret_{file_id}.jpg"
    result_path = composer.compose_ziyaret(user_photo_path, text, output_path)
    
    if result_path and os.path.exists(result_path):
        await update.message.reply_photo(photo=open(result_path, 'rb'))
        os.remove(result_path)
    else:
        await update.message.reply_text("Bir hata oluştu, görsel oluşturulamadı.")
        
    if os.path.exists(user_photo_path):
        os.remove(user_photo_path)
        
    await update.message.reply_text(
        "Görsel oluşturuldu! Yeni bir işlem için:\n"
        "🔹 /ziyaret - Yeni ziyaret görseli oluştur\n"
        "🔹 /katilim - Yeni katılım görseli oluştur\n"
        "🔹 /avantaj - Avantaj kampanyası görseli oluştur"
    )
    return ConversationHandler.END

# --- AVANTAJ ŞABLONU ---
# Sorular avantaj_steps.py'de, görsel avantaj_composer.py'de. Adım numarası ve cevaplar
# (resimler bytes olarak) user_data'da tutulur; görsel üretilince/iptalde temizlenir.
async def ask_avantaj_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = AVANTAJ_STEPS[context.user_data['avantaj_step']]
    await update.message.reply_text(step['prompt'], reply_markup=ReplyKeyboardRemove())

async def avantaj_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['avantaj_step'] = 0
    context.user_data['avantaj_data'] = {}
    await ask_avantaj_step(update, context)
    return AVANTAJ

async def avantaj_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data['avantaj_step'] > 0:
        context.user_data['avantaj_step'] -= 1
        context.user_data['avantaj_data'].pop(AVANTAJ_STEPS[context.user_data['avantaj_step']]['key'], None)
    await ask_avantaj_step(update, context)
    return AVANTAJ

async def receive_avantaj_image(message):
    """Fotoğraf ya da resim dosyasını indirip bytes döner; uygun değilse kullanıcıya yazıp None döner."""
    document = message.document
    if document and (document.mime_type or '').lower() not in ('image/png', 'image/jpeg', 'image/webp'):
        document = None
    file = message.photo[-1] if message.photo else document
    if not file:
        await message.reply_text("Lütfen bir resim gönderin (JPG, PNG veya WEBP; fotoğraf ya da dosya olarak).")
        return None
    if file.file_size and file.file_size > MAX_IMAGE_BYTES:
        await message.reply_text("Resim 20 MB'tan büyük olamaz.")
        return None

    tg_file = await file.get_file()
    data = bytes(await tg_file.download_as_bytearray())
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        await message.reply_text("Resim okunamadı, lütfen başka bir resim gönderin.")
        return None
    return data

ALBUM_KEYS = ['ig_avatar', 'ig_post', 'business_logo']  # albümdeki görsellerin sırası
ALBUM_WAIT = 1.5  # albümün son mesajından sonra beklenen süre (sn)
_album_tasks = set()

def _is_image(message):
    doc = message.document
    return bool(message.photo or (doc and (doc.mime_type or '').lower() in ('image/png', 'image/jpeg', 'image/webp')))

async def avantaj_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verisi eksik ilk adımı sorar; hepsi tamamsa görseli üretir."""
    data = context.user_data['avantaj_data']
    for i, step in enumerate(AVANTAJ_STEPS):
        if step['key'] not in data:
            context.user_data['avantaj_step'] = i
            await ask_avantaj_step(update, context)
            return AVANTAJ
    return await send_avantaj(update, context, {**AVANTAJ_DEFAULTS, **data})

async def avantaj_album_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İlk adımda gelen görsel(ler): albümün parçalarını toplar, son parçadan sonra işler.
    Update'ler sırayla işlendiği için bekleme handler içinde değil, ayrı görevde yapılır."""
    message = update.message
    value = await receive_avantaj_image(message)
    if value is None:
        return AVANTAJ

    album = context.user_data.setdefault('avantaj_album', {'items': []})
    album['items'].append((message.message_id, value))
    task = asyncio.create_task(avantaj_album_done(update, context, len(album['items'])))
    _album_tasks.add(task)
    task.add_done_callback(_album_tasks.discard)
    return AVANTAJ

async def avantaj_album_done(update: Update, context: ContextTypes.DEFAULT_TYPE, count):
    await asyncio.sleep(ALBUM_WAIT)
    album = context.user_data.get('avantaj_album')
    if not album or len(album['items']) != count:  # yeni parça geldi ya da işlem iptal edildi
        return
    context.user_data.pop('avantaj_album')
    data = context.user_data['avantaj_data']
    try:
        items = [img for _, img in sorted(album['items'])]
        for key, img in zip(ALBUM_KEYS, items):
            data[key] = img
        if len(items) > len(ALBUM_KEYS):
            await update.message.reply_text(f"İlk {len(ALBUM_KEYS)} görsel kullanıldı, fazlası yok sayıldı.")
        await avantaj_next(update, context)
    except Exception:
        logging.exception("Avantaj albümü işlenemedi")
        context.user_data.clear()
        await update.message.reply_text("Bir hata oluştu. /avantaj ile tekrar deneyebilirsiniz.")

async def avantaj_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if 'avantaj_step' not in context.user_data:  # görsel üretildi ya da iptal edildi
        await message.reply_text("Yeni bir görsel için /avantaj yazın.")
        return ConversationHandler.END
    step = AVANTAJ_STEPS[context.user_data['avantaj_step']]

    if context.user_data['avantaj_step'] == 0 and _is_image(message):
        return await avantaj_album_part(update, context)

    if step['kind'] == 'image':
        value = await receive_avantaj_image(message)
        if value is None:
            return AVANTAJ
    else:
        if message.text is None:
            await message.reply_text(f"Bu adımda metin bekleniyor.\n\n{step['prompt']}")
            return AVANTAJ
        result, value = step['parse'](message.text, message.entities)
        if result == 'error':
            await message.reply_text(value)
            return AVANTAJ

    if step['kind'] == 'text':
        context.user_data['avantaj_data'].update(value)
    else:
        context.user_data['avantaj_data'][step['key']] = value
    return await avantaj_next(update, context)

async def debug_avantaj_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Avantaj Debug modu: örnek verilerle, metin alanları işaretli görsel üretiliyor.")
    return await send_avantaj(update, context, sample_data(), debug=True)

async def send_avantaj(update: Update, context: ContextTypes.DEFAULT_TYPE, data, debug=False):
    await update.message.reply_text("Avantaj görseli hazırlanıyor, lütfen bekleyin...", reply_markup=ReplyKeyboardRemove())
    try:
        # Görsel üretimi CPU'yu meşgul ettiği için ayrı thread'de; bu sırada bot diğer kullanıcılara cevap verebilir.
        png, overflow = await asyncio.to_thread(compose_avantaj, data, debug)
    except Exception:
        logging.exception("Avantaj görseli oluşturulamadı")
        await update.message.reply_text("Bir hata oluştu, görsel oluşturulamadı. /avantaj ile tekrar deneyebilirsiniz.")
        context.user_data.clear()
        return ConversationHandler.END

    filename = f"avantaj-{data['discount']}-{int(time.time())}.png"
    await update.message.reply_photo(photo=png, caption="Önizleme")
    await update.message.reply_document(document=png, filename=filename, caption="Sıkıştırılmamış PNG")
    if overflow:
        await update.message.reply_text(
            "⚠️ Bazı metinler alana tam sığmadı, lütfen görseli kontrol edin. "
            "Metni kısaltıp /avantaj ile tekrar deneyebilirsiniz."
        )

    context.user_data.clear()
    await update.message.reply_text(
        "Görsel oluşturuldu! Yeni bir işlem için:\n"
        "🔹 /avantaj - Yeni avantaj kampanyası görseli oluştur\n"
        "🔹 /katilim - Yeni katılım görseli oluştur\n"
        "🔹 /ziyaret - Ziyaret görseli oluştur"
    )
    return ConversationHandler.END

# --- DOKÜMAN (SENDİKAL KILAVUZ PDF) ---
# Sorular dokuman_steps.py'de, PDF dokuman_composer.py'de (templates/<belge>/ şablonları, Chromium ile basılır).
# Belge türü, adım numarası ve cevaplar user_data'da dokuman_ önekiyle tutulur.
async def retry(fn, *args, **kwargs):
    """Telegram'a bağlantı anlık kopunca gönderimi birkaç kez yeniden dener."""
    for deneme in range(5):
        try:
            return await fn(*args, **kwargs)
        except (NetworkError, TimedOut):
            if deneme == 4:
                raise
            logging.warning("Telegram bağlantı hatası, yeniden deneniyor (%d/4)", deneme + 1)
            await asyncio.sleep(1.5 * (deneme + 1))

def dokuman_allowed(update: Update) -> bool:
    user = update.effective_user
    return bool(user) and (not DOKUMAN_ALLOWED or user.id in DOKUMAN_ALLOWED)

async def dokuman_deny(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text(
        f"Kılavuz komutlarını kullanma yetkiniz yok. Telegram ID'niz: {update.effective_user.id}"
    )
    return ConversationHandler.END

async def ask_dokuman_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, prompt = dokuman_steps.STEPS[context.user_data['dokuman_step']]
    await retry(update.effective_message.reply_text, prompt, parse_mode=ParseMode.MARKDOWN, reply_markup=ReplyKeyboardRemove())

async def dokuman_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Komut hangi belgeyse onu başlatır (/yonetim, /hukuk ...); /kilavuz = yönetim, /tumu = hepsi."""
    if not dokuman_allowed(update):
        return await dokuman_deny(update, context)
    komut = (update.message.text or "").split()[0].lstrip("/").split("@")[0].lower()
    context.user_data.clear()
    context.user_data['dokuman_belge'] = komut if komut in dokuman_composer.DOKUMANLAR or komut == "tumu" else "yonetim"
    context.user_data['dokuman_step'] = 0
    context.user_data['dokuman_data'] = {}
    await ask_dokuman_step(update, context)
    return DOKUMAN_ASK

async def dokuman_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('dokuman_step')
    if step is None:
        return ConversationHandler.END
    # özet ekranındayken step == len(STEPS); son adıma dön
    context.user_data['dokuman_step'] = max(0, min(step, len(dokuman_steps.STEPS)) - 1)
    await ask_dokuman_step(update, context)
    return DOKUMAN_ASK

async def dokuman_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not dokuman_allowed(update):
        return await dokuman_deny(update, context)
    msg = update.message
    if 'dokuman_step' not in context.user_data:
        await msg.reply_text("Yeni bir kılavuz için /start ile komutlara bakın.")
        return ConversationHandler.END
    if context.user_data['dokuman_step'] >= len(dokuman_steps.STEPS):
        return await dokuman_summary(update, context)  # özet gönderimi önceki seferde kopmuşsa yeniden gönder
    key, _ = dokuman_steps.STEPS[context.user_data['dokuman_step']]
    try:
        if key == "logo":
            if msg.document:
                tg_file = await retry(msg.document.get_file)
            elif msg.photo:
                tg_file = await retry(msg.photo[-1].get_file)  # sıkıştırılmış: şeffaflık kaybolur
            else:
                raise dokuman_steps.ValidationError("Logoyu dosya veya fotoğraf olarak gönderin.")

            async def indir() -> bytes:
                buf = io.BytesIO()  # her denemede temiz tampon
                await tg_file.download_to_memory(buf)
                return buf.getvalue()

            value = dokuman_steps.validate_logo(await retry(indir))
        else:
            if not msg.text:
                raise dokuman_steps.ValidationError("Lütfen metin olarak yazın.")
            value = {
                "sendika_adi": dokuman_steps.validate_name,
                "web_url": dokuman_steps.normalize_url,
                "panel_url": dokuman_steps.normalize_url,
            }[key](msg.text)
    except dokuman_steps.ValidationError as e:
        await msg.reply_text(f"⚠️ {e}")
        return DOKUMAN_ASK
    except TelegramError:
        logging.exception("Telegram'dan dosya alınamadı")
        await msg.reply_text("⚠️ Dosya Telegram'dan alınamadı (bağlantı zaman aşımı). Logoyu tekrar gönderin.")
        return DOKUMAN_ASK

    context.user_data['dokuman_data'][key] = value
    context.user_data['dokuman_step'] += 1
    if context.user_data['dokuman_step'] < len(dokuman_steps.STEPS):
        await ask_dokuman_step(update, context)
        return DOKUMAN_ASK
    return await dokuman_summary(update, context)

async def dokuman_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data['dokuman_data']
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ PDF'i hazırla", callback_data="dokuman_ok"),
        InlineKeyboardButton("❌ İptal", callback_data="dokuman_no"),
    ]])
    await retry(
        update.effective_message.reply_text,
        f"Özet:\n• Sendika: {d['sendika_adi']}\n• Logo: alındı\n"
        f"• Web sitesi: {d['web_url']}\n• Yönetim paneli: {d['panel_url']}\n\n"
        "Düzeltmek için /geri yazabilirsiniz.",
        reply_markup=kb,
    )
    return DOKUMAN_CONFIRM

async def dokuman_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except TelegramError:
        pass  # düğme bildirimi geç kalmış olabilir; işlemi yine de sürdür
    if not dokuman_allowed(update):
        return await dokuman_deny(update, context)
    if q.data != "dokuman_ok" or 'dokuman_data' not in context.user_data:
        context.user_data.clear()
        await q.edit_message_text("İptal edildi.")
        return ConversationHandler.END

    d = context.user_data['dokuman_data']
    belge = context.user_data['dokuman_belge']
    belgeler = list(dokuman_composer.DOKUMANLAR) if belge == "tumu" else [belge]
    await q.edit_message_text("PDF hazırlanıyor, birkaç saniye sürebilir…")
    for belge in belgeler:
        info = dokuman_composer.DOKUMANLAR[belge]
        try:
            # Chromium ile basım uzun sürdüğü için ayrı thread'de; bu sırada bot diğer kullanıcılara cevap verebilir.
            pdf = await asyncio.to_thread(
                dokuman_composer.render_pdf, belge, d['sendika_adi'], d['logo'], d['web_url'], d['panel_url']
            )
        except Exception:
            logging.exception("PDF üretilemedi: %s", belge)
            await q.message.reply_text(f"❌ {info['ad']} üretilirken hata oluştu. Tekrar deneyin.")
            continue
        name = f"{dokuman_composer.slugify(d['sendika_adi'])}-{info['ek']}.pdf"
        await retry(q.message.reply_document, pdf, filename=name,
                    caption=f"{d['sendika_adi']} — {info['ad']} hazır.")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # yarım kalan /avantaj resimlerini bellekten at
    await update.message.reply_text("İşlem iptal edildi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN or TOKEN == "your_token_here":
        print("Error: TELEGRAM_BOT_TOKEN not set in .env file.")
        exit(1)

    application = (
        ApplicationBuilder().token(TOKEN)
        # varsayılan 5 sn bağlantı zaman aşımı dosya indirme/PDF gönderiminde yetmiyor
        .connect_timeout(30).read_timeout(60).write_timeout(60).pool_timeout(30)
        .get_updates_connect_timeout(30).get_updates_read_timeout(60)
        .build()
    )
    
    # Unified Conversation Handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('katilim', katilim_command),
            CommandHandler('ziyaret', ziyaret_command),
            CommandHandler('debug', debug_command),
            CommandHandler('debug_ziyaret', debug_ziyaret_command),
            CommandHandler('avantaj', avantaj_command),
            CommandHandler('debug_avantaj', debug_avantaj_command),
            CommandHandler([*dokuman_composer.DOKUMANLAR, 'kilavuz', 'tumu'], dokuman_command),
            CommandHandler('start', start),
        ],
        states={
            CITY: [MessageHandler(filters.TEXT & (~filters.COMMAND), city_entered)],
            MUNICIPALITY: [MessageHandler(filters.TEXT & (~filters.COMMAND), municipality_entered)],
            PHOTO: [MessageHandler(filters.PHOTO, photo_received)],
            ZIYARET_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), ziyaret_text_entered)],
            ZIYARET_PHOTO: [MessageHandler(filters.PHOTO, ziyaret_photo_received)],
            AVANTAJ: [
                CommandHandler('geri', avantaj_back),
                MessageHandler(~filters.COMMAND, avantaj_input),
            ],
            DOKUMAN_ASK: [
                CommandHandler('geri', dokuman_back),
                MessageHandler((filters.TEXT | filters.Document.ALL | filters.PHOTO) & ~filters.COMMAND, dokuman_answer),
            ],
            DOKUMAN_CONFIRM: [
                CommandHandler('geri', dokuman_back),
                CallbackQueryHandler(dokuman_confirm, pattern=r'^dokuman_(ok|no)$'),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start),
        ],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    
    print("Bot is running...")
    application.run_polling()
