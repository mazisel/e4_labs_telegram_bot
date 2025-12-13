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

# Initialize Composer
composer = ImageComposer()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Görsel oluşturma botuna hoşgeldiniz.\n\n"
        "Lütfen şehir ismini giriniz (Örn: İzmir):"
    )
    return CITY

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
    context.user_data['debug'] = True
    await update.message.reply_text("Debug modu açıldı. Şimdi bir fotoğraf gönderin, kılavuz çizgileriyle gelecek.")
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
        
    await update.message.reply_text("Yeni bir görsel oluşturmak için /start yazabilirsiniz.")
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
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('debug', debug_command)],
        states={
            CITY: [MessageHandler(filters.TEXT & (~filters.COMMAND), city_entered)],
            MUNICIPALITY: [MessageHandler(filters.TEXT & (~filters.COMMAND), municipality_entered)],
            PHOTO: [MessageHandler(filters.PHOTO, photo_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    
    print("Bot is running...")
    application.run_polling()
