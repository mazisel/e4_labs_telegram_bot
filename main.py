import os
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler

from dotenv import load_dotenv
from image_composer import ImageComposer

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
        "🔹 /ziyaret - Ziyaret görseli oluştur\n\n"
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
        "🔹 /ziyaret - Ziyaret görseli oluştur"
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
        "🔹 /katilim - Yeni katılım görseli oluştur"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            CommandHandler('start', start),
        ],
        states={
            CITY: [MessageHandler(filters.TEXT & (~filters.COMMAND), city_entered)],
            MUNICIPALITY: [MessageHandler(filters.TEXT & (~filters.COMMAND), municipality_entered)],
            PHOTO: [MessageHandler(filters.PHOTO, photo_received)],
            ZIYARET_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), ziyaret_text_entered)],
            ZIYARET_PHOTO: [MessageHandler(filters.PHOTO, ziyaret_photo_received)],
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
