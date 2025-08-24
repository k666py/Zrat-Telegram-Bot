import logging
import sqlite3
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# تنظیمات توکن ربات - اینجا توکن واقعی رو قرار بده
TOKEN = os.environ.get('TOKEN', '8357308067:AAGCVwRNCbDMIlv2NkjAkDvjRdungmXeBqA')
ADMIN_ID = os.environ.get('ADMIN_ID', 'Z666_py')  # آیدی ادمین

# تنظیمات دیتابیس
DB_NAME = "zrat_bot.db"

# حالت های مکالمه
SELECTING_PLAN, CONFIRM_PAYMENT, WAITING_HASH = range(3)

# راه اندازی لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ایجاد اتصال به دیتابیس
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # ایجاد جدول کاربران
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        join_date TEXT,
        active_service TEXT,
        service_end_date TEXT,
        transaction_hash TEXT
    )
    ''')
    
    # ایجاد جدول تراکنش ها
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan_type TEXT,
        amount REAL,
        transaction_hash TEXT,
        status TEXT,
        date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

# افزودن کاربر جدید به دیتابیس
def add_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, join_date, active_service)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, join_date, "None"))
    
    conn.commit()
    conn.close()

# به روز رسانی اطلاعات کاربر
def update_user_service(user_id, service_type, duration_days):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    end_date = (datetime.now() + timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
    UPDATE users 
    SET active_service = ?, service_end_date = ?
    WHERE user_id = ?
    ''', (service_type, end_date, user_id))
    
    conn.commit()
    conn.close()

# افزودن تراکنش
def add_transaction(user_id, plan_type, amount, transaction_hash, status="pending"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
    INSERT INTO transactions (user_id, plan_type, amount, transaction_hash, status, date)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, plan_type, amount, transaction_hash, status, date))
    
    conn.commit()
    conn.close()

# دریافت اطلاعات کاربر
def get_user_info(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    return user

# دریافت تمام کاربران
def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    
    conn.close()
    return users

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name or ""
    
    # افزودن کاربر به دیتابیس
    add_user(user_id, username, first_name, last_name)
    
    # ایجاد دکمه های صفحه اصلی
    keyboard = [
        [KeyboardButton("1.خرید سرویس")],
        [KeyboardButton("2.سرویس های من")],
        [KeyboardButton("3.وضعیت اکانت")]
    ]
    
    # افزودن دکمه مدیریت برای ادمین
    if str(user_id) == ADMIN_ID or username == ADMIN_ID:
        keyboard.append([KeyboardButton("مدیریت ادمین")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # ارسال پیام خوشامدگویی
    welcome_text = """👾 | سلام خوش آمدی. با استفاده از من میتونی هر لحظه و هرجا هر چقد سرویس خواستی بخری و مدیریتشون کنی خیلی راحت .

Ⓜ️ | قابلیت های سرویس شامل لیست زیر میشه :
1️⃣ | پشتیبانی تا اندروید 15
2️⃣ | پایداری تا هروقت که تارگت برنامه رو حذف نکنه
3️⃣ | قابلیت های پیشرفته اعم از اسکرین شات، دریافت اطلاعات بانکی کامل و 10 آپشن مجزا
4️⃣ | هاید تا اندروید 14 غیر سامسونگ | چنج پیشرفته تا اندروید 14 سامسونگ
5️⃣ | تشخیص لیست یوزر های صادرات دار با موجودی هر حساب مثل پینگ آل
6️⃣ | کامپایل لحظه ای و اتومات با آیکون و اسم دلخواه خودتون
7️⃣ | تنظیم دسترسی های دلخواه | فرست اکشن به محض نصب
⚠️ | مسئولیت هر گونه استفاده از ربات بر عهده کاربر میباشد

🕸 امنیت همیشه یک بازی موش و گربه خواهد بود چون کسانی خواهند بود که شکارچی جایزه حفره های زیرو دی هستند، و کسانی مسئول امور هستند که مدیریت پیکربندی ندارند، مدیریت آسیبپذیری ندارند، و مدیریت اصلاح خطرات را ندارند.🧑🏻‍💻🕸"""
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# بازگشت به صفحه اصلی
async def back_to_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    keyboard = [
        [KeyboardButton("1.خرید سرویس")],
        [KeyboardButton("2.سرویس های من")],
        [KeyboardButton("3.وضعیت اکانت")]
    ]
    
    if str(user_id) == ADMIN_ID or query.from_user.username == ADMIN_ID:
        keyboard.append([KeyboardButton("مدیریت ادمین")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await query.message.reply_text("به صفحه اصلی بازگشتید.", reply_markup=reply_markup)
    return ConversationHandler.END

# مدیریت خرید سرویس
async def handle_service_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # نمایش پلن های سرویس
    keyboard = [
        [InlineKeyboardButton("7 روزه - 15 دلار", callback_data="plan_7")],
        [InlineKeyboardButton("15 روزه - 20 دلار", callback_data="plan_15")],
        [InlineKeyboardButton("30 روزه - 30 دلار", callback_data="plan_30")],
        [InlineKeyboardButton("بازگشت", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """🏧 | لطفا پلن خود را انتخاب کنید.
ℹ️ | توضیحات پلن ها به شرح زیر میباشد :

7 روزه = 15 دلار
15 روزه = 20 دلار
30 روزه = 30 دلار"""
    
    await update.message.reply_text(text, reply_markup=reply_markup)
    
    return SELECTING_PLAN

# انتخاب پلن
async def select_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_main":
        return await back_to_main_callback(update, context)
    
    # تعیین نوع پلن و قیمت
    plan_types = {
        "plan_7": {"name": "7 روزه", "price": 15, "days": 7},
        "plan_15": {"name": "15 روزه", "price": 20, "days": 15},
        "plan_30": {"name": "30 روزه", "price": 30, "days": 30}
    }
    
    if data in plan_types:
        plan = plan_types[data]
        context.user_data["selected_plan"] = plan
        
        # نمایش تایید خرید
        keyboard = [
            [InlineKeyboardButton("بله", callback_data="confirm_yes")],
            [InlineKeyboardButton("خیر", callback_data="confirm_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""♻️ | سرویس شما آماده خرید است

Ⓜ️ | نوع : سرویس {plan['name']}
💰 | قیمت : {plan['price']} دلار

⚠️ | در خرید خود دقت کنید، مبلغی بازگشت نخواهد داده شد.
⚠️ | کلیه پورت ها تا یک روز قبل از تمدید فعال هستند، بعد از آن از طریق پنل مربوط به هر پورت میتوانید اقدام به تمدید پورت بکنید.
⚠️ | هر لحظه میتونید پورت رو انتقال بدید به یک گپ دیگه.
⚠️ | امکان تغییر نوع پورت وجود نداره
🔰 | آیا خریداری شود ؟"""
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return CONFIRM_PAYMENT

# تایید پرداخت
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "confirm_no":
        return await back_to_main_callback(update, context)
    
    if data == "confirm_yes":
        plan = context.user_data["selected_plan"]
        
        # نمایش آدرس ولت و گزینه ها
        wallet_address = "TP1LuyCXpkN5KvZvpT7XZWfM6GpKYgR7GR"
        
        keyboard = [
            [InlineKeyboardButton("کپی آدرس", callback_data="copy_address")],
            [InlineKeyboardButton("تایید پرداخت", callback_data="payment_done")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""✅ | برای فعال سازی سرویس {plan['name']} مبلغ {plan['price']} دلار ترون به آدرس زیر واریز کنید:

{wallet_address}"""
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return WAITING_HASH

# کپی آدرس
async def copy_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    wallet_address = "TP1LuyCXpkN5KvZvpT7XZWfM6GpKYgR7GR"
    await query.message.reply_text(wallet_address)

# پرداخت انجام شد
async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("لطفاً لینک هش تراکنش خود را ارسال کنید.")
    return WAITING_HASH

# دریافت هش تراکنش
async def receive_transaction_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    transaction_hash = update.message.text
    
    # ذخیره هش تراکنش در دیتابیس
    plan = context.user_data["selected_plan"]
    add_transaction(user_id, plan["name"], plan["price"], transaction_hash, "pending")
    
    # اطلاع به ادمین
    user = get_user_info(user_id)
    admin_text = f"""کاربر جدیدی تراکنش ارسال کرده:
👤 کاربر: {user[2]} {user[3]} (@{user[1]})
📦 پلن: {plan['name']}
💰 مبلغ: {plan['price']} دلار
🔗 هش تراکنش: {transaction_hash}"""
    
    # بازگشت به صفحه اصلی
    keyboard = [
        [KeyboardButton("1.خرید سرویس")],
        [KeyboardButton("2.سرویس های من")],
        [KeyboardButton("3.وضعیت اکانت")]
    ]
    
    if str(user_id) == ADMIN_ID or update.effective_user.username == ADMIN_ID:
        keyboard.append([KeyboardButton("مدیریت ادمین")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text("✅ پرداخت شما ثبت شد و در انتظار تایید ادمین است. به محض تایید، سرویس شما فعال خواهد شد.", reply_markup=reply_markup)
    
    # ارسال پیام به ادمین
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    except:
        logger.error("Failed to send message to admin")
    
    return ConversationHandler.END

# مدیریت ادمین
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # بررسی آیا کاربر ادمین است
    if str(user.id) != ADMIN_ID and user.username != ADMIN_ID:
        await update.message.reply_text("⛔️ شما دسترسی به این بخش را ندارید.")
        return
    
    # دریافت تمام کاربران
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("هیچ کاربری در سیستم ثبت نشده است.")
        return
    
    # نمایش اطلاعات کاربران
    for user_data in users:
        user_id, username, first_name, last_name, join_date, active_service, service_end_date, transaction_hash = user_data
        
        user_info_text = f"""ℹ️ | اطلاعات کاربر.

👤 | نام: {first_name} {last_name}
🗂 | سرویس های فعال: {active_service if active_service != "None" else "یافت نشد"}
🔗 | هش تراکنش: {transaction_hash or "ارسال نشده"}"""
        
        keyboard = [
            [InlineKeyboardButton("فعال سازی سرویس A (7 روز)", callback_data=f"activate_7_{user_id}")],
            [InlineKeyboardButton("فعال سازی سرویس B (15 روز)", callback_data=f"activate_15_{user_id}")],
            [InlineKeyboardButton("فعال سازی سرویس Z (30 روز)", callback_data=f"activate_30_{user_id}")],
            [InlineKeyboardButton("بازگشت به صفحه اصلی", callback_data="back_to_main_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(user_info_text, reply_markup=reply_markup)

# فعال سازی سرویس توسط ادمین
async def activate_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_main_admin":
        return await back_to_main_callback(update, context)
    
    if data.startswith("activate_"):
        parts = data.split("_")
        plan_days = int(parts[1])
        user_id = int(parts[2])
        
        plan_types = {
            7: {"name": "سرویس A (7 روزه)", "price": 15},
            15: {"name": "سرویس B (15 روزه)", "price": 20},
            30: {"name": "سرویس Z (30 روزه)", "price": 30}
        }
        
        plan = plan_types[plan_days]
        
        # به روز رسانی سرویس کاربر
        update_user_service(user_id, plan["name"], plan_days)
        
        # اطلاع به کاربر
        try:
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"✅ سرویس شما توسط ادمین فعال شد!\n📦 نوع سرویس: {plan['name']}\n⏰ مدت زمان: {plan_days} روز"
            )
        except:
            logger.error(f"Failed to send message to user {user_id}")
        
        await query.edit_message_text(f"سرویس {plan['name']} برای کاربر فعال شد.")

# نمایش سرویس های کاربر
async def show_my_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_user_info(user_id)
    
    if user_info[5] == "None" or not user_info[5]:
        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "متاسفانه شما هنوز سرویس فعالی ندارید برای فعال سازی به بخش خرید سرویس مراجعه کنید.",
            reply_markup=reply_markup
        )
    else:
        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""📊 سرویس های فعال شما:

🗂 نوع سرویس: {user_info[5]}
⏰ پایان سرویس: {user_info[6]}"""
        
        await update.message.reply_text(text, reply_markup=reply_markup)

# نمایش وضعیت اکانت
async def account_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_user_info(user_id)
    
    join_date = user_info[4]
    active_service = user_info[5] if user_info[5] != "None" else "هیچ سرویس فعالی وجود ندارد"
    
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""📊 وضعیت اکانت شما:

👤 نام: {user_info[2]} {user_info[3]}
🗂 سرویس های فعال: {active_service}
⏰ زمان عضویت: {join_date}

💬 پیام از ادمین:
هدف ما فرار از ماتریکس اقتصادی و رسیدن به ثبات مالی در جامعه فاسد است"""
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END

# تابع اصلی
def main():
    # راه اندازی دیتابیس
    init_db()
    
    # ایجاد اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # هندلر مکالمه برای خرید سرویس
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^1.خرید سرویس$"), handle_service_purchase)],
        states={
            SELECTING_PLAN: [CallbackQueryHandler(select_plan)],
            CONFIRM_PAYMENT: [CallbackQueryHandler(confirm_payment)],
            WAITING_HASH: [
                CallbackQueryHandler(payment_done, pattern="^payment_done$"),
                CallbackQueryHandler(copy_address, pattern="^copy_address$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_transaction_hash)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main"),
            CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main_admin")
        ]
    )
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^2.سرویس های من$"), show_my_services))
    application.add_handler(MessageHandler(filters.Regex("^3.وضعیت اکانت$"), account_status))
    application.add_handler(MessageHandler(filters.Regex("^مدیریت ادمین$"), admin_panel))
    application.add_handler(CallbackQueryHandler(activate_service, pattern="^activate_"))
    application.add_handler(CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main"))
    application.add_handler(CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main_admin"))
    
    # شروع ربات
    application.run_polling()
    print("ربات فعال شد...")

if __name__ == "__main__":
    main()

