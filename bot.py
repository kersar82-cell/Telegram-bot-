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
# --- ফোর্স জয়েন সেটিংস ---
CHANNEL_ID = "@instafb_hub" 
CHANNEL_LINK = "https://t.me/instafb_hub"
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
async def check_user_joined(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        # যদি ইউজার মেম্বার, অ্যাডমিন বা ক্রিয়েটর হয় তবে True
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            return False
    except Exception:
        return False


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
        # ১. প্রথমে চেক করবে ইউজার গ্রুপে আছে কি না
    is_joined = await check_user_joined(user_id)
    
    if not is_joined:
        # যদি জয়েন না থাকে তবে নিচের এই বাটনগুলো দেখাবে
        join_kb = types.InlineKeyboardMarkup()
        join_kb.add(types.InlineKeyboardButton("📢 গ্রুপে জয়েন করুন", url=CHANNEL_LINK))
        join_kb.add(types.InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_join_now"))
        
        return await message.answer(
            f"👋 হ্যালো {user_name}!\n\n"
            "আমাদের বটটি ব্যবহার করতে হলে আপনাকে অবশ্যই নিচের গ্রুপে জয়েন করতে হবে।\n"
            "জয়েন করার পর '✅ জয়েন করেছি' বাটনে ক্লিক করুন।",
            reply_markup=join_kb
        )
# ৪. ইউজারকে মেসেজ পাঠানো
    await message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    await message.answer("✅ আপনার কাজের ধরণ বেছে নিন:", reply_markup=main_menu())

    # ২. যদি অলরেডি জয়েন থাকে, তবেই আপনার আগের মেসেজগুলো যাবে
    await message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    await message.answer("✅ আপনার কাজের ধরণ বেছে নিন:", reply_markup=main_menu())
@dp.callback_query_handler(text="check_join_now")
async def check_join_callback(call: types.CallbackQuery):
    is_joined = await check_user_joined(call.from_user.id)
    
    if is_joined:
        await call.answer("✅ অভিনন্দন! আপনি গ্রুপে জয়েন করেছেন।", show_alert=True)
        await call.message.delete() # জয়েন করার অনুরোধের মেসেজটি মুছে যাবে
        
        # এখানে আপনার মেইন মেনু দেখানোর কোড (আগে স্টার্টে যা ছিল)
        welcome_text = "🎉 স্বাগতম! আপনি এখন সফলভাবে ভেরিফাইড।"
        inline_kb = types.InlineKeyboardMarkup() # আপনার যদি কোনো ইনলাইন বাটন থাকে এখানে যোগ করবেন
        
        await call.message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
        await call.message.answer("✅ আপনার কাজের ধরণ বেছে নিন:", reply_markup=main_menu())
    else:
        # যদি এখনো জয়েন না করে থাকে
        await call.answer("❌ আপনি এখনো গ্রুপে জয়েন করেননি! দয়া করে জয়েন করে আবার চেষ্টা করুন।", show_alert=True)
        
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
        return await message.answer("❌ দুঃখিত, আপনি ব্লকড!")
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # প্রথম লাইনে এই দুটি বাটন থাকবে
    keyboard.row("IG Mother Account", "IG 2fa")
    
    # দ্বিতীয় লাইনে IG Cookies বাটনটি একা থাকবে
    keyboard.row("IG Cookies")
    
    # সবশেষে রিফ্রেশ বাটন
    keyboard.row("🔄 রিফ্রেশ") 
    
    msg = """ 𝗡𝗢𝗥𝗗 𝗩𝗣𝗡 𝗣𝗥𝗘𝗠𝗜𝗨𝗠
━━━━━━━━━━━━━━━━━━
🥲 Email = `chriskr508@gmail.com`
🔐 Pass  = `Automan1012`

🥲 Email = `evanmkma2011@gmail.com`
🔐 Pass  = `Devamar88!#`

🥲Email = `gaughan9999@hotmail.co.uk`
🔐Pass  = `Auders*1`"""
    
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
  
