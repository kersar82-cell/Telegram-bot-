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
# --- ডাটাবেজ আপডেট করার কোড (এটি নিশ্চিত করবে সব কলাম আছে) ---
try:
    # রেফার ব্যালেন্স জমানোর জন্য কলাম
    cursor.execute("ALTER TABLE users ADD COLUMN refer_balance REAL DEFAULT 0.0")
except:
    pass

try:
    # উইথড্র সংখ্যা ১০ বার লিমিট চেক করার জন্য কলাম
    cursor.execute("ALTER TABLE users ADD COLUMN withdraw_count INTEGER DEFAULT 0")
except:
    pass

try:
    # কে কাকে রেফার করেছে তা সেভ করার জন্য কলাম
    cursor.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")
except:
    pass

db.commit()
print("✅ ডাটাবেজ সফলভাবে আপডেট হয়েছে!")
    

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
    keyboard.row("💻INSTAGRAM WORK", "💻FACEBOOK WORK")
    keyboard.row("☎️SUPPORT", "🎁INVITE BONUS")
    keyboard.row("🔊RULES & PRICE", "💳WITHDRAW")
    
    keyboard.row("🏆LEADERBOARD", "📊MY STATUS")
    
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
        referrer_id = 0
        if args and args.isdigit():
            temp_id = int(args)
            # চেক করা হচ্ছে ইউজার নিজের লিংকে নিজে ক্লিক করেছে কি না
            if temp_id != user_id:
                referrer_id = temp_id
                # ১. রেফারারের কাউন্ট ১ বাড়ানো
                cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
                db.commit()
                
                # ২. রেফারারকে মেসেজ পাঠানো
                try:
                    await bot.send_message(referrer_id, "🔔 **অভিনন্দন!**\n\nআপনার রেফারেল লিঙ্ক ব্যবহার করে একজন নতুন ইউজার জয়েন করেছে। 🥳")
                except:
                    pass

        # ৩. ডাটাবেসে নতুন ইউজার সেভ করা (আপনার সব কলামের সিরিয়াল ঠিক রেখে)
        # কলামগুলো: user_id, username, balance, referral_count, referred_by, refer_balance, withdraw_count
        sql = "INSERT INTO users (user_id, username, balance, referral_count, referred_by, refer_balance, withdraw_count) VALUES (?, ?, ?, ?, ?, ?, ?)"
        cursor.execute(sql, (user_id, username, 0.0, 0, referrer_id, 0.0, 0))
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
# ১. এখানে নামের বানান এবং স্পেস আপনার বাটন অনুযায়ী ঠিক করা হয়েছে
@dp.message_handler(lambda message: message.text in ["IG Mother Account", "IG 2fa", "IG Cookies"])
async def ask_work_type(message: types.Message, state: FSMContext):
    # ক্যাটাগরি সেভ করা হচ্ছে
    await state.update_data(category=message.text)
    
    inline_kb = types.InlineKeyboardMarkup(row_width=2)
    btn_file = types.InlineKeyboardButton("🗃️ File", callback_data="type_file")
    btn_single = types.InlineKeyboardButton("👤 Single ID", callback_data="type_single")

    # ২. কন্ডিশন চেক: যদি বাটন "IG Cookies" হয়
    if message.text == "IG Cookies":
        btn_link = types.InlineKeyboardButton("🔗 Submit Link", url="https://t.me/instafb_hub/108")
        inline_kb.add(btn_file, btn_single)
        inline_kb.add(btn_link)
    else:
        inline_kb.add(btn_file, btn_single)

    await message.answer(f"✅ আপনি বেছে নিয়েছেন: **{message.text}**\n\n━━━━━━━━━━━━━━━\n\nএখন কিভাবে ডাটা জমা দিতে চান? নিচের বাটন থেকে সিলেক্ট করুন।", 
                         reply_markup=inline_kb, 
                         parse_mode="Markdown")
    
@dp.message_handler(lambda message: message.text == "💻INSTAGRAM WORK")
async def work_start(message: types.Message):
    if await is_blocked(message.from_user.id):
        return await message.answer("❌ দুঃখিত, আপনি ব্লকড! আপনি আর কাজ জমা দিতে পারবেন না। /nএডমিনের সাথে কথা বলুন 👍")
    
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # প্রথম লাইনে এই দুটি বাটন থাকবে
    keyboard.row("IG Mother Account", "IG 2fa")
    
    # দ্বিতীয় লাইনে IG Cookies বাটনটি একা থাকবে
    keyboard.row("IG Cookies", "🔄রিফ্রেশ") 
    
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
@dp.message_handler(lambda message: message.text == "💳WITHDRAW")
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
    
        # ... আগের ব্যালেন্স আপডেট এবং কমিশনের হিসাবের নিচে ...
    user_name = f"@{message.from_user.username}" if message.from_user.username else "নেই"
    
    # ২. এইখানে আপনার আগের admin_text সরিয়ে এটি বসান
    admin_text = (
        f"{withdraw_title}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {user_name}\n"
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

    # ৩. এইখানে আগের kb সরিয়ে এটি বসান
    kb = types.InlineKeyboardMarkup()
    kb.add(
        # এখানে callback_data এর ভেতর commission পাঠানো হয়েছে
        types.InlineKeyboardButton("✅ Approve", callback_data=f"admin_payment_approve_{user_id}_{amount}_{commission}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_payment_reject_{user_id}_{amount}")
    )

    # ৪. এরপর অ্যাডমিনকে মেসেজ পাঠানো
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="Markdown")
    
    # ইউজারকে কনফার্মেশন পাঠানো
    await message.answer("✅ আপনার উইথড্র রিকোয়েস্ট জমা হয়েছে!", reply_markup=main_menu())
    await state.finish()

# ৪. এডমিন প্যানেল
# ==========================================
@dp.message_handler(commands=['check_user'])
async def check_user_details(message: types.Message):
    # আপনার অ্যাডমিন চেক করার কন্ডিশন (যেমন: if message.from_user.id != ADMIN_ID: return)
    if message.from_user.id != ADMIN_ID:
        return

    args = message.get_args()
    if not args or not args.isdigit():
        return await message.answer("⚠️ আইডি দিন। উদাহরণ: `/check_user 12345678`", parse_mode="Markdown")

    target_id = int(args)

    # ডাটাবেস থেকে সব তথ্য একসাথে আনা
    cursor.execute("""SELECT username, balance, refer_balance, bkash_num, nagad_num, 
                      rocket_num, recharge_num, binance_id FROM users WHERE user_id=?""", (target_id,))
    res = cursor.fetchone()

    if res:
        username, balance, ref_balance, bkash, nagad, rocket, recharge, binance = res
        
        info_text = (
            f"👤 **ইউজার ডিটেইলস**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **ইউজার আইডি:** `{target_id}`\n"
            f"📛 **ইউজার নেম:** {username if username else 'নেই'}\n\n"
            
            f"💰 **ব্যালেন্স ডিটেইলস:**\n"
            f"💵 মেইন ব্যালেন্স: `{balance:.2f} ৳`\n"
            f"👥 রেফার ব্যালেন্স: `{ref_balance:.2f} ৳`\n\n"
            
            f"📱 **মোবাইল রিচার্জ মেথড:**\n"
            f"📞 নম্বর: `{recharge if recharge else 'সেট নেই'}`\n\n"
            
            f"💸 **সেন্ড মানি মেথডসমূহ:**\n"
            f"🔸 বিকাশ: `{bkash if bkash else 'সেট নেই'}`\n"
            f"🔸 নগদ: `{nagad if nagad else 'সেট নেই'}`\n"
            f"🔸 রকেট: `{rocket if rocket else 'সেট নেই'}`\n"
            f"🔸 বিন্যান্স: `{binance if binance else 'সেট নেই'}`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await message.answer(info_text, parse_mode="Markdown")
    else:
        await message.answer("❌ দুঃখিত, এই আইডি দিয়ে কোনো ইউজার পাওয়া যায়নি।")
        
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
