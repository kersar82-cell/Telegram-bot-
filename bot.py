import logging
import sqlite3
import os 
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==========================================
# ১. সেটিংস ও ডাটাবেস
# ==========================================
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
FILE_ADMIN_ID = 7446548744
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS stats 
                  (user_id INTEGER, file_count INTEGER DEFAULT 0, single_id_count INTEGER DEFAULT 0, date TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests 
                  (req_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, address TEXT)''')
db.commit()
cursor.execute('''CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)''')
db.commit()
                  
cursor.execute('''ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0''')
db.commit()

# এটি ডাটাবেস সেকশনে যোগ করুন
cursor.execute('''CREATE TABLE IF NOT EXISTS user_history 
                  (user_id INTEGER, message_text TEXT, date TEXT)''')
db.commit()
# এই লাইনটি খুঁজে বের করুন এবং referred_by যোগ করুন
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0.0, 
                  referral_count INTEGER DEFAULT 0, referred_by INTEGER)''')
db.commit()

# ডাটাবেজে username কলাম যোগ করা (একবার রান হলেই হবে)
try:
    cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    db.commit()
except:
    pass
    # --- ধাপ ১: ডাটাবেসে পেমেন্ট মেথড কলাম যোগ করা ---
try:
    cursor.execute("ALTER TABLE users ADD COLUMN bkash_num TEXT")
    cursor.execute("ALTER TABLE users ADD COLUMN nagad_num TEXT")
    cursor.execute("ALTER TABLE users ADD COLUMN rocket_num TEXT")
    cursor.execute("ALTER TABLE users ADD COLUMN binance_id TEXT")
    cursor.execute("ALTER TABLE users ADD COLUMN recharge_num TEXT")
    db.commit()
    print("Database columns added successfully!")
except Exception as e:
    # যদি কলামগুলো আগে থেকেই থাকে তবে এই এরর ইগনোর করবে
    print(f"Note: {e}")
    # ডাটাবেসে নতুন কলামগুলো যোগ করার কোড
try:
    # রেফারেল কমিশন জমানোর জন্য আলাদা ব্যালেন্স ঘর
    cursor.execute("ALTER TABLE users ADD COLUMN refer_balance REAL DEFAULT 0")
    # উইথড্র কতবার হয়েছে তা গুনার জন্য ঘর (১০ বার লিমিট চেক করার জন্য)
    cursor.execute("ALTER TABLE users ADD COLUMN withdraw_count INTEGER DEFAULT 0")
    db.commit()
    print("✅ Database updated successfully!")
except Exception as e:
    # যদি কলামগুলো আগে থেকেই থাকে তবে কোনো এরর দিবে না
    print(f"ℹ️ Database notice: {e}")


class BotState(StatesGroup):
    waiting_for_file = State()
    waiting_for_address = State()
    waiting_for_withdraw_amount = State()
    waiting_for_add_money = State()
    waiting_for_add_money = State()
    # নিচে এই ৩টি লাইন লিখে দিন
    waiting_for_single_user = State()
    waiting_for_single_pass = State()
    waiting_for_single_2fa = State()
    waiting_for_block_reason = State() 
    waiting_for_target_id = State()
    waiting_for_admin_msg = State()
    waiting_for_team_name = State()
    waiting_for_referrer_info = State() # এটি নতুন যোগ করুন

    # পেমেন্ট মেথড সেভ করার জন্য নতুন স্টেট
    waiting_for_payment_type = State()  # মোবাইল রিচার্জ নাকি সেন্ড মানি
    waiting_for_recharge_num = State()  # রিচার্জ নম্বর নেওয়ার জন্য
    waiting_for_method_select = State() # বিকাশ/নগদ/রকেট/বাইনান্স সিলেক্ট
    waiting_for_method_num = State()    # ওই মেথডগুলোর নম্বর নেওয়ার জন্য
    
    # উইথড্র করার জন্য স্টেট
    waiting_for_withdraw_type = State() # রিচার্জে নেবে নাকি সেন্ড মানিতে
    waiting_for_transfer_amount = State()
async def is_blocked(user_id):
    cursor.execute("SELECT user_id FROM blacklist WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # আপনার পছন্দমতো জোড়ায় জোড়ায় সাজানো
    keyboard.row("Work start 🔥", "🔥Work Start v2")
    keyboard.row("🧑‍💻Support", "👥 Referral")
    keyboard.row("🔴Rules & Price", "💴Withdraw")
    
    keyboard.row("🏆 Leaderboard", "📊 My Status")
    
    return keyboard
    
    
# /start কমান্ডে মেইন মেনু, রেফারেল ও ওয়েলকাম মেসেজ
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "No_Username"
    args = message.get_args()
    
    # ১. প্রথমে চেক করি ইউজার আগে থেকে ডাটাবেসে আছে কি না
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()

    # ২. যদি ইউজার একদম নতুন হয় (ডাটাবেসে নেই)
    if not existing_user:
        # যদি সে কারো রেফারেল লিংকে ক্লিক করে আসে
        if args and args.isdigit():
            referrer_id = int(args)
            if referrer_id != user_id:
                # রেফারারের কাউন্ট ১ বাড়িয়ে দেওয়া
                cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
                db.commit()
                
                # রেফারারকে অভিনন্দন জানানো
                try:
                    await bot.send_message(referrer_id, "🔔 **অভিনন্দন!**\n\nআপনার রেফারেল লিঙ্ক ব্যবহার করে একজন নতুন ইউজার জয়েন করেছে। 🥳")
                except:
                    pass
        
        # নতুন ইউজারকে ডাটাবেসে সেভ করা
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        db.commit()
    else:
        # যদি ইউজার আগে থেকেই থাকে, শুধু ইউজারনেম আপডেট করা (ঐচ্ছিক)
        cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        db.commit()

    # ৩. ইনলাইন বাটন ও ওয়েলকাম মেসেজ সেটআপ
    inline_kb = types.InlineKeyboardMarkup(row_width=2)
    help_button = types.InlineKeyboardButton(text="🆘 Contact Support", url="https://t.me/instafbhub_support") 
    inline_kb.add(help_button)

    welcome_text = """📢 আজকের কাজের আপডেট এবং রেট লিস্ট 📢
📌 Instagram 2FA: ২.৩০ ৳
📌 Instagram Cookies: ৩.৯০ ৳
📌 Instagram Mother: ৭ ৳
📌 Facebook FBc00Fnd: ৫.৮০ ৳

🏠 Support: @Dinanhaji"""

    # ৪. ইউজারকে মেসেজ পাঠানো
    await message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    await message.answer("✅ আপনার কাজের ধরণ বেছে নিন:", reply_markup=main_menu())
    
# =========================================
@dp.message_handler(lambda message: message.text in ["IG Mother Account", "IG 2fa"])
async def ask_work_type(message: types.Message, state: FSMContext):
    # এই লাইনগুলো বাম দিক থেকে ৪টি স্পেস ডানে থাকবে
    await state.update_data(category=message.text)
    
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(types.InlineKeyboardButton("🗃️ File", callback_data="type_file"))
    inline_kb.add(types.InlineKeyboardButton("👤 Single ID", callback_data="type_single"))
    await message.answer("✅ আপনার কাজের ধরণ বেছে নিন:", reply_markup=inline_kb)
@dp.message_handler(lambda message: message.text == "Work start 🔥")
async def work_start(message: types.Message):
    if await is_blocked(message.from_user.id):
        return await message.answer("❌ দুঃখিত, আপনি ব্লকড! আপনি আর কাজ জমা দিতে পারবেন না। /nএডমিনের সাথে কথা বলুন 👍")
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("IG Mother Account", "IG 2fa")
    keyboard.add("🔄 রিফ্রেশ") 
    
    msg = """Nord VPN 🫱
    🤩Mail: * 3tx0zztil1@xkxkud.com *
    Pass: * RJR83@RdFr2@ *

    🤩Mail: * 377guy1zb4@dollicons.com *
    Pass: * RJR83@RdFr2@ *

    🤩Mail: * icufc65r6j@dollicons.com *
    Pass: * RJR83@RdFr2@ *
    
    👍 যেকোনো সমস্যায়: @Dinanhaji !
    🔴 আপনার কাজের ক্যাটাগরি বেছে নিন:"""
    await message.answer(msg, reply_markup=keyboard)
    

# --- ইনলাইন বাটনের প্রসেসিং (File vs Single ID) ---
@dp.callback_query_handler(lambda c: c.data.startswith('type_'), state="*")
async def process_callback_work_type(callback_query: types.CallbackQuery):
    if callback_query.data == "type_file":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "📤 আপনার এক্সেল ফাইলটি (Excel File) পাঠান।")
        await BotState.waiting_for_file.set()
    elif callback_query.data == "type_single":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "🔙 মেন মেনুতে ফিরে যেতে/start\n👤 আপনার ইউজার আইডি (User ID) দিন:")
        await BotState.waiting_for_single_user.set()

# --- সিঙ্গেল আইডির তথ্য এক এক করে নেওয়ার হ্যান্ডলার ---
@dp.message_handler(state=BotState.waiting_for_single_user)
async def get_id(message: types.Message, state: FSMContext):
    await state.update_data(u_id=message.text)
    await message.answer("🔙 মেইন মেনুতে ফিরে যেতে/start\n🔑 এবার পাসওয়ার্ড (Password) দিন:")
    await BotState.waiting_for_single_pass.set()

@dp.message_handler(state=BotState.waiting_for_single_pass)
async def get_pass(message: types.Message, state: FSMContext):
    await state.update_data(u_pass=message.text)
    await message.answer("🔙 মেইন মেনুতে ফিরে যেতে/start\n🔐 এবার টু-এফা (2FA Code) দিন:")
    await BotState.waiting_for_single_2fa.set()
# ১৪৭ নম্বর লাইনে এটি বসান (যদি না থাকে)

@dp.message_handler(state=BotState.waiting_for_single_2fa)
async def get_2fa(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # ১৪৯ থেকে ১৫৫ নম্বর লাইনের সিঙ্গেল আইডি রিপোর্ট অংশ
    admin_msg = (f"🚀 **নতুন সিঙ্গেল আইডি জমা পড়েছে!**\n"
                 f"👤 **ইউজার:** {message.from_user.full_name}\n"
                 f"🆔 **আইডি:** `{message.from_user.id}`\n"
                 f"🔗 **প্রোফাইল:** [এখানে ক্লিক করুন](tg://user?id={message.from_user.id})\n"
                 f"📂 **ক্যাটাগরি:** {data.get('category')}\n"
                 f"━━━━━━━━━━━━━━━\n"
                 f"🆔 **ID:** `{data.get('u_id')}`\n"
                 f"🔑 **Pass:** `{data.get('u_pass')}`\n"
                 f"🔐 **2FA:** `{message.text}`")

    import datetime
            # ইউজারের মেসেজ ডাটাবেসে সেভ করা হচ্ছে (আগের কোড সব ঠিক রেখে)
    current_time_log = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO user_history (user_id, message_text, date) VALUES (?, ?, ?)", 
                       (message.from_user.id, message.text, current_time_log))
    db.commit()

    today = datetime.date.today().strftime("%Y-%m-%d")
    cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
    cursor.execute("UPDATE stats SET single_id_count = single_id_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))

    category = data.get('category')
    amount_to_add = 0 

    # পুরাতন এবং নতুন সব কাজের রেট এখানে দেওয়া হলো
    if category == "FB 00 Fnd 2fa":
        amount_to_add = 5.80
    elif category == "IG Cookies":
        amount_to_add = 3.90
    elif category == "IG Mother Account":
        amount_to_add = 7
    elif category == "IG 2fa":
        amount_to_add = 2.30

    # শুধুমাত্র সিঙ্গেল আইডি জমা দিলে ব্যালেন্স আপডেট হবে
    if amount_to_add > 0:
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount_to_add, message.from_user.id))
    db.commit()
        
    await bot.send_message(FILE_ADMIN_ID, admin_msg, parse_mode="Markdown")
    await state.finish()
    await message.answer("✅ আপনার তথ্য জমা হয়েছে!\n📌 মেন মেনুতে ফিরে যেতে/start", reply_markup=main_menu())
    
# ৩. রিফ্রেশ বাটনের লজিক (state="*" যোগ করা হয়েছে যাতে যেকোনো অবস্থায় এটি কাজ করে)
@dp.message_handler(lambda message: message.text == "🔄 রিফ্রেশ", state="*")
async def refresh_to_main(message: types.Message, state: FSMContext):
    # ইউজার যদি ফাইল দেওয়ার স্টেটে থাকে তবে তা ক্লিয়ার করবে
    await state.finish() 
    # মেইন মেনুতে ফিরিয়ে নিবে
    await message.answer("✅ আপনি মেইন মেনুতে ফিরে এসেছেন।", reply_markup=main_menu())
    
@dp.message_handler(content_types=['document'], state=BotState.waiting_for_file)
async def handle_file(message: types.Message, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup()
    # Add Money button ebong profile link caption eksathe deya holo
    keyboard.add(types.InlineKeyboardButton("Add Money 💰", callback_data="add_money"))
    
    import datetime
    today = datetime.date.today().strftime("%Y-%m-%d")
    cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
    cursor.execute("UPDATE stats SET file_count = file_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))
    db.commit()

    caption = (f"📩 **নতুন ফাইল জমা পড়েছে!**\n\n"
               f"👤 **নাম:** {message.from_user.full_name}\n"
               f"🆔 **আইডি:** `{message.from_user.id}`\n"
               f"🔗 **প্রোফাইল:** [এখানে ক্লিক করুন](tg://user?id={message.from_user.id})")

    await bot.send_document(FILE_ADMIN_ID, message.document.file_id, 
                           caption=caption, 
                           reply_markup=keyboard, 
                           parse_mode="Markdown")
    
    await message.answer("✅ আপনার ফাইলটি জমা হয়েছে। \n🔥এডমিন চেক করে ব্যালেন্স এড করে দিবে।")
    await state.finish()
# --- ধাপ ২ এর উইথড্র মেইন মেনু ---
@dp.message_handler(lambda message: message.text == "💴Withdraw")
async def withdraw_main_menu(message: types.Message):
    user_id = message.from_user.id
    
    # ইনলাইন কিবোর্ড তৈরি
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("➕ Add Payment Method", callback_data="add_method"),
        types.InlineKeyboardButton("💸 Withdraw", callback_data="start_withdraw"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh_wd")
    )
    
    text = (
        "💳 **উইথড্র ও পেমেন্ট সেটিংস**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "নিচের বাটনগুলো ব্যবহার করে আপনার পেমেন্ট নম্বর সেভ করুন অথবা টাকা উত্তোলনের আবেদন করুন। ✨"
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
       # --- ১. পেমেন্ট মেথড টাইপ সিলেকশন (Recharge vs Send Money) ---
@dp.callback_query_handler(text="add_method")
async def select_method_type(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📱 Mobile Recharge", callback_data="set_recharge"),
        types.InlineKeyboardButton("💸 Send Money", callback_data="set_sendmoney")
    )
    await call.message.edit_text("আপনি কোন মাধ্যমে নম্বর সেভ করতে চান? 👇", reply_markup=kb)
# --- ১. মোবাইল রিচার্জ নম্বর সেভ করা ---
@dp.message_handler(state=BotState.waiting_for_recharge_num)
async def save_recharge_db(message: types.Message, state: FSMContext):
    num = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    
    # ডাটাবেসে সেভ করা
    cursor.execute("UPDATE users SET recharge_num = ? WHERE user_id = ?", (num, user_id))
    db.commit()
    
    # অ্যাডমিনকে জানানো
    admin_text = (
        f"📱 **নতুন রিচার্জ নম্বর সেট!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {message.from_user.full_name}\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"🔗 ইউজারনেম: @{username}\n"
        f"📞 নম্বর: `{num}`"
    )
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    
    await message.answer(f"✅ আপনার **Mobile Recharge** নম্বর `{num}` সফলভাবে সেভ হয়েছে!", reply_markup=main_menu())
    await state.finish()

# --- ২. মোবাইল রিচার্জ নম্বর নেওয়ার জন্য ---
@dp.callback_query_handler(text="set_recharge")
async def ask_recharge_num(call: types.CallbackQuery):
    await BotState.waiting_for_recharge_num.set()
    await call.message.answer("📱 আপনার **Mobile Recharge** নম্বরটি লিখুন:")
    await call.answer()

# --- ৩. সেন্ড মানি মেথড সিলেকশন (৪টি অপশন) ---
@dp.callback_query_handler(text="set_sendmoney")
async def set_sendmoney_options(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("bKash 🟢", callback_data="save_bkash"),
        types.InlineKeyboardButton("Nagad 🟠", callback_data="save_nagad"),
        types.InlineKeyboardButton("Rocket 💜", callback_data="save_rocket"),
        types.InlineKeyboardButton("Binance 🟡", callback_data="save_binance")
    )
    await call.message.edit_text("✨ আপনি কোন মেথডটি এড বা আপডেট করতে চান?", reply_markup=kb)

# --- ৪. সেন্ড মানি নম্বর চাওয়ার লজিক ---
@dp.callback_query_handler(lambda c: c.data.startswith('save_'))
async def ask_for_num(call: types.CallbackQuery, state: FSMContext):
    provider = call.data.split('_')[1]
    await state.update_data(p_type=provider)
    await BotState.waiting_for_method_num.set()
    await call.message.answer(f"🔢 আপনার **{provider.upper()}** নম্বর বা ID টি লিখুন:")
    await call.answer()
    # --- ১. মোবাইল রিচার্জ নম্বর সেভ করা ---
@dp.message_handler(state=BotState.waiting_for_recharge_num)
async def save_recharge_db(message: types.Message, state: FSMContext):
    num = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    
    # ডাটাবেসে সেভ করা
    cursor.execute("UPDATE users SET recharge_num = ? WHERE user_id = ?", (num, user_id))
    db.commit()
    
    # অ্যাডমিনকে জানানো
    admin_text = (
        f"📱 **নতুন রিচার্জ নম্বর সেট!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {message.from_user.full_name}\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"🔗 ইউজারনেম: @{username}\n"
        f"📞 নম্বর: `{num}`"
    )
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    
    await message.answer(f"✅ আপনার **Mobile Recharge** নম্বর `{num}` সফলভাবে সেভ হয়েছে!", reply_markup=main_menu())
    await state.finish()

# --- ২. সেন্ড মানি (বিকাশ/নগদ/রকেট/বাইনান্স) নম্বর সেভ করা ---
@dp.message_handler(state=BotState.waiting_for_method_num)
async def save_sendmoney_db(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_type = data.get('p_type') # bkash, nagad, etc.
    num = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    
    # কোন কলামে সেভ হবে তা নির্ধারণ করা
    column = f"{p_type}_num" if p_type != "binance" else "binance_id"
    
    # ডাটাবেসে সেভ করা
    cursor.execute(f"UPDATE users SET {column} = ? WHERE user_id = ?", (num, user_id))
    db.commit()
    
    # অ্যাডমিনকে জানানো
    admin_text = (
        f"💸 **নতুন পেমেন্ট মেথড সেট!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {message.from_user.full_name}\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"💳 মেথড: {p_type.upper()}\n"
        f"🔢 নম্বর/ID: `{num}`"
    )
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    
    await message.answer(f"✅ আপনার **{p_type.upper()}** তথ্য সফলভাবে সেভ হয়েছে!", reply_markup=main_menu())
    await state.finish()
    # --- ১. উইথড্র বাটন ক্লিক করলে অপশন দেখানো ---
@dp.callback_query_handler(text="start_withdraw", state="*")
async def withdraw_selection(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = call.from_user.id
    
    # ডাটাবেস থেকে ব্যালেন্স আনা
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    balance = res[0] if res else 0

    # এখানে কোনো ব্যালেন্স চেক নেই, সরাসরি দুটি বাটনই দেখাবে
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📱 Mobile Recharge", callback_data="wd_recharge"),
        types.InlineKeyboardButton("💸 Send Money", callback_data="wd_sendmoney")
    )
    
    text = (
        f"💰 **আপনার বর্তমান ব্যালেন্স:** `{balance:.2f} ৳`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "আপনি কোন মাধ্যমে পেমেন্ট নিতে চান? সিলেক্ট করুন: 👇"
    )

    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await call.answer()

# --- সেন্ড মানি ক্লিক করলে ৫০ টাকার নিচের চেক ---
@dp.callback_query_handler(text="wd_sendmoney")
async def check_sendmoney_limit(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]

    # যদি ৫০ টাকার কম হয়
    if balance < 50:
        return await call.answer("⚠️ সেন্ড মানি করতে কমপক্ষে ৫০ টাকা লাগবে। আপনার ব্যালেন্স কম!", show_alert=True)
    
    # ৫০ বা তার বেশি হলে টাকার পরিমাণ চাইবে (আগের ধাপ ৫ এর মতো)
    await state.update_data(withdraw_type="sendmoney")
    await BotState.waiting_for_withdraw_amount.set()
    await call.message.answer("💵 কত টাকা উইথড্র (Send Money) করতে চান? পরিমাণ লিখুন:")
    await call.answer()

# --- মোবাইল রিচার্জ ক্লিক করলে (২০ টাকার চেক রাখতে পারেন) ---
@dp.callback_query_handler(text="wd_recharge")
async def check_recharge_limit(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]

    if balance < 20:
        return await call.answer("⚠️ রিচার্জ নিতে কমপক্ষে ২০ টাকা লাগবে।", show_alert=True)
    
    await state.update_data(withdraw_type="recharge")
    await BotState.waiting_for_withdraw_amount.set()
    await call.message.answer("📱 কত টাকা রিচার্জ নিতে চান? পরিমাণ লিখুন:")
    await call.answer()
    
# --- ২. উইথড্র মেথড সিলেক্ট করার পর টাকার পরিমাণ চাওয়া ---
@dp.callback_query_handler(lambda c: c.data.startswith('wd_'))
async def ask_withdraw_amount(call: types.CallbackQuery, state: FSMContext):
    w_type = call.data.split('_')[1] # recharge / sendmoney
    user_id = call.from_user.id
    
    # ডাটাবেস থেকে তথ্য পুনরায় চেক করা
    cursor.execute(f"SELECT {w_type}_num FROM users WHERE user_id=?" if w_type == 'recharge' else "SELECT bkash_num, nagad_num, rocket_num, binance_id FROM users WHERE user_id=?", (user_id,))
    saved_data = cursor.fetchone()

    # নম্বর সেভ করা না থাকলে উইথড্র করতে দিবে না
    if not any(saved_data) if isinstance(saved_data, tuple) else not saved_data:
        return await call.message.answer("⚠️ আপনার কোনো পেমেন্ট নম্বর সেভ করা নেই! \nআগে 'Add Payment Method' বাটন থেকে নম্বর সেভ করুন।")

    await state.update_data(withdraw_type=w_type)
    await BotState.waiting_for_withdraw_amount.set()
    
    await call.message.answer(
        f"💵 আপনি কত টাকা উইথড্র করতে চান?\n"
        f"পরিমাণটি সংখ্যায় লিখুন (যেমন: ৫০):"
    )
    await call.answer()
    # --- ১. উইথড্র পরিমাণ গ্রহণ এবং অ্যাডমিনকে পাঠানো ---

@dp.message_handler(state=BotState.waiting_for_withdraw_amount)
async def process_withdraw_final(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ অনুগ্রহ করে সঠিক সংখ্যা লিখুন (যেমন: ১০০)")

    amount = int(message.text)
    user_id = message.from_user.id
    
        
    # ডাটাবেস থেকে তথ্য আনা (নতুনভাবে withdraw_count এবং referred_by সহ)
    cursor.execute("SELECT balance, bkash_num, nagad_num, rocket_num, binance_id, recharge_num, withdraw_count, referred_by FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    
    # ডাটাগুলো আলাদা করা
    balance, bkash, nagad, rocket, binance, recharge, wd_count, ref_by = res
    if amount > balance:
        return await message.answer(f"❌ আপনার ব্যালেন্স পর্যাপ্ত নয়! বর্তমান: {balance} ৳")
    
    # স্টেট থেকে জেনে নেওয়া ইউজার কোনটি সিলেক্ট করেছিল (recharge নাকি sendmoney)
    data = await state.get_data()
    w_type = data.get('withdraw_type')

    # ব্যালেন্স কাটা
    new_balance = balance - amount
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    db.commit()
   # --- এখানে বসান (ধাপ ২) ---
    commission = amount * 0.05
    next_wd_number = (wd_count or 0) + 1
    # --- অ্যাডমিন মেসেজ তৈরির লজিক ---
    if w_type == "recharge":
        # শুধু রিচার্জের তথ্য
        method_details = f"📱 **Recharge Number:** `{recharge or 'Not Set'}`"
        withdraw_title = "📱 নতুন রিচার্জ রিকোয়েস্ট!"
    else:
        # সেন্ড মানির সব মেথড (বিকাশ, নগদ ইত্যাদি)
        method_details = (
            f"🟢 bKash: `{bkash or 'Not Set'}`\n"
            f"🟠 Nagad: `{nagad or 'Not Set'}`\n"
            f"💜 Rocket: `{rocket or 'Not Set'}`\n"
            f"🟡 Binance: `{binance or 'Not Set'}`"
        )
        withdraw_title = "💸 নতুন সেন্ড মানি রিকোয়েস্ট!"

        # --- এই লাইনের নিচ থেকে আগের admin_text এবং kb সরিয়ে ফেলুন ---
    
    admin_text = (
        f"{withdraw_title}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {message.from_user.full_name}\n"
        f"🆔 আইডি: `{user_id}`\n\n"
        f"💵 উইথড্র পরিমাণ: **{amount} ৳**\n"
        f"🎁 **রেফার কমিশন (৫%):** `{commission:.2f} ৳`\n"
        f"📊 উইথড্র সংখ্যা: `{next_wd_number}/10` (লিমিট)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏠 **পেমেন্ট ডিটেইলস:**\n"
        f"{method_details}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"পেমেন্ট করে নিচের বাটনে ক্লিক করুন 👇"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(
        # এখানে callback_data তে commission যোগ করা হয়েছে যাতে এপ্রুভ করলে বট টাকা পাঠাতে পারে
        types.InlineKeyboardButton("✅ Approve", callback_data=f"admin_payment_approve_{user_id}_{amount}_{commission}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_payment_reject_{user_id}_{amount}")
    )

    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="Markdown")
    
    # --- এরপর আগের মতোই থাকবে ---
    await message.answer(
        f"✅ **আপনার উইথড্র রিকোয়েস্ট জমা হয়েছে!**\n...",
        reply_markup=main_menu()
    )
    
    await state.finish()
    
# ৪. এডমিন প্যানেল
# ==========================================
@dp.message_handler(commands=['check'])
async def admin_check(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        uid = message.get_args()
        cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (uid,))
        res = cursor.fetchone()
        if res: await message.answer(f"👤 ইউজার: `{uid}`\n💰 ব্যালেন্স: {res[0]} ৳\n📍 এড্রেস: {res[1]}")
        else: await message.answer("❌ ইউজার পাওয়া যায়নি।")

@dp.message_handler(commands=['edit'])
async def admin_edit(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            args = message.get_args().split()
            cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (args[1], args[0]))
            db.commit()
            await message.answer(f"✅ ইউজার {args[0]} এর ব্যালেন্স এডিট করা হয়েছে।")
        except: await message.answer("ফরম্যাট: /edit আইডি টাকা")

@dp.message_handler(commands=['broadcast'])
async def admin_broadcast(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        text = message.get_args()
        cursor.execute("SELECT user_id FROM users")
        all_users = cursor.fetchall()
        for user in all_users:
            try: await bot.send_message(user[0], text)
            except: pass
        await message.answer("✅ সবার কাছে মেসেজ পাঠানো হয়েছে।")

@dp.callback_query_handler(lambda c: c.data.startswith('adminadd_'))
async def add_money_btn(call: types.CallbackQuery, state: FSMContext):
    target_id = call.data.split('_')[1]
    await state.update_data(target_id=target_id)
    await call.message.answer(f"ইউজার `{target_id}` কে কত টাকা পাঠাতে চান?")
    await BotState.waiting_for_add_money.set()

@dp.message_handler(state=BotState.waiting_for_add_money)
async def final_add_money(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        try:
            data = await state.get_data()
            amount = float(message.text)
            uid = data['target_id']
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
            db.commit()
            await bot.send_message(uid, f"✅আপনার একাউন্টে {amount} ৳ যোগ করেছে।")
            await message.answer(f"✅ {amount} ৳ সফলভাবে যোগ করা হয়েছে।")
        except: await message.answer("❌ ভুল ইনপুট।")
        await state.finish()
  # ৫. রান করা
# ==========================================
# --- অ্যাডমিন প্যানেল: ইউজার সার্চ ও বিস্তারিত রিপোর্ট ---
@dp.message_handler(commands=['search'], user_id=ADMIN_ID)
async def admin_search(message: types.Message):
    args = message.get_args()
    if not args: return await message.answer("⚠️ আইডি দিন। যেমন: `/search 12345678`")
    
    try:
        target_id = int(args)
        cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (target_id,))
        user = cursor.fetchone()
        
        if user:
            import datetime
            today = datetime.date.today().strftime("%Y-%m-%d")
            # আজকের কাজের হিসাব
            cursor.execute("SELECT file_count, single_id_count FROM stats WHERE user_id=? AND date=?", (target_id, today))
            s = cursor.fetchone() or (0, 0)
            
            text = (f"👤 **ইউজার রিপোর্ট (ID: `{target_id}`)**\n\n"
                    f"💵 ব্যালেন্স: {user[0]} টাকা\n"
                    f"💳 পেমেন্ট মেথড: `{user[1] or 'নেই'}`\n"
                    f"📊 আজ জমা দিয়েছে:\n"
                    f"📁 ফাইল: {s[0]} টি\n"
                    f"👤 সিঙ্গেল আইডি: {s[1]} টি")
            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("❌ ডাটাবেসে এই ইউজার পাওয়া যায়নি।")
    except ValueError:
        await message.answer("❌ আইডি শুধুমাত্র সংখ্যা হতে হবে।")
        # ১. কমান্ড দিয়ে ব্লক করা: /block 12345678
@dp.message_handler(commands=['block'], user_id=ADMIN_ID)
async def admin_block(message: types.Message, state: FSMContext):
    try:
        # কমান্ড থেকে ইউজার আইডি নেওয়া
        uid = int(message.get_args())
        
        # ডাটাবেসে ব্লক হিসেবে সেভ করা
        cursor.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (uid,))
        db.commit()
        
        # কারণ পাঠানোর জন্য আইডিটি সাময়িকভাবে সেভ রাখা
        await state.update_data(blocking_user_id=uid)
        
        await message.answer(f"🚫 ইউজার `{uid}` ব্লক করা হয়েছে।\nএখন ব্লক করার কারণটি লিখে পাঠান:")
        
        # কারণ নেওয়ার জন্য স্টেট সেট করা
        await BotState.waiting_for_block_reason.set()
        
    except:
        await message.answer("⚠️ সঠিক ফরম্যাট: `/block ইউজার_আইডি` লিখুন।")

# ২. কমান্ড দিয়ে আনব্লক করা: /unblock 12345678
@dp.message_handler(commands=['unblock'], user_id=ADMIN_ID)
async def admin_unblock(message: types.Message):
    try:
        uid = int(message.get_args())
        cursor.execute("DELETE FROM blacklist WHERE user_id=?", (uid,))
        db.commit()
        await message.answer(f"✅ ইউজার `{uid}` এখন আনব্লক।")
        await bot.send_message(uid, "✅ আপনাকে আনব্লক করা হয়েছে।\nআর ভুল করবেন না❌")
        
    except: await message.answer("সঠিক ফরম্যাট: `/unblock আইডি`")
@dp.callback_query_handler(lambda c: c.data.startswith('block_'), user_id=ADMIN_ID)
async def block_callback(call: types.CallbackQuery, state: FSMContext):
    uid = int(call.data.split('_')[1])
    # ডাটাবেসে ব্লক করা
    cursor.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (uid,))
    db.commit()
    
    # ইউজার আইডি সেভ রাখা
    await state.update_data(blocking_user_id=uid)
    
    await call.message.answer(f"🚫 ইউজার `{uid}` ব্লকড।\nএখন ব্লক করার কারণটি লিখে পাঠান:")
    await BotState.waiting_for_block_reason.set()
    await call.answer()
    
@dp.message_handler(state=BotState.waiting_for_block_reason, user_id=ADMIN_ID)
async def send_block_reason(message: types.Message, state: FSMContext):
    # সেভ করা আইডিটি ফিরিয়ে আনা
    data = await state.get_data()
    uid = data.get('blocking_user_id')
    reason = message.text # আপনি যা লিখে পাঠাবেন
    
    try:
        # ইউজারের কাছে কারণসহ মেসেজ পাঠানো
        msg_text = f"❌ আপনাকে বট থেকে ব্লক করা হয়েছে।\n📝 কারণ: {reason}"
        await bot.send_message(uid, msg_text)
        await message.answer(f"✅ ইউজার `{uid}` কে কারণসহ ব্লক মেসেজ পাঠানো হয়েছে।")
        await state.finish()
    except:
        await message.answer(f"⚠️ ইউজার `{uid}` কে মেসেজ পাঠানো যায়নি।")

@dp.message_handler(commands=['edit_ref'], user_id=ADMIN_ID)
async def admin_edit_referral(message: types.Message):
    try:
        args = message.get_args().split()
        if len(args) < 2:
            return await message.answer("⚠️ ফরম্যাট: `/edit_ref আইডি সংখ্যা`")
        
        target_id, new_count = int(args[0]), int(args[1])
        cursor.execute("UPDATE users SET referral_count = ? WHERE user_id = ?", (new_count, target_id))
        db.commit()
        
        await message.answer(f"✅ ইউজার `{target_id}` এর রেফারেল সংখ্যা আপডেট করে `{new_count}` করা হয়েছে।")
        try:
            await bot.send_message(target_id, f"📢 আপনার মোট রেফারেল সংখ্যা আপডেট করা হয়েছে।\nবর্তমান রেফারেল: {new_count} জন।")
        except: pass
    except:
        await message.answer("❌ ভুল আইডি বা সংখ্যা।")
    # 'Support' বাটনে ক্লিক করলে যা শো করবে (হাইপারলিঙ্ক সহ)
@dp.message_handler(lambda message: message.text == "🧑‍💻Support")
async def support_message(message: types.Message):
    # এখানে [শব্দ](লিঙ্ক) এই ফরম্যাটে হাইপারলিঙ্ক সেট করা হয়েছে
    text = (
        "👋 **হ্যালো! আমাদের সাপোর্ট সেন্টারে আপনাকে স্বাগতম।**\n\n"
        "যেকোনো সমস্যা বা তথ্যের জন্য নিচে ক্লিক করুন:\n\n"
        "🎥 **Bot Setup:** [VIDEO](ht)\n"
        "📢 **আপডেট গ্রুপ:** [Join Channel](https://t.me/instafbhub)\n"
        "🛠 **হেল্প সাপোর্ট:** [Contact Support](https://t.me/INSTAFB_SUPPORT)\n\n"
        "✅আমরা আপনাকে দ্রুত সাহায্য করার চেষ্টা করব। ধন্যবাদ!"
    )
    
    # parse_mode="Markdown" অবশ্যই থাকতে হবে নাহলে লিঙ্ক কাজ করবে না
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

# ১. মেনু বাটন ফাংশন (নিশ্চিত করুন নামটি সঠিক)
def work_v2_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("FB 00 Fnd 2fa", "IG Cookies") 
    keyboard.add("🔄 রিফ্রেশ") 
    return keyboard

# ২. মেইন বাটন হ্যান্ডলার (v2 ওপেন করার জন্য)
@dp.message_handler(lambda message: "Work Start v2" in message.text or message.text == "🔥Work Start v2")
async def work_v2_handler(message: types.Message):
    user_id = message.from_user.id 
    if await is_blocked(user_id):
        return await message.answer("❌ দুঃখিত, আপনাকে ব্লক করা হয়েছে। \n\n✅আপনি 24 hrs পরে বটটি ব্যবহার করতে পারবেন না।")
        
    text = (
        "🔴 **আপনার কাজের ক্যাটাগরি বেছে নিন:**\n"
        "👍 যেকোনো সমস্যায়: @Dinanhaji !"
    )
    await message.answer(text, reply_markup=work_v2_menu(), parse_mode="Markdown")

# ৩. ক্যাটাগরি সিলেক্ট করার হ্যান্ডলার
# ৩. ক্যাটাগরি সিলেক্ট করার হ্যান্ডলার
@dp.message_handler(lambda message: message.text in ["FB 00 Fnd 2fa", "IG Cookies"])
async def work_v2_options(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    
    # ইনলাইন কিবোর্ড তৈরি (row_width সেট করা হয়েছে যাতে বাটনগুলো সাজানো থাকে)
    inline_kb = types.InlineKeyboardMarkup(row_width=2)
        # সাধারণ ফাইল এবং সিঙ্গেল আইডি বাটন
    btn_file = types.InlineKeyboardButton("📁 File", callback_data="type_file")
    btn_single = types.InlineKeyboardButton("🆔 Single ID", callback_data="type_single")
    
    # শর্ত: শুধুমাত্র IG Cookies হলে নতুন বাটনটি যোগ হবে
    if message.text == "IG Cookies":
        # এখানে 'your_link' এর জায়গায় আপনার আসল টেলিগ্রাম লিংক দিন
        btn_submit_link = types.InlineKeyboardButton("🔗 Submit Link", url="https://t.me/instafbhub/80")
        inline_kb.add(btn_file, btn_single) # প্রথম সারিতে দুই বাটন
        inline_kb.add(btn_submit_link)      # তার নিচে বড় সাবমিট বাটন
    else:
        inline_kb.add(btn_file, btn_single) # অন্য ক্যাটাগরিতে শুধু এই দুটি থাকবে
    
    msg_text = (
        f"✅ আপনি বেছে নিয়েছেন: **{message.text}**\n"
        "━━━━━━━━━━━━━━━\n"
        "এখন কিভাবে ডাটা জমা দিতে চান? নিচের বাটন থেকে সিলেক্ট করুন।"
    )
    
    await message.answer(msg_text, reply_markup=inline_kb, parse_mode="Markdown")
                      
#মেসেজ
@dp.message_handler(commands=['msg'], user_id=ADMIN_ID)
async def admin_direct_msg(message: types.Message):
    try:
        # কমান্ড থেকে আইডি এবং মেসেজ আলাদা করা
        args = message.get_args().split(maxsplit=1)
        if len(args) < 2:
            return await message.answer("⚠️ সঠিক ফরম্যাট: `/msg আইডি মেসেজ`")
        
        target_id = int(args[0])
        text_to_send = args[1]
        
        # ইউজারের কাছে মেসেজ পাঠানো
        await bot.send_message(target_id, f"📩 **অ্যাডমিনের কাছ থেকে মেসেজ:**\n\n{text_to_send}")
        await message.answer(f"✅ ইউজার `{target_id}` কে মেসেজ পাঠানো হয়েছে।")
        
    except Exception as e:
        await message.answer(f"❌ মেসেজ পাঠানো যায়নি। ভুল আইডি বা ইউজার বটটি ব্লক করে রেখেছে।")


# --- ১. কিবোর্ড ফাংশন (এটি লাইনের শুরুতে থাকবে) ---
def rules_price_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("IG 2fa Rules", "IG Cookies Rules")
    keyboard.add("Ig mother account Rules", "Fb 00 fnd 2fa Rules")
    keyboard.add("🔄 রিফ্রেশ") 
    return keyboard

# --- ২. মেইন বাটন হ্যান্ডলার ---
@dp.message_handler(lambda message: message.text == "🔴Rules & Price")
async def rules_price_handler(message: types.Message):
    await message.answer(
        "👉 যে ক্যাটাগরির নিয়ম এবং রেট জানতে চান,\n\n👇 নিচের বাটন থেকে সেটি সিলেক্ট করুন:",
        reply_markup=rules_price_menu()
    )

# --- ৩. রুলস মেসেজ হ্যান্ডলার ---
@dp.message_handler(lambda message: message.text in ["IG 2fa Rules", "IG Cookies Rules", "Ig mother account Rules", "Fb 00 fnd 2fa Rules"])
async def show_only_rules(message: types.Message):
    category = message.text
    msg = ""
    
    if category == "IG 2fa Rules":
        msg = (
            "📌 **পয়েন্ট ১: 📸 Instagram 00 Follower (2FA)**\n\n"
            "💸 প্রাইস: ২.৩০ টাকা (১০০+ হলে ২.৫০ টাকা)\n\n"
            "⚠️ নিয়ম: 🚫 Resell ID Not Allowed.\n\n"
            "📄 শীট ফরম্যাট: User-pass-2fa\n\n"             
            "⏰ আইডি সাবমিট লাস্ট টাইম: রাত ০৮:১৫ মিনিট।\n\n"
            "⏳ **রিপোর্ট টাইম: ১২ ঘণ্টা।**"
        )
    elif category == "IG Cookies Rules":
        msg = (
            "📌 **পয়েন্ট ২: 📸 Instagram Cookies 00 Follower**\n\n"
            "💸 প্রাইস: ৩.৯০ টাকা (৪.১০ টাকা)\n\n"
            "⚠️ নিয়ম: ⚡ আইডি করার সাথে সাথে সাবমিট দিতে হবে।\n\n"
            "📄 শীট ফরম্যাট: **User-pass**\n\n"
            "⏰ ফাইল সাবমিট লাস্ট টাইম: সকাল ১০:৩০ মিনিট।\n\n"
            "⏳ **রিপোর্ট টাইম: ৪ ঘণ্টা।**"
        )
    elif category == "Ig mother account Rules":
        msg = (
            "📌 **পয়েন্ট ৩: 📸 Instagram Mother Account (2FA)**\n\n"
            "💸 প্রাইস: ৮ টাকা (৫০+ হলে ৯ টাকা)\n\n"
            "📄 শীট ফরম্যাট: User-pass-2fa\n\n"
            "⚠️ নিয়ম: ❗ একটি নাম্বার দিয়ে একটি আইডিই খুলতে হবে।\n\n"
            "⏰ লাস্ট টাইম: যেকোনো সময় (Anytime)。\n\n"
            "⏳ **রিপোর্ট টাইম: ১ ঘণ্টা।**"
        )
    elif category == "Fb 00 fnd 2fa Rules":
        msg = (
            "📌 **পয়েন্ট ৪: 🔵 Facebook (FB00Fnd 2fa)**\n\n"
            "💸 প্রাইস: ৫.৮০ টাকা (৫০+ হলে ৬ টাকা)\n\n"
            "📄 শীট ফরম্যাট: User-pass-2fa\n\n"
            "⚠️ নিয়ম: ❌ পাসওয়ার্ডের শেষে তারিখ দেওয়া যাবে না।\n\n"
            "⏰ আইডি সাবমিট লাস্ট টাইম: রাত ১০:০০ মিনিট।\n\n"
            "⏳ **রিপোর্ট টাইম: ৫ ঘণ্টা।**"
        )
    
    if msg:
        await message.answer(msg, parse_mode="Markdown")
@dp.message_handler(lambda message: message.text == "📊 My Status")
async def show_user_status(message: types.Message):
    user_id = message.from_user.id
    
    # ডাটাবেস থেকে ইউজারের ব্যালেন্স এবং অন্যান্য তথ্য আনা
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    balance = user_data[0] if user_data else 0

    # স্ট্যাটাস টেবিল থেকে ফাইল এবং সিঙ্গেল আইডির সংখ্যা আনা
    cursor.execute("SELECT file_count, single_id_count FROM stats WHERE user_id = ?", (user_id,))
    stats_data = cursor.fetchone()
    
    file_count = stats_data[0] if stats_data else 0
    single_id_count = stats_data[1] if stats_data else 0

    # সুন্দর করে সাজানো মেসেজ
    status_msg = (
        f"👤 **আপনার প্রোফাইল স্ট্যাটাস**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ইউজার আইডি:** `{user_id}`\n"
        f"💰 **মোট ব্যালেন্স:** {balance} BDT\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📁 **মোট ফাইল পাঠিয়েছেন:** {file_count} টি\n"
        f"🆔 **সিঙ্গেল আইডি পাঠিয়েছেন:** {single_id_count} টি\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"সঠিকভাবে কাজ করুন এবং বেশি আয় করুন! 🔥"
    )
    
    await message.answer(status_msg, parse_mode="Markdown")
    # এডমিন প্যানেল থেকে ইউজারের মেসেজ দেখার কমান্ড
@dp.message_handler(commands=['userlogs'], user_id=ADMIN_ID)
async def get_user_history(message: types.Message):
    args = message.get_args().split()
    if not args:
        return await message.answer("⚠️ সঠিক নিয়ম: `/userlogs USER_ID` \nউদাহরণ: `/userlogs 12345678`")
    
    target_id = args[0]
    
    # শেষ ২০টি মেসেজ সিরিয়ালি আনা হচ্ছে
    cursor.execute("SELECT message_text, date FROM user_history WHERE user_id = ? ORDER BY date DESC LIMIT 20", (target_id,))
    rows = cursor.fetchall()

    if rows:
        history_text = f"📜 **ইউজার আইডি `{target_id}` এর শেষ ২০টি মেসেজ:**\n"
        history_text += "━━━━━━━━━━━━━━━━━━\n"
        
        for i, row in enumerate(rows, 1):
            history_text += f"{i}. 🕒 {row[1]}\n📝 {row[0]}\n\n"
        
        history_text += "━━━━━━━━━━━━━━━━━━"
        await message.answer(history_text)
    else:
        await message.answer(f"❌ আইডি `{target_id}` এর কোনো মেসেজ রেকর্ড পাওয়া যায়নি।")
# অ্যাডমিন এই কমান্ড দিলে সব ইউজারের ইউজারনেম ও আইডি দেখতে পাবেন
@dp.message_handler(commands=['allusers'], user_id=ADMIN_ID)
async def get_all_users(message: types.Message):
    cursor.execute("SELECT user_id, username FROM users")
    users = cursor.fetchall()
    
    if not users:
        return await message.answer("❌ ডাটাবেসে কোনো ইউজার পাওয়া যায়নি।")
    
    # ইনচার্জ বা অ্যাডমিনের জন্য মেসেজ হেডার
    response_text = "👥 **বটের সকল ইউজার লিস্ট:**\n━━━━━━━━━━━━━━━\n"
    
    count = 0
    for index, user in enumerate(users, 1):
        uid, uname = user[0], user[1]
        # ইউজারনেম না থাকলে 'No Username' দেখাবে
        display_name = uname if uname else "No Username"
        response_text += f"{index}. 🆔 `{uid}` | 👤 {display_name}\n"
        count += 1
        
        # টেলিগ্রাম মেসেজের লিমিট এড়াতে প্রতি ৫০ জন পর পর নতুন মেসেজ পাঠানো
        if index % 50 == 0:
            await message.answer(response_text, parse_mode="Markdown")
            response_text = ""

    if response_text:
        response_text += f"━━━━━━━━━━━━━━━\n✅ মোট ইউজার: {count} জন"
        await message.answer(response_text, parse_mode="Markdown")

import datetime

@dp.message_handler(commands=['todaystats'], user_id=ADMIN_ID)
async def get_today_stats(message: types.Message):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # ১. ডাটাবেস থেকে সব ইউজার এবং তাদের আজকের কাজের তথ্য আনা
    cursor.execute("""
        SELECT users.user_id, users.username, stats.file_count, stats.single_id_count 
        FROM users 
        LEFT JOIN stats ON users.user_id = stats.user_id AND stats.date = ?
    """, (today,))
    
    all_users = cursor.fetchall()

    if not all_users:
        return await message.answer("❌ ডাটাবেসে কোনো ইউজার পাওয়া যায়নি।")

    worked_list = []      # যারা কাজ করেছে
    not_worked_list = []  # যারা কাজ করেনি

    for user in all_users:
        uid, uname, f_count, s_count = user
        f_count = f_count if f_count else 0
        s_count = s_count if s_count else 0
        username = uname if uname else "No Username"

        if f_count > 0 or s_count > 0:
            worked_list.append(f"✅ 🆔 `{uid}` | {username}\n   └📁 ফাইল: {f_count} | 🆔 সিঙ্গেল: {s_count}")
        else:
            not_worked_list.append(f"❌ 🆔 `{uid}` | {username}")

    # ২. মেসেজ সাজানো
    response_text = f"📊 **আজকের রিপোর্ট ({today})**\n\n"
    
    response_text += "🔥 **যারা কাজ জমা দিয়েছে:**\n━━━━━━━━━━━━━━━\n"
    if worked_list:
        response_text += "\n\n".join(worked_list)
    else:
        response_text += "আজ এখন পর্যন্ত কেউ কাজ করেনি।"

    response_text += "\n\n😴 **যারা এখনো কাজ দেয়নি:**\n━━━━━━━━━━━━━━━\n"
    if not_worked_list:
        response_text += "\n".join(not_worked_list)
    else:
        response_text += "সবাই আজকে কাজ করেছে!"

    # ৩. মেসেজ পাঠানো (অনেক বড় হলে ভাগ করে পাঠানো)
    if len(response_text) > 4000:
        # মেসেজ খুব বড় হলে পার্ট পার্ট করে পাঠানো
        for i in range(0, len(response_text), 4000):
            await message.answer(response_text[i:i+4000], parse_mode="Markdown")
    else:
        await message.answer(response_text, parse_mode="Markdown")
# --- এটি ফাইলের একদম শেষে বসান ---
  # ==========================================
# ৪. উইথড্র এপ্রুভ/রিজেক্ট বাটন প্রসেস
# ==========================================
@dp.callback_query_handler(lambda c: c.data.startswith('wd_'), user_id=ADMIN_ID)
async def process_withdraw_callback(call: types.CallbackQuery):
    action = call.data.split('_')[1] # approve/reject
    req_id = call.data.split('_')[2]

    cursor.execute("SELECT user_id, amount, status FROM withdraw_requests WHERE req_id=?", (req_id,))
    request = cursor.fetchone()

    if not request or request[2] != 'pending':
        return await call.answer("⚠️ এই রিকোয়েস্টটি আগেই প্রসেস করা হয়েছে।", show_alert=True)

    uid, amount, _ = request

    if action == "approve":
        cursor.execute("UPDATE withdraw_requests SET status='approved' WHERE req_id=?", (req_id,))
        db.commit()
        try:
            await bot.send_message(uid, f"✅ **আপনার উইথড্র এপ্রুভ হয়েছে!**\n💰 পরিমাণ: {amount} ৳\nঅল্প সময়ের মধ্যে পেমেন্ট পেয়ে যাবেন।")
        except: pass
        await call.message.edit_text(call.message.text + "\n\n✅ **Status: Approved**")
        await call.answer("সফলভাবে এপ্রুভ করা হয়েছে।")

    elif action == "reject":
        # রিজেক্ট করলে টাকা ইউজারের একাউন্টে ফেরত দেওয়া
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
        cursor.execute("UPDATE withdraw_requests SET status='rejected' WHERE req_id=?", (req_id,))
        db.commit()
        try:
            await bot.send_message(uid, f"❌ **আপনার উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে।**\n💰 {amount} ৳ আপনার ব্যালেন্সে ফেরত দেওয়া হয়েছে।")
        except: pass
        await call.message.edit_text(call.message.text + "\n\n❌ **Status: Rejected**")
        await call.answer("রিকোয়েস্ট রিজেক্ট করা হয়েছে।")
import random

# ১. ফেক মেম্বার অ্যাড করার কমান্ড (অ্যাডমিনের জন্য)
@dp.message_handler(commands=['add_fake'], user_id=ADMIN_ID)
async def add_fake_leaderboard(message: types.Message):
    args = message.get_args().split()
    if len(args) < 2:
        return await message.answer("⚠️ নিয়ম: `/add_fake NAME BALANCE` \nউদাহরণ: `/add_fake Worker1 5000`")

    fake_name = args[0].replace("_", " ")
    try:
        balance = float(args[1])
    except:
        return await message.answer("❌ ব্যালেন্স অবশ্যই নম্বর হতে হবে।")

    # ফেক ইউআইডি জেনারেট (৬ ডিজিট)
    fake_uid = random.randint(1000000000, 9999999999) 

    # ডাটাবেসে সেভ (username কলামে নাম থাকলেও আমরা লিডারবোর্ডে UID দেখাবো)
    cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (fake_uid, fake_name, balance))
    db.commit()

    await message.answer(f"✅ ফেক ইউজার যুক্ত হয়েছে!\n🆔 UID: `{fake_uid}`\n💰 ব্যালেন্স: {balance} ৳")

@dp.message_handler(lambda message: message.text == "🏆 Leaderboard")
async def show_leaderboard(message: types.Message):
    user_id = message.from_user.id
    # ১০৩ লাইনের নিচে এটি বসান
    if await is_blocked(user_id):
        return await message.answer("❌ দুঃখিত, আপনাকে ব্লক করা হয়েছে। \n\n✅আপনি 24 hrs পরে বটটি ব্যবহার করতে পারবেন না।")
        
    # এটি ডাটাবেসের সবার মধ্যে তুলনা করে টপ ৫ জনের UID এবং Balance আনবে
    # এখানে রিয়েল এবং ফেক সবাই একসাথে প্রতিযোগিতা করবে
    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")
    top_rows = cursor.fetchall()

    if not top_rows:
        return await message.answer("🏆 লিডারবোর্ড এখনো খালি!")

    # ইউজারের নিজের পজিশন কত নম্বরে সেটা বের করা
    cursor.execute("""
        SELECT COUNT(*) + 1 FROM users 
        WHERE balance > (SELECT balance FROM users WHERE user_id = ?)
    """, (user_id,))
    user_rank = cursor.fetchone()[0]

    # মেসেজ তৈরি
    text = "🏆 **সর্বোচ্চ ব্যালেন্সধারী ৫ জন কর্মী** 🏆\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, row in enumerate(top_rows):
        uid, balance = row
        # এখানে আসল বা ফেক যার ব্যালেন্স বেশি হবে, তার UID-ই উপরে দেখাবে
        text += f"{emojis[i]} **UID:** `{uid}`\n└─ 💰 ব্যালেন্স: {balance} ৳\n\n"

    text += "━━━━━━━━━━━━━━━━━━━\n🔥 বেশি কাজ করে লিডারবোর্ডের শীর্ষে আসুন!"
    
    await message.answer(text, parse_mode="Markdown")

# ৩. ফেক বা রিয়েল ইউজারের ব্যালেন্স এডিট করার কমান্ড (অ্যাডমিনের জন্য)
@dp.message_handler(commands=['edit_fake'], user_id=ADMIN_ID)
async def edit_fake_balance(message: types.Message):
    args = message.get_args().split()
    if len(args) != 2:
        return await message.answer("⚠️ নিয়ম: `/edit_fake USER_ID NEW_BALANCE`")

    target_uid = args[0]
    try:
        new_balance = float(args[1])
    except:
        return await message.answer("❌ ব্যালেন্স নম্বর হতে হবে।")

    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, target_uid))
    db.commit()
    
    await message.answer(f"✅ সাকসেস!\n🆔 আইডি: `{target_uid}`\n💰 ব্যালেন্স সেট: `{new_balance}` ৳")
@dp.message_handler(commands=['del_fake'], user_id=ADMIN_ID)
async def delete_fake_user(message: types.Message):
    # নিয়ম: /del_fake [ইউজার_আইডি]
    args = message.get_args().split()
    
    if len(args) != 1:
        return await message.answer("⚠️ সঠিক নিয়ম: `/del_fake USER_ID` \n\n"
                                   "উদাহরণ: `/del_fake 123456` \n"
                                   "(লিডারবোর্ড থেকে আইডি কপি করে এখানে বসান)")

    target_uid = args[0]

    # ডাটাবেস থেকে ওই আইডিটি মুছে ফেলা
    cursor.execute("DELETE FROM users WHERE user_id = ?", (target_uid,))
    # চাইলে তার স্ট্যাটাস টেবিল থেকেও ডাটা মুছে দিতে পারেন (অপশনাল)
    cursor.execute("DELETE FROM stats WHERE user_id = ?", (target_uid,))
    
    db.commit()
    
    await message.answer(f"🗑️ সফলভাবে ডিলিট করা হয়েছে!\n🆔 আইডি: `{target_uid}` এখন আর লিডারবোর্ডে দেখাবে না।")
    # ==========================================
# ব্লক করা ইউজারদের তালিকা দেখার কমান্ড
# ==========================================
@dp.message_handler(commands=['check_blocks'], user_id=ADMIN_ID)
async def list_blocked_users(message: types.Message):
    # ডাটাবেস থেকে ব্লকড ইউজারদের তথ্য আনা
    cursor.execute("SELECT user_id FROM blacklist")
    blocked_list = cursor.fetchall()

    if not blocked_list:
        return await message.answer("✅ বর্তমানে কোনো ইউজার ব্লক নেই।")

    response = "🚫 **ব্লক করা ইউজারদের তালিকা:**\n\n"
    for index, row in enumerate(blocked_list, start=1):
        uid = row[0]
        # ইউজারনেম খুঁজে বের করার চেষ্টা করা (যদি থাকে)
        cursor.execute("SELECT username FROM users WHERE user_id = ?", (uid,))
        user_info = cursor.fetchone()
        
        username = f"@{user_info[0]}" if user_info and user_info[0] else "নাম পাওয়া যায়নি"
        response += f"{index}. ID: `{uid}` | User: {username}\n"

    await message.answer(response, parse_mode="Markdown")


        # --- শুধুমাত্র অ্যাডমিনের পেমেন্ট কন্ট্রোল ---
@dp.callback_query_handler(lambda c: c.data.startswith('admin_payment_'), user_id=ADMIN_ID)
async def finalize_admin_action(call: types.CallbackQuery):
    data = call.data.split('_')
    # data[2] = action (approve/reject), data[3] = user_id, data[4] = amount
    action = data[2]
    target_uid = int(data[3])
    amount = int(data[4])

    if action == "approve":
        # ১. ইউজারকে মেসেজ পাঠানো
        try:
            await bot.send_message(target_uid, f"✅ **আপনার উইথড্র অ্যাপ্রুভ হয়েছে!**\n💰 পরিমাণ: {amount} ৳\nটাকা আপনার একাউন্টে পাঠিয়ে দেওয়া হয়েছে।")
        except: pass
            
        # ২. অ্যাডমিন মেসেজ আপডেট (এখানে আর কোনো প্রশ্ন করবে না)
        await call.message.edit_text(call.message.text + f"\n\n✅ **Status: Approved (সফল)**")
        await call.answer("পেমেন্ট অ্যাপ্রুভড!", show_alert=True)

    elif action == "reject":
        # টাকা ফেরত দেওয়া
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_uid))
        db.commit()
        
        try:
            await bot.send_message(target_uid, f"❌ **আপনার উইথড্র রিজেক্ট করা হয়েছে।**\n💰 {amount} ৳ ফেরত দেওয়া হয়েছে।")
        except: pass
            
        await call.message.edit_text(call.message.text + "\n\n❌ **Status: Rejected (টাকা ফেরত)**")
        await call.answer("রিজেক্ট করা হয়েছে!", show_alert=True)
        # --- ধাপ ২: রেফারেল মেনু আপডেট ---
@dp.message_handler(lambda message: message.text == "👥 Referral")
async def referral_menu(message: types.Message):
    user_id = message.from_user.id
    
    # ডাটাবেস থেকে রেফার ব্যালেন্স এবং মেইন ব্যালেন্স আনা
    cursor.execute("SELECT refer_balance, balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    ref_balance = res[0] if res else 0
    main_balance = res[1] if res else 0

    # ইনলাইন কিবোর্ড তৈরি (নতুন বাটনসহ)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💰 Add to Main Balance", callback_data="transfer_ref_request"),
        types.InlineKeyboardButton("📜 Rules", callback_data="ref_rules")
    )
    
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    
    text = (
        f"👥 **রেফারেল ড্যাশবোর্ড**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 **রেফার ব্যালেন্স:** `{ref_balance:.2f} ৳`\n"
        f"💰 **মেইন ব্যালেন্স:** `{main_balance:.2f} ৳`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 **আপনার রেফার লিংক:**\n`{ref_link}`\n\n"
        f"✨ রেফার ব্যালেন্স মেইন ব্যালেন্সে নিতে নিচের বাটনে ক্লিক করুন। 👇"
    )
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
# --- ১. ইউজার যখন বাটনে ক্লিক করবে ---
@dp.callback_query_handler(text="transfer_ref_request")
async def ask_transfer_amount(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    
    # ডাটাবেস থেকে ইউজারের রেফার ব্যালেন্স চেক করা
    cursor.execute("SELECT refer_balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    ref_bal = res[0] if res else 0
    
    # যদি ব্যালেন্স ০ বা তার কম হয়
    if ref_bal <= 0:
        return await call.answer("⚠️ আপনার কোনো রেফার ব্যালেন্স নেই!", show_alert=True)
    
    # স্টেট সেট করা (টাকার পরিমাণ নেওয়ার জন্য)
    await BotState.waiting_for_transfer_amount.set() 
    
    # ইউজারকে মেসেজ দেওয়া
    text = (
        f"💰 আপনার বর্তমান রেফার ব্যালেন্স: `{ref_bal:.2f} ৳`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "আপনি কত টাকা মেইন ব্যালেন্সে নিতে চান? পরিমাণটি সংখ্যায় লিখুন (যেমন: ২০):"
    )
    await call.message.answer(text)
    await call.answer()
    # --- ২. ইউজার টাকার পরিমাণ লিখে পাঠালে অ্যাডমিনকে জানানো ---
@dp.message_handler(state=BotState.waiting_for_transfer_amount)
async def send_transfer_request_to_admin(message: types.Message, state: FSMContext):
    # ইনপুটটি সংখ্যা কি না চেক করা
    if not message.text.isdigit():
        return await message.answer("❌ অনুগ্রহ করে সঠিক সংখ্যা লিখুন (যেমন: ৫০)")

    amount = float(message.text)
    user_id = message.from_user.id
    
    # ডাটাবেস থেকে ইউজারের বর্তমান রেফার ব্যালেন্স চেক করা
    cursor.execute("SELECT refer_balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    current_ref_bal = res[0] if res else 0

    # ইউজারের কি যথেষ্ট ব্যালেন্স আছে?
    if amount > current_ref_bal:
        return await message.answer(f"❌ আপনার পর্যাপ্ত রেফার ব্যালেন্স নেই!\nবর্তমান ব্যালেন্স: `{current_ref_bal:.2f} ৳`")

    # পরিমাণ যদি ০ এর কম হয়
    if amount <= 0:
        return await message.answer("❌ সর্বনিম্ন ১ টাকা ট্রান্সফার করা যাবে।")

    # অ্যাডমিনের জন্য কিবোর্ড তৈরি (Approve/Reject বাটন)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Add Money", callback_data=f"ref_adm_add_{user_id}_{amount}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"ref_adm_rej_{user_id}_{amount}")
    )

    # অ্যাডমিনকে পাঠানোর মেসেজ
    admin_text = (
        f"🔄 **নতুন ব্যালেন্স ট্রান্সফার রিকোয়েস্ট!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 নাম: {message.from_user.full_name}\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"🔗 ইউজারনেম: @{message.from_user.username or 'No_Username'}\n"
        f"💰 পরিমাণ: **{amount:.2f} ৳**\n"
        f"🏠 মেথড: **Refer to Main Balance**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"আপনি কি এই টাকা মেইন ব্যালেন্সে এড করতে চান? 👇"
    )

    # অ্যাডমিনকে মেসেজ পাঠানো
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="Markdown")
    
    # ইউজারকে জানানো
    await message.answer(
        f"✅ আপনার **{amount:.2f} ৳** ট্রান্সফার রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।\n"
        f"⏳ অ্যাডমিন এপ্রুভ করলে আপনার মেইন ব্যালেন্সে টাকা যোগ হয়ে যাবে।",
        reply_markup=main_menu() # আপনার মেইন মেনু ফাংশনটি কল করুন
    )
    
    # স্টেট শেষ করা
    await state.finish()
    # --- ৫. অ্যাডমিন যখন ব্যালেন্স ট্রান্সফার এপ্রুভ বা রিজেক্ট করবে ---
@dp.callback_query_handler(lambda c: c.data.startswith('ref_adm_'), user_id=ADMIN_ID)
async def handle_transfer_approval(call: types.CallbackQuery):
    # ডাটা আলাদা করা (ref_adm_add_USERID_AMOUNT)
    data = call.data.split('_')
    action = data[2] # add অথবা rej
    target_uid = int(data[3])
    amount = float(data[4])

    if action == "add":
        # ১. ডাটাবেসে মেইন ব্যালেন্স যোগ এবং রেফার ব্যালেন্স বিয়োগ করা
        # আমরা সরাসরি SQL দিয়ে একবারে করছি যাতে কোনো ভুল না হয়
        cursor.execute(
            "UPDATE users SET balance = balance + ?, refer_balance = refer_balance - ? WHERE user_id = ?", 
            (amount, amount, target_uid)
        )
        db.commit()

        # ২. ইউজারকে সুখবর পাঠানো
        try:
            success_text = (
                f"🎉 **অভিনন্দন!**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"আপনার **{amount:.2f} ৳** রেফার ব্যালেন্স থেকে মেইন ব্যালেন্সে সফলভাবে যুক্ত হয়েছে।\n"
                f"এখন আপনি এই টাকা উইথড্র করতে পারবেন। ধন্যবাদ! ✨"
            )
            await bot.send_message(target_uid, success_text, parse_mode="Markdown")
        except:
            pass

        # ৩. অ্যাডমিন মেসেজ আপডেট করা
        await call.message.edit_text(call.message.text + f"\n\n✅ **Status: Money Added to Main Balance**")
        await call.answer("টাকা সফলভাবে মেইন ব্যালেন্সে যোগ হয়েছে!", show_alert=True)

    elif action == "rej":
        # রিজেক্ট করলে শুধু স্ট্যাটাস আপডেট হবে (টাকা ইউজারের রেফার ব্যালেন্সেই থেকে যাবে)
        try:
            await bot.send_message(target_uid, f"❌ দুঃখিত! আপনার **{amount:.2f} ৳** ব্যালেন্স ট্রান্সফার রিকোয়েস্ট অ্যাডমিন রিজেক্ট করেছে।")
        except:
            pass

        await call.message.edit_text(call.message.text + "\n\n❌ **Status: Request Rejected**")
        await call.answer("রিকোয়েস্ট রিজেক্ট করা হয়েছে।", show_alert=True)
    
if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
