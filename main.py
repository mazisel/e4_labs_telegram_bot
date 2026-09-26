import os
import io
import time
import asyncio
import logging
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from PIL import Image

from dotenv import load_dotenv
from image_composer import ImageComposer
from avantaj_composer import compose_avantaj, sample_data
from avantaj_steps import STEPS as AVANTAJ_STEPS, COLORS as AVANTAJ_COLORS

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

MAX_IMAGE_BYTES = 20 * 1024 * 1024  # Telegram getFile sınırı

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
    if step['kind'] == 'color':
        labels = [label for label, _ in AVANTAJ_COLORS]
        rows = [labels[i:i + 2] for i in range(0, len(labels), 2)]
        markup = ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)
    else:
        markup = ReplyKeyboardRemove()
    await update.message.reply_text(step['prompt'], reply_markup=markup)

async def avantaj_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['avantaj_step'] = 0
    context.user_data['avantaj_data'] = {}
    await update.message.reply_text(
        "Avantaj kampanyası görseli oluşturma işlemi başlatıldı.\n\n"
        "Bir önceki soruya dönmek için: /geri\n"
        "İşlemi iptal etmek için: /cancel"
    )
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

async def avantaj_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    step = AVANTAJ_STEPS[context.user_data['avantaj_step']]

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

    context.user_data['avantaj_data'][step['key']] = value
    context.user_data['avantaj_step'] += 1
    if context.user_data['avantaj_step'] < len(AVANTAJ_STEPS):
        await ask_avantaj_step(update, context)
        return AVANTAJ
    return await send_avantaj(update, context, context.user_data['avantaj_data'])

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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # yarım kalan /avantaj resimlerini bellekten at
    await update.message.reply_text("İşlem iptal edildi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN or TOKEN == "your_token_here":
        print("Error: TELEGRAM_BOT_TOKEN not set in .env file.")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()
    
    # Unified Conversation Handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('katilim', katilim_command),
            CommandHandler('ziyaret', ziyaret_command),
            CommandHandler('debug', debug_command),
            CommandHandler('debug_ziyaret', debug_ziyaret_command),
            CommandHandler('avantaj', avantaj_command),
            CommandHandler('debug_avantaj', debug_avantaj_command),
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
