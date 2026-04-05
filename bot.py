import logging
import sqlite3
import os 
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from supabase import create_client, Client

# আপনার ডাটাবেস তথ্য
SUPABASE_URL = "https://mxxxnwnberhhnpgfmzml.supabase.co"
SUPABASE_KEY = "sb_publishable_NhIUA5uUQMKB7wBhxH2oxg_myQWFWJ0"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
def save_id_supabase(user_id, u_id, u_pass, two_fa, category):
    try:
        data = {
            "user_id": str(user_id),
            "u_id": str(u_id),
            "u_pass": str(u_pass),
            "two_fa": str(two_fa),
            "category": str(category)
        }
        # এটি ১০০০ মানুষ একসাথে করলেও ডাটাবেস লক হবে না
        supabase.table("user_id_logs").insert(data).execute()
        return True
    except Exception as e:
        print(f"সেভ করতে সমস্যা হয়েছে: {e}")
        return False

# ==========================================
# ১. সেটিংস ও ডাটাবেস
# ==========================================
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
FILE_ADMIN_ID = 7446548744
# ফোর্জ জয়েন সেটিংস
CHANNEL_ID = -1003869471032  # আপনার দেওয়া আইডি
CHANNEL_LINK = "https://t.me/instafbhub" # আপনার গ্রুপের লিঙ্ক
# এটি বটের যেকোনো জায়গায় বসাতে পারেন (ফাংশনের বাইরে)
WITHDRAW_ENABLED = True 
# কাজগুলো অন/অফ করার জন্য ভেরিয়েবল
IG_MOTHER_ENABLED = True
IG_2FA_ENABLED = True
IG_COOKIES_ENABLED = True

# রেফারেল থেকে মেইন ব্যালেন্স এড করার সুইচ
REFER_ADD_ENABLED = True
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
  # ডাটাবেসে পেন্ডিং ব্যালেন্স কলাম যোগ করা
try:
    cursor.execute("ALTER TABLE users ADD COLUMN pending_balance REAL DEFAULT 0.0")
    db.commit()
except:
    pass
# এটি একবারে রান করলেই হবে
cursor.execute('''CREATE TABLE IF NOT EXISTS user_id_logs 
                  (user_id INTEGER, category TEXT, u_id TEXT, u_pass TEXT, two_fa TEXT, date_time TEXT)''')
db.commit()

# user_id এর ওপর একটি ইনডেক্স তৈরি করা
cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON user_id_logs (user_id)")
db.commit()
    # ডাটাবেস সেটআপ অংশে এটি যোগ করুন
cursor.execute('''CREATE TABLE IF NOT EXISTS ids 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   category TEXT, 
                   u_id TEXT, 
                   u_pass TEXT, 
                   status TEXT DEFAULT 'Pending')''')
db.commit()
# --- ধাপ ১: ডাটাবেসে পেমেন্ট মেথড কলাম যোগ করা ---
new_columns = ["bkash_num", "nagad_num", "rocket_num", "binance_id", "recharge_num"]
for col in new_columns:
    try:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        db.commit()
    except Exception:
        pass # যদি কলাম আগে থেকেই থাকে, তবে এরর ইগনোর করে পরের কলামটি চেক করবে

class BotState(StatesGroup):
    waiting_for_file = State()
    waiting_for_address = State()
    waiting_for_withdraw_amount = State()
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
    waiting_for_auto_2fa = State() # এটি নতুন লাইন

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
    
async def check_joined(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception:
        return False
import random

def generate_ig_username():
    # অনেকগুলো প্রিফিক্স
    prefixes = [
        "itz", "the_real", "official", "daily", "ig", "pro", "mr", "pure", "iam", "its_me", 
        "vloger", "king", "queen", "smart", "cool", "stylish", "creative", "urban", "boss", "elite"
    ]
    
    # অনেকগুলো নাম (দেশি ও বিদেশি মিশিয়ে)
    names = [
        "rahul", "alex", "nila", "sam", "jhon", "riya", "max", "khan", "arman", "sara",
        "tushar", "emran", "firoz", "mim", "liza", "pavel", "abir", "sakib", "rakib", "shuvo",
        "david", "kevin", "linda", "amy", "rose", "jack", "tom", "jerry", "leo", "mia"
    ]
    
    # সাফিক্স বা শেষের অংশ
    suffix = [
        "_official", "_vlogs", "77", "_01", "360", "_king", "_99", "_zone", "_hub", "_studio",
        ".me", "_world", "_404", "_xd", "_life", "007", "_bd", "_usa", "_top", "_star"
    ]
    
    # র‍্যান্ডমলি সিলেক্ট করা
    p = random.choice(prefixes)
    n = random.choice(names)
    s = random.choice(suffix)
    num = random.randint(1000, 99999) # ৪ থেকে ৫ ডিজিটের বড় সংখ্যা যাতে ডুপ্লিকেট না হয়
    
    # বিভিন্ন ফরম্যাটে নাম জেনারেট করা
    formats = [
        f"{p}_{n}{num}",
        f"{n}_{p}{s}",
        f"{p}{n}_{num}",
        f"{n}{num}{s}",
        f"{p}_{n}_{s}{num}"
    ]
    
    return random.choice(formats)
    
# /start কমান্ডে মেইন মেনু, রেফারেল ও ওয়েলকাম মেসেজ
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
       
    user_id = message.from_user.id
            # গ্রুপে জয়েন আছে কি না চেক
    is_joined = await check_joined(user_id)
    if not is_joined:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📢 আমাদের গ্রুপে জয়েন করুন", url=CHANNEL_LINK))
        keyboard.add(types.InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_join"))
        
        return await message.answer(
            "👋 দুঃখিত! আপনি আমাদের গ্রুপে জয়েন নেই।\n\n"
            "বটটি ব্যবহার করতে নিচের বাটনে ক্লিক করে গ্রুপে জয়েন করুন।",
            reply_markup=keyboard
        )
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
    help_button = types.InlineKeyboardButton(text="🆘 Contact Support", url="t.me/INSTAFB_SUPPORT") 
    inline_kb.add(help_button)

    welcome_text = """📢 আজকের কাজের আপডেট এবং রেট লিস্ট 📢

💸 Instagram 2FA: ৩ ৳🎉

💸 Instagram Cookies: ৪.০০ ৳🎉

💸 Instagram Mother: ৭.০০ ৳🎉

💸 Facebook 00 Fnd 2FA: ৫.৮০ ৳🎉
"""

    # ৪. ইউজারকে মেসেজ পাঠানো
    await message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    await message.answer("❓কী করতে চান বেছে নিন ◀️", reply_markup=main_menu())
    
# ১. এখানে নামের বানান এবং স্পেস আপনার বাটন অনুযায়ী ঠিক করা হয়েছে

@dp.message_handler(lambda message: message.text == "💻INSTAGRAM WORK")
async def work_start(message: types.Message):
    if await is_blocked(message.from_user.id):
        return await message.answer("❌ দুঃখিত, আপনি ব্লকড! আপনি আর কাজ জমা দিতে পারবেন না। \nএডমিনের সাথে কথা বলুন 👍")
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # বাটনগুলো সাজানো
    keyboard.row("IG Mother Account", "IG 2fa")
    keyboard.row("IG Cookies", "🔄 রিফ্রেশ") 
    
    msg = """🔐NORD VPN
🌐Email > gaughan9999@hotmail.co.uk
🔐Pass  > Auders*1

🌐Email > betzcampaign@gmail.com
🔐Pass  > Hnhnddio1986!

🌐Email > thomasvcrowl@gmail.com
🔐Pass  > HeretiC762!!"""

    # এখানে parse_mode সরিয়ে দেওয়া হয়েছে যাতে স্পেশাল ক্যারেক্টারের কারণে এরর না আসে
    await message.answer(msg, reply_markup=keyboard)

                    
# এই হ্যান্ডলারটি এখন একদম পারফেক্ট কাজ করবে
@dp.message_handler(lambda message: message.text in ["IG Mother Account", "IG 2fa", "IG Cookies"])
async def ask_work_type(message: types.Message, state: FSMContext):
    category = message.text
    
    # আপনার আগের অন/অফ লজিকগুলো ঠিক রাখা হয়েছে
    if category == "IG Mother Account" and not IG_MOTHER_ENABLED:
        return await message.answer("⚠️ দুঃখিত, বর্তমানে IG Mother Account কাজ সাময়িকভাবে বন্ধ আছে।")
    if category == "IG 2fa" and not IG_2FA_ENABLED:
        return await message.answer("⚠️ দুঃখিত, বর্তমানে IG 2fa কাজ সাময়িকভাবে বন্ধ আছে।")
    if category == "IG Cookies" and not IG_COOKIES_ENABLED:
        return await message.answer("⚠️ দুঃখিত, বর্তমানে IG Cookies কাজ সাময়িকভাবে বন্ধ আছে।")

    # অটোমেটিক ইউজারনেম এবং ফিক্সড পাসওয়ার্ড জেনারেট
    username = generate_ig_username() # এটি ধাপ ২ এর ফাংশন থেকে আসবে
    fixed_password = "UserPass@2026" 

    # ডাটাগুলো বটের মেমোরিতে সেভ রাখা
    await state.update_data(auto_user=username, auto_pass=fixed_password, category=category)

    # ইনলাইন বাটন তৈরি (HTML এর জন্য ইনলাইন বাটনই বেস্ট)
    inline_kb = types.InlineKeyboardMarkup(row_width=1)
    btn_2fa = types.InlineKeyboardButton("🔐 2FA কোড দিন", callback_data="ask_auto_2fa")
    btn_regen = types.InlineKeyboardButton("🔄 নতুন ইউজারনেম (Regenerate)", callback_data="regen_ig_user")
    btn_back = types.InlineKeyboardButton("🔙 ফিরে যান", callback_data="back_to_main")
    inline_kb.add(btn_2fa, btn_regen, btn_back)

    # HTML ফরম্যাটে মেসেজ (<code> ব্যবহারের ফলে ক্লিক করলে কপি হবে)
    text = (
        f"<b>✅ আপনি বেছে নিয়েছেন:</b> {category}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>👤 Username:</b> <code>{username}</code>\n"
        f"<b>🔑 Password:</b> <code>{fixed_password}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>💡 উপরের তথ্য দিয়ে লগিন করুন। ইউজারনেম না মিললে '🔄 নতুন ইউজারনেম' বাটনে ক্লিক করুন। কাজ শেষে ২এফএ কোড দিন।</i>"
    )

    await message.answer(text, reply_markup=inline_kb, parse_mode="HTML")
    # ১. "🔄 নতুন ইউজারনেম" বাটনের কাজ (Regenerate)
@dp.callback_query_handler(lambda c: c.data == "regen_ig_user", state="*")
async def regenerate_user_logic(call: types.CallbackQuery, state: FSMContext):
    # নতুন একটি ইউনিক নাম তৈরি করা
    new_username = generate_ig_username()
    
    # মেমোরি থেকে আগের ক্যাটাগরি এবং পাসওয়ার্ড নেওয়া
    user_data = await state.get_data()
    category = user_data.get("category", "IG Work")
    fixed_pass = user_data.get("auto_pass", "UserPass@2026")

    # মেমোরিতে নতুন ইউজারনেমটি আপডেট করে রাখা
    await state.update_data(auto_user=new_username)

    # ইনলাইন বাটনগুলো আগের মতোই থাকবে
    inline_kb = types.InlineKeyboardMarkup(row_width=1)
    btn_2fa = types.InlineKeyboardButton("🔐 2FA কোড দিন", callback_data="ask_auto_2fa")
    btn_regen = types.InlineKeyboardButton("🔄 নতুন ইউজারনেম (Regenerate)", callback_data="regen_ig_user")
    btn_back = types.InlineKeyboardButton("🔙 ফিরে যান", callback_data="back_to_main")
    inline_kb.add(btn_2fa, btn_regen, btn_back)

    # HTML ফরম্যাটে আগের মেসেজটি এডিট করা (যাতে স্ক্রিন ক্লিন থাকে)
    text = (
        f"<b>📌 ক্যাটাগরি:</b> {category}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>👤 Username:</b> <code>{new_username}</code> (Updated ✨)\n"
        f"<b>🔑 Password:</b> <code>{fixed_pass}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>💡 নতুন ইউজারনেম জেনারেট হয়েছে। এটি কপি করে লগিন করুন এবং কাজ শেষে ২এফএ কোড দিন।</i>"
    )
    
    try:
        await call.message.edit_text(text, reply_markup=inline_kb, parse_mode="HTML")
        await call.answer("✅ নতুন ইউজারনেম তৈরি হয়েছে!")
    except Exception as e:
        await call.answer("⚠️ কোনো পরিবর্তন হয়নি বা এরর হয়েছে।")
# 2FA কোড নেওয়ার জন্য নতুন হ্যান্ডলার
@dp.callback_query_handler(lambda c: c.data == "ask_auto_2fa", state="*")
async def trigger_2fa_input(call: types.CallbackQuery):
    # ইউজারকে 2FA দেওয়ার স্টেটে নিয়ে যাওয়া
    await BotState.waiting_for_auto_2fa.set()
    
    # ইনলাইন মেসেজটি এডিট করে বা নতুন মেসেজ দিয়ে কোড চাওয়া
    await call.message.answer(
        "🔐 **অনুগ্রহ করে আপনার 2FA (Two-Factor Authentication) কোডটি নিচে লিখে পাঠান:**", 
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await call.answer()
    
# ২. "🔙 ফিরে যান" বাটনের কাজ
@dp.callback_query_handler(lambda c: c.data == "back_to_main", state="*")
async def go_back_to_home(call: types.CallbackQuery, state: FSMContext):
    await state.finish() # সব স্টেট ক্লিয়ার করা
    await call.message.delete() # বর্তমান মেসেজটি মুছে ফেলা
    await call.message.answer("🏠 আপনি মেইন মেনুতে ফিরে এসেছেন।", reply_markup=main_menu())
    await call.answer()
    # ১. ২এফএ কোড চাওয়ার বাটন হ্যান্ডলার

        # ২. ২এফএ রিসিভ করে সরাসরি সেভ করা এবং ব্যালেন্স অ্যাড করা
@dp.message_handler(state=BotState.waiting_for_auto_2fa)
async def process_auto_2fa_submission(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    username = user_data.get('auto_user')
    password = user_data.get('auto_pass')
    category = user_data.get('category')
    tfa_code = message.text # ইউজারের পাঠানো কোড

    if username and password:
        # স্ট্যাটাসসহ ক্যাটাগরি নাম (যাতে আপনার প্যানেলে 'Done' দেখায়)
        final_category = f"{category} [✅ Done]"

        # ১. সরাসরি Supabase এ সেভ
        save_id_supabase(
            user_id=message.from_user.id,
            u_id=username,
            u_pass=password,
            two_fa=tfa_code,
            category=final_category
        )

        import datetime
        # ২. লোকাল ডাটাবেসে সেভ করা
        bd_now = datetime.datetime.now() + datetime.timedelta(hours=6)
        dt_log = bd_now.strftime("%d/%m/%Y %I:%M %p") 
        cursor.execute("INSERT INTO user_id_logs (user_id, category, u_id, u_pass, two_fa, date_time) VALUES (?, ?, ?, ?, ?, ?)", 
                       (message.from_user.id, category, username, password, tfa_code, dt_log))
        
        # ৩. ইউজারের স্ট্যাটাস আপডেট
        today = datetime.date.today().strftime("%Y-%m-%d")
        cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
        cursor.execute("UPDATE stats SET single_id_count = single_id_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))

        # ৪. ব্যালেন্স অ্যাড করা
        amount_to_add = 0 
        if category == "IG Cookies":
            amount_to_add = 4
        elif category == "IG Mother Account":
            amount_to_add = 7
        elif category == "IG 2fa":
            amount_to_add = 3

        if amount_to_add > 0:
            cursor.execute("UPDATE users SET pending_balance = pending_balance + ? WHERE user_id = ?", (amount_to_add, message.from_user.id))
        db.commit()

        # ৫. অ্যাডমিনকে রিপোর্ট পাঠানো
        admin_report = (
            f"🚀 <b>নতুন অটো-টাস্ক সম্পন্ন!</b>\n"
            f"👤 <b>ইউজার:</b> {message.from_user.full_name}\n"
            f"🆔 <b>আইডি:</b> <code>{message.from_user.id}</code>\n"
            f"📂 <b>ক্যাটাগরি:</b> {category}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{username}</code>\n"
            f"🔑 <b>Pass:</b> <code>{password}</code>\n"
            f"🔐 <b>2FA:</b> <code>{tfa_code}</code>"
        )
        await bot.send_message(FILE_ADMIN_ID, admin_report, parse_mode="HTML")

        # ৬. সাকসেস মেসেজ ও নতুন কিবোর্ড
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(f"➕ আরেকটি {category} পাঠান") 
        markup.add("🏠 মেইন মেনু")
        
        await message.answer(
            f"<b>✅ আইডি সফলভাবে জমা হয়েছে!</b>\n\n"
            f"👤 ইউজারনেম: <code>{username}</code>\n"
            f"📊 স্ট্যাটাস: <b>🟢 সম্পন্ন (Done)</b>\n\n"
            f"ধন্যবাদ! আপনার তথ্য ডাটাবেসে সেভ করা হয়েছে।", 
            reply_markup=markup, parse_mode="HTML"
        )
        
        await state.finish()
    else:
        await message.answer("⚠️ সেশন এরর! দয়া করে মেনু থেকে আবার ক্যাটাগরি সিলেক্ট করুন।", reply_markup=main_menu())
        await state.finish()

        # ==========================================
# নির্দিষ্ট ইউজারের সব আইডি ডিলিট করার কমান্ড
# ==========================================
@dp.message_handler(commands=['del_user_data'], user_id=ADMIN_ID)
async def delete_user_all_ids(message: types.Message):
    # কমান্ডটি হবে: /del_user_data [ইউজার_আইডি]
    target_user = message.get_args()
    
    if not target_user or not target_user.isdigit():
        return await message.answer("❌ সঠিক নিয়ম: `/del_user_data [ইউজার_আইডি]`\nউদাহরণ: `/del_user_data 123456789`", parse_mode="Markdown")
    
    deleted_msg = await message.answer("⏳ ডাটাবেস থেকে ইউজারের সব আইডি খোঁজা হচ্ছে এবং ডিলিট করা হচ্ছে...")

    try:
        # ১. Supabase (Cloud Database) থেকে সব ডাটা ডিলিট করা
        supabase.table("user_id_logs").delete().eq("user_id", str(target_user)).execute()
        
        # ২. SQLite (Local Database) থেকে ডিলিট করা
        cursor.execute("DELETE FROM user_id_logs WHERE user_id = ?", (target_user,))
        db.commit()
        
        # ৩. সবচেয়ে ইম্পর্ট্যান্ট: ডাটাবেস রিকভারি (VACUUM)
        # এটি ডিলিট করা ডাটার ফাঁকা জায়গাটা রিকভার করে ডাটাবেসের সাইজ কমিয়ে দেয়
        cursor.execute("VACUUM")
        db.commit()

        # সফল মেসেজ
        await deleted_msg.edit_text(f"✅ **সাকসেস!**\n\nইউজার `{target_user}` এর পাঠানো সকল আইডি **Supabase** এবং **Local Database** থেকে চিরতরে মুছে ফেলা হয়েছে।\n🚀 ডাটাবেস এখন একদম ফাস্ট এবং চাপমুক্ত!", parse_mode="Markdown")
        
    except Exception as e:
        await deleted_msg.edit_text(f"❌ ডিলিট করতে সমস্যা হয়েছে: {str(e)}")
    
# ১. "🏠 মেইন মেনু" বাটনের কাজ
@dp.message_handler(lambda message: message.text == "🏠 মেইন মেনু", state="*")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    # যে অবস্থাতেই থাকুক না কেন স্টেট ক্লিয়ার করে মেইন মেনুতে নিয়ে যাবে
    await state.finish()
    await message.answer("✅ আপনি মেইন মেনুতে ফিরে এসেছেন।", reply_markup=main_menu())
# আগের দুটি "➕ আরেকটি" হ্যান্ডলার মুছে ফেলে শুধু এই একটি রাখুন
@dp.message_handler(lambda message: "➕ আরেকটি" in message.text, state="*")
async def send_another_id_clean(message: types.Message, state: FSMContext):
    # বাটন থেকে ক্যাটাগরি বের করা (যেমন: IG 2FA)
    text = message.text
    category = text.replace("➕ আরেকটি ", "").replace(" পাঠান", "").strip()
    
    # নতুন ইউজারনেম তৈরি
    new_username = generate_ig_username()
    fixed_password = "UserPass@2026"  # আপনি চাইলে এটি পরিবর্তন করতে পারেন

    # ইউজারের ডাটা আপডেট করা যাতে ২এফএ জমা দেওয়ার সময় কাজে লাগে
    await state.update_data(auto_user=new_username, auto_pass=fixed_password, category=category)

    # ইউজারকে ইনলাইন কিবোর্ড সহ মেসেজ পাঠানো
    inline_kb = types.InlineKeyboardMarkup(row_width=1)
    btn_2fa = types.InlineKeyboardButton("🔐 2FA কোড দিন", callback_data="ask_auto_2fa")
    inline_kb.add(btn_2fa)

    response_text = (
        f"<b>✅ নতুন {category} কাজ বরাদ্দ করা হয়েছে:</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>👤 Username:</b> <code>{new_username}</code>\n"
        f"<b>🔑 Password:</b> <code>{fixed_password}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>💡 আইডি লগইন করে ২এফএ কোডটি নিচের বাটনে ক্লিক করে দিন।</i>"
    )

    await message.answer(response_text, reply_markup=inline_kb, parse_mode="HTML")
    
# ৩. রিফ্রেশ বাটনের লজিক (state="*" যোগ করা হয়েছে যাতে যেকোনো অবস্থায় এটি কাজ করে)
@dp.message_handler(lambda message: message.text == "🔄 রিফ্রেশ", state="*")
async def refresh_to_main(message: types.Message, state: FSMContext):
    # ইউজার যদি ফাইল দেওয়ার স্টেটে থাকে তবে তা ক্লিয়ার করবে
    await state.finish() 
    # মেইন মেনুতে ফিরিয়ে নিবে
    await message.answer("✅ আপনি মেইন মেনুতে ফিরে এসেছেন।", reply_markup=main_menu())
    # ৪. অ্যাডমিন কর্তৃক আইডি স্টক যোগ করার হ্যান্ডেলার
@dp.message_handler(user_id=ADMIN_ID, commands=['add_id'])
async def add_stock_ids(message: types.Message):
    # ফরম্যাট: /add_id Category | Username | Password
    try:
        args = message.get_args().split("|")
        if len(args) == 3:
            category = args[0].strip()
            u_id = args[1].strip()
            u_pass = args[2].strip()

            cursor.execute("INSERT INTO ids (category, u_id, u_pass, status) VALUES (?, ?, ?, ?)", 
                           (category, u_id, u_pass, 'Pending'))
            db.commit()
            await message.answer(f"✅ সফলভাবে স্টক যোগ করা হয়েছে!\n📂 ক্যাটাগরি: {category}\n👤 আইডি: {u_id}")
        else:
            await message.answer("⚠️ সঠিক ফরম্যাট ব্যবহার করুন:\n`/add_id IG 2fa | username | password`", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ ভুল হয়েছে: {e}")

# ৫. স্টকে কয়টি আইডি আছে তা দেখার জন্য (ঐচ্ছিক কিন্তু দরকারি)
@dp.message_handler(user_id=ADMIN_ID, commands=['stock'])
async def check_stock(message: types.Message):
    cursor.execute("SELECT category, COUNT(*) FROM ids WHERE status='Pending' GROUP BY category")
    rows = cursor.fetchall()
    
    if rows:
        text = "📊 **বর্তমান স্টক লিস্ট:**\n"
        for row in rows:
            text += f"🔹 {row[0]}: {row[1]} টি\n"
        await message.answer(text, parse_mode="Markdown")
    else:
        await message.answer("空 বর্তমানে কোনো আইডি স্টক নেই।")
    
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
        # শুধু এই অংশটুকু যোগ করবেন
    if not WITHDRAW_ENABLED:
        return await message.answer("⚠️ বর্তমানে পেমেন্ট সার্ভার রক্ষণাবেক্ষণের জন্য উইথড্র সাময়িকভাবে বন্ধ আছে।\n🔋আজকের রিপোর্ট আসলে তখন আমাদের গ্রুপে জানিয়ে দেওয়া হবে।\nতখন আপনারা উইথড্র করতে পারবেন।\n 💳 Withdraw Option খোলার সময়~~~~~~~\n⌛⏰6.pm-12pm")
    user_id = message.from_user.id
    
    # ইনলাইন কিবোর্ড তৈরি
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("➕ Add Payment Method", callback_data="add_method"),
        types.InlineKeyboardButton("💸 Withdraw", callback_data="start_withdraw"),
        types.InlineKeyboardButton("🔄 রিফ্রেশ", callback_data="refresh_wd")
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
# --- ১. মোবাইল রিচার্জ নম্বর সেভ করা (সংশোধিত) ---
@dp.message_handler(state=BotState.waiting_for_recharge_num)
async def save_recharge_db(message: types.Message, state: FSMContext):
    num = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    full_name = message.from_user.full_name
    
    # ডাটাবেসে সেভ করা
    cursor.execute("UPDATE users SET recharge_num = ? WHERE user_id = ?", (num, user_id))
    db.commit()
    
    # অ্যাডমিনকে জানানো (Markdown এরর এড়াতে নিরাপদভাবে সাজানো)
    admin_text = (
        f"📱 নতুন রিচার্জ নম্বর সেট!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {full_name}\n"
        f"🆔 আইডি: {user_id}\n"
        f"🔗 ইউজারনেম: @{username}\n"
        f"📞 নম্বর: {num}"
    )
    
    try:
        # parse_mode সরিয়ে দেওয়া হয়েছে যাতে নামের মাঝের আন্ডারস্কোর (_) বট ক্র্যাশ না করে
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        print(f"অ্যাডমিনকে মেসেজ পাঠাতে এরর: {e}")
    
    # ইউজারকে রিপ্লাই দেওয়া (এখানে বোল্ড করার জন্য HTML মোড ব্যবহার করা নিরাপদ)
    await message.answer(
        f"✅ আপনার <b>Mobile Recharge</b> নম্বর <code>{num}</code> সফলভাবে সেভ হয়েছে!", 
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    
    # স্টেট অবশ্যই ফিনিশ করতে হবে যাতে ইউজার পরবর্তী কমান্ড দিতে পারে
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
# ১. উইথড্র বাটন দেখানোর ফাংশন (start_withdraw)
@dp.callback_query_handler(text="start_withdraw", state="*")
async def withdraw_selection(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = call.from_user.id
    
    # ডাটাবেস থেকে ব্যালেন্স আনা (দশমিক ছাড়া দেখানোর জন্য int ব্যবহার)
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    balance = int(res[0]) if res else 0

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        # এখানে callback_data গুলো নিচের হ্যান্ডলারের সাথে মিল রাখা হয়েছে
        types.InlineKeyboardButton("📱 Mobile Recharge", callback_data="withdraw_recharge"),
        types.InlineKeyboardButton("💸 Send Money", callback_data="withdraw_sendmoney")
    )
    
    text = (
        f"💰 **আপনার বর্তমান ব্যালেন্স:** `{balance} ৳`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "আপনি কোন মাধ্যমে পেমেন্ট নিতে চান? সিলেক্ট করুন: 👇"
    )

    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except:
        await call.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    
    await call.answer()

# ২. মেথড সিলেক্ট করার পর টাকা চাওয়ার হ্যান্ডলার
@dp.callback_query_handler(lambda c: c.data in ['withdraw_recharge', 'withdraw_sendmoney'])
async def process_withdraw_method(call: types.CallbackQuery, state: FSMContext):
    # ইউজার কোনটি সিলেক্ট করেছে তা সেভ করা
    method = "recharge" if call.data == "withdraw_recharge" else "sendmoney"
    await state.update_data(withdraw_type=method)
    
    # এটি সবচেয়ে গুরুত্বপূর্ণ: এখন বট ইউজারের কাছ থেকে টাকার পরিমাণ আশা করবে
    await BotState.waiting_for_withdraw_amount.set()
    
    await call.message.answer(
        "💵 **আপনি কত টাকা উইথড্র করতে চান?**\n"
        "পরিমাণটি সংখ্যায় লিখুন (যেমন: ১০০):",
        parse_mode="Markdown"
    )
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

    # --- ১. উইথড্র পরিমাণ গ্রহণ এবং অ্যাডমিনকে পাঠানো ---

@dp.message_handler(state=BotState.waiting_for_withdraw_amount)
async def process_withdraw_final(message: types.Message, state: FSMContext):
    # ১. ইনপুট চেক (সংখ্যা কি না এবং দশমিক থাকলে তা হ্যান্ডেল করা)
    try:
        # ইউজার যদি ৫.৭৯ লেখে, float() সেটাকে ৫.৭৯ করবে আর int() সেটাকে ৫ করে দেবে
        amount = int(float(message.text))
    except (ValueError, TypeError):
        return await message.answer("❌ অনুগ্রহ করে সঠিক সংখ্যা লিখুন (যেমন: ১০০)")

    user_id = message.from_user.id
    
    # ২. ডাটাবেস থেকে ইউজারের বর্তমান তথ্য আনা (withdraw_count এবং referred_by সহ)
    cursor.execute("SELECT balance, bkash_num, nagad_num, rocket_num, binance_id, recharge_num, withdraw_count, referred_by FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    
    if not res:
        await state.finish()
        return await message.answer("❌ ডাটাবেসে আপনার তথ্য পাওয়া যায়নি।")

    # ডাটাগুলো আলাদা করা
    balance, bkash, nagad, rocket, binance, recharge, wd_count, ref_by = res
    
    # ৩. ব্যালেন্স চেক
    if amount > int(balance):
        return await message.answer(f"❌ আপনার ব্যালেন্স পর্যাপ্ত নয়! বর্তমান: {int(balance)} ৳")
    
    if amount <= 19:
        return await message.answer("❌ সর্বনিম্ন ১ টাকা উইথড্র করা যাবে।")

    # ৪. স্টেট থেকে উইথড্র টাইপ (Recharge নাকি Send Money) নেওয়া
    data = await state.get_data()
    w_type = data.get('withdraw_type')

    # ৫. কমিশন ও পরবর্তী উইথড্র সংখ্যা হিসাব
    commission = int(amount * 0.05)
    next_wd_number = (wd_count or 0) + 1

    # ৬. ইউজারের ব্যালেন্স এবং উইথড্র সংখ্যা আপডেট করা
    new_balance = int(balance - amount)
    cursor.execute("UPDATE users SET balance = ?, withdraw_count = ? WHERE user_id = ?", (new_balance, next_wd_number, user_id))
    db.commit()

    # ৭. মেথড অনুযায়ী পেমেন্ট ডিটেইলস সাজানো (HTML ব্যবহার করা হয়েছে)
    if w_type == "recharge":
        method_details = f"📱 Recharge: <code>{recharge or 'Not Set'}</code>"
        withdraw_title = "📱 নতুন রিচার্জ রিকোয়েস্ট!"
    else:
        method_details = (
            f"🟢 bKash: <code>{bkash or 'Not Set'}</code>\n"
            f"🟠 Nagad: <code>{nagad or 'Not Set'}</code>\n"
            f"💜 Rocket: <code>{rocket or 'Not Set'}</code>\n"
            f"🟡 Binance: <code>{binance or 'Not Set'}</code>"
        )
        withdraw_title = "💸 নতুন সেন্ড মানি রিকোয়েস্ট!"

    user_name = f"@{message.from_user.username}" if message.from_user.username else "নেই"
    
    # ৮. অ্যাডমিনকে পাঠানোর জন্য মেসেজ ফরম্যাট
    admin_text = (
        f"<b>{withdraw_title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {user_name}\n"
        f"🆔 আইডি: <code>{user_id}</code>\n\n"
        f"💵 উইথড্র পরিমাণ: <b>{amount} ৳</b>\n"
        f"🎁 <b>রেফার কমিশন (৫%):</b> <code>{commission} ৳</code>\n"
        f"📊 উইথড্র সংখ্যা: <code>{next_wd_number}/10</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏠 <b>পেমেন্ট ডিটেইলস:</b>\n"
        f"{method_details}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"পেমেন্ট করে নিচের বাটনে ক্লিক করুন 👇"
    )

    # ৯. ইনলাইন কিবোর্ড তৈরি (Approve এবং Reject বাটন)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"admin_payment_approve_{user_id}_{amount}_{commission}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_payment_reject_{user_id}_{amount}")
    )

    # ১০. অ্যাডমিনকে মেসেজ পাঠানো
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="HTML")
        await message.answer("✅ আপনার উইথড্র রিকোয়েস্ট সফলভাবে জমা হয়েছে!", reply_markup=main_menu())
    except Exception as e:
        # কোনো কারণে মেসেজ না গেলে ব্যালেন্স রিফান্ড করে দেওয়া
        cursor.execute("UPDATE users SET balance = balance + ?, withdraw_count = withdraw_count - 1 WHERE user_id = ?", (amount, user_id))
        db.commit()
        await message.answer("❌ সিস্টেম এরর! অ্যাডমিনকে রিকোয়েস্ট পাঠানো যায়নি। টাকা রিফান্ড করা হয়েছে।")
    
    # ১১. সিগনিফিক্যান্ট লাইন: স্টেট ফিনিশ করা (যাতে বারবার টাকা না চায়)
    await state.finish()
    
    # ৪. এরপর অ্যাডমিনকে মেসেজ পাঠানো

# ==========================================
@dp.message_handler(commands=['check_user'], user_id=ADMIN_ID)
async def admin_check_user_details(message: types.Message):
    args = message.get_args()
    if not args.isdigit(): 
        return await message.answer("⚠️ সঠিক ইউজার আইডি দিন।\nউদাহরণ: `/check_user 12345678`", parse_mode="Markdown")
    
    user_id = int(args)
    
    # ডাটাবেস থেকে সব তথ্য আনা (পেন্ডিং ব্যালেন্স সহ)
    cursor.execute("SELECT balance, refer_balance, pending_balance, referral_count, username FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    
    if res:
        balance = res[0]
        refer_bal = res[1]
        pending_bal = res[2]
        ref_count = res[3]
        # ইউজারনেম না থাকলে বা None হলে বিকল্প টেক্সট
        db_username = res[4] if res[4] else "ইউজারনেম নেই"
        
        # HTML মোড ব্যবহার করা হয়েছে যাতে আন্ডারস্কোর (_) থাকলে মেসেজ ফেইল না হয়
        text = (
            f"👤 <b>ইউজার রিপোর্ট (ID: <code>{user_id}</code>)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>ইউজারনেম:</b> @{db_username}\n"
            f"💵 <b>মূল ব্যালেন্স:</b> {balance:.2f} ৳\n"
            f"👥 <b>রেফার ব্যালেন্স:</b> {refer_bal:.2f} ৳\n"
            f"⏳ <b>পেন্ডিং ব্যালেন্স:</b> {pending_bal:.2f} ৳\n"
            f"📊 <b>মোট রেফারেল:</b> {ref_count} জন\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer("❌ এই আইডিটি ডাটাবেসে পাওয়া যায়নি।")
        
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
@dp.message_handler(lambda message: message.text == "☎️SUPPORT")
async def support_message(message: types.Message):
    # এখানে [শব্দ](লিঙ্ক) এই ফরম্যাটে হাইপারলিঙ্ক সেট করা হয়েছে
    text = (
        "👋 **হ্যালো! আমাদের সাপোর্ট সেন্টারে আপনাকে স্বাগতম।**\n\n"
        "যেকোনো সমস্যা বা তথ্যের জন্য নিচে ক্লিক করুন:\n\n"
        "🖲️ **SUPPORT BOT** [BOT](https://t.me/instafbhubsupport_bot)\n"
        "📢 **আপডেট গ্রুপ:** [Join Channel](https://t.me/instafbhub)\n"
        "🛠 **হেল্প সাপোর্ট:** [Contact Support](https://t.me/INSTAFB_SUPPORT)\n\n"
        "✅আমরা আপনাকে দ্রুত সাহায্য করার চেষ্টা করব। ধন্যবাদ!"
    )
    
    # parse_mode="Markdown" অবশ্যই থাকতে হবে নাহলে লিঙ্ক কাজ করবে না
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

# ১. মেনু বাটন ফাংশন (নিশ্চিত করুন নামটি সঠিক)
def work_v2_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("FB 00 Fnd 2fa") 
    keyboard.add("🔄 রিফ্রেশ") 
    return keyboard

# ২. মেইন বাটন হ্যান্ডলার (v2 ওপেন করার জন্য)
@dp.message_handler(lambda message: "Work Start v2" in message.text or message.text == "💻FACEBOOK WORK")
async def work_v2_handler(message: types.Message):
    user_id = message.from_user.id 
    if await is_blocked(user_id):
        return await message.answer("❌ দুঃখিত, আপনাকে ব্লক করা হয়েছে। \n\n✅আপনি 24 hrs পরে বটটি ব্যবহার করতে পারবেন না।")
        
    text = (
        "🔴 **আপনার কাজের ক্যাটাগরি বেছে নিন:**"
    )
    await message.answer(text, reply_markup=work_v2_menu(), parse_mode="Markdown")

# ৩. ক্যাটাগরি সিলেক্ট করার হ্যান্ডলার
# ৩. ক্যাটাগরি সিলেক্ট করার হ্যান্ডলার
@dp.message_handler(lambda message: message.text in ["FB 00 Fnd 2fa"])
async def work_v2_options(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    
    # ইনলাইন কিবোর্ড তৈরি
    inline_kb = types.InlineKeyboardMarkup(row_width=2)
    
    # বাটনগুলো তৈরি করা হলো
    btn_file = types.InlineKeyboardButton("📁 File", callback_data="type_file")
    btn_single = types.InlineKeyboardButton("🆔 Single ID", callback_data="type_single")
    
    # 🛑 এই লাইনটি আপনার কোডে নেই, এটি অবশ্যই যোগ করতে হবে:
    inline_kb.add(btn_file, btn_single) 
    
    msg_text = (
        f"✅ আপনি বেছে নিয়েছেন: **{message.text}**\n"
        "━━━━━━━━━━━━━━━\n"
        "এখন কিভাবে ডাটা জমা দিতে চান? নিচের বাটন থেকে সিলেক্ট করুন।"
    )
    
    await message.answer(msg_text, reply_markup=inline_kb, parse_mode="Markdown")
            # --- ১. সিঙ্গেল আইডি বাটনে ক্লিক করলে প্রথমে UID চাইবে ---
@dp.callback_query_handler(lambda c: c.data == "type_single", state="*")
async def ask_single_uid(call: types.CallbackQuery, state: FSMContext):
    await BotState.waiting_for_single_user.set() # UID নেওয়ার স্টেট চালু
    await call.message.edit_text(
        "🆔 **অনুগ্রহ করে আপনার আইডির UID (User ID/Number) দিন:**", 
        parse_mode="Markdown"
    )
    await call.answer()

# --- ২. UID রিসিভ করে Password চাইবে ---
# --- ১. প্রথমে UID নেওয়ার পর Password চাওয়ার কোড ---
@dp.message_handler(state=BotState.waiting_for_single_user)
async def get_uid(message: types.Message, state: FSMContext):
    await state.update_data(fb_uid=message.text) # UID সেভ করা হলো
    await BotState.waiting_for_single_pass.set() # পাসওয়ার্ড চাওয়ার স্টেট
    await message.answer("🔑 **আইডির পাসওয়ার্ড (Password) দিন:**")

# --- ২. Password নেওয়ার পর 2FA চাওয়ার কোড ---
@dp.message_handler(state=BotState.waiting_for_single_pass)
async def get_pass(message: types.Message, state: FSMContext):
    await state.update_data(fb_pass=message.text) # পাসওয়ার্ড সেভ করা হলো
    await BotState.waiting_for_single_2fa.set() # 2FA চাওয়ার স্টেট
    await message.answer("🔐 **আইডির 2FA কোডটি দিন:**")

# --- ৩. সবশেষে 2FA পাওয়ার পর এডমিনের কাছে পাঠানো ---
# --- ৩. সবশেষে 2FA পাওয়ার পর এডমিনের কাছে পাঠানো ও ডাটাবেসে সেভ করা ---
@dp.message_handler(state=BotState.waiting_for_single_2fa)
async def send_to_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id # <--- এটি যোগ করা হলো
    
    # মেমোরি থেকে আগের ডাটাগুলো নেওয়া
    user_data = await state.get_data()
    uid = user_data.get('fb_uid')
    pw = user_data.get('fb_pass')
    two_fa = message.text # শেষ মেসেজটি হলো 2FA
    category = user_data.get('category', 'FB 00 Fnd 2fa')
    
    # অ্যাডমিনকে পাঠানোর মেসেজ ফরম্যাট
    admin_report = (
        f"✅ **নতুন সিঙ্গেল আইডি জমা হয়েছে!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 নাম: {message.from_user.full_name}\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"📂 ক্যাটাগরি: {category}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📌 UID: `{uid}`\n"
        f"🔑 Pass: `{pw}`\n"
        f"🔐 2FA: `{two_fa}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📝 কপি ফরম্যাট:\n`{uid}|{pw}|{two_fa}`"
    )

    try:
        # ১. অ্যাডমিনকে মেসেজ পাঠানো
        await bot.send_message(FILE_ADMIN_ID, admin_report, parse_mode="Markdown")
        
        # ২. Supabase-এ সেভ করা (যাতে /view_ids কাজ করে)
        final_category = f"{category} [✅ Single]"
        save_id_supabase(user_id=user_id, u_id=uid, u_pass=pw, two_fa=two_fa, category=final_category)
        
        # ৩. Local SQLite ডাটাবেসে সেভ করা
        import datetime
        bd_now = datetime.datetime.now() + datetime.timedelta(hours=6)
        dt_log = bd_now.strftime("%d/%m/%Y %I:%M %p") 
        cursor.execute("INSERT INTO user_id_logs (user_id, category, u_id, u_pass, two_fa, date_time) VALUES (?, ?, ?, ?, ?, ?)", 
                       (user_id, final_category, uid, pw, two_fa, dt_log))
        
        # ৪. ব্যালেন্স আপডেট করা
        id_price = 4.5 
        cursor.execute("UPDATE users SET pending_balance = pending_balance + ? WHERE user_id = ?", (id_price, user_id))
        
        # ৫. ইউজারের সিঙ্গেল আইডি কাউন্ট বাড়ানো
        today = datetime.date.today().strftime("%Y-%m-%d")
        cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (user_id, today))
        cursor.execute("UPDATE stats SET single_id_count = single_id_count + 1 WHERE user_id = ? AND date = ?", (user_id, today))
        
        db.commit()
    
        # ইউজারকে কনফার্ম করা
        await message.answer("✅ আপনার আইডিটি সফলভাবে জমা হয়েছে! অ্যাডমিন চেক করে ব্যালেন্স দিয়ে দিবে।", reply_markup=main_menu())
    except Exception as e:
        print(f"Error sending to admin: {e}")
        await message.answer("❌ কারিগরি ত্রুটির কারণে অ্যাডমিনকে জানানো যায়নি।")

    # সব শেষ হলে স্টেট ক্লিয়ার করা
    await state.finish()
    
        
        # --- ১. ফাইল বাটনে ক্লিক করলে এই হ্যান্ডলারটি কাজ করবে ---
@dp.callback_query_handler(lambda c: c.data == "type_file", state="*")
async def ask_for_file(call: types.CallbackQuery, state: FSMContext):
    await BotState.waiting_for_file.set() # ফাইল রিসিভ করার স্টেট সেট করা
    await call.message.edit_text(
        "📂 **অনুগ্রহ করে আপনার কাজের ফাইলটি (.txt বা Excel) এখানে পাঠান:**\n\n"
        "⚠️ ফাইলটি সরাসরি এই চ্যাটে আপলোড করুন।", 
        parse_mode="Markdown"
    )
    await call.answer()

# --- ২. ইউজার যখন ফাইল পাঠাবে, তখন এই হ্যান্ডলারটি সেটি রিসিভ করবে ---
@dp.message_handler(content_types=['document'], state=BotState.waiting_for_file)
async def process_uploaded_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    category = data.get('category', 'FB 00 Fnd 2fa') # কাজের ক্যাটাগরি
    
    # অ্যাডমিনকে ফাইলটি ফরোয়ার্ড করা
    caption = (
        f"📩 **নতুন ফাইল জমা পড়েছে!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 নাম: {message.from_user.full_name}\n"
        f"🔗 ইউজারনেম: @{message.from_user.username if message.from_user.username else 'N/A'}\n"
        f"🆔 ইউজার আইডি: `{message.from_user.id}`\n"
        f"📂 ক্যাটাগরি: **{category}**"
    )
    
    # অ্যাডমিনের জন্য পেমেন্ট বাটন
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Add Money 💰", callback_data=f"adminadd_{message.from_user.id}"))

    # অ্যাডমিন আইডিতে (FILE_ADMIN_ID) ফাইল পাঠানো
    try:
        await bot.send_document(FILE_ADMIN_ID, message.document.file_id, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        
        # ইউজারকে কনফার্মেশন দেওয়া
        await message.answer("✅ আপনার ফাইলটি সফলভাবে অ্যাডমিনের কাছে পাঠানো হয়েছে! চেক করে ব্যালেন্স দেওয়া হবে।", reply_markup=main_menu())
    except Exception as e:
        await message.answer("❌ ফাইল পাঠাতে সমস্যা হয়েছে। দয়া করে অ্যাডমিনকে জানান।")
        print(f"Error sending file: {e}")

    # স্টেট ক্লিয়ার করা
    await state.finish()

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
@dp.message_handler(lambda message: message.text == "🔊RULES & PRICE")
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
@dp.message_handler(lambda message: message.text == "📊MY STATUS")
async def show_user_status(message: types.Message):
    user_id = message.from_user.id
    
    # ডাটাবেস থেকে তথ্য আনা (আপনার দেওয়া কুয়েরি)
    cursor.execute("""SELECT balance, pending_balance, bkash_num, nagad_num, 
                      rocket_num, binance_id, recharge_num 
                      FROM users WHERE user_id = ?""", (user_id,))
    user_data = cursor.fetchone()
    
    if user_data:
        balance, pending_balance, bkash, nagad, rocket, binance, recharge = user_data
    else:
        balance = pending_balance = 0
        bkash = nagad = rocket = binance = recharge = None

    cursor.execute("SELECT file_count, single_id_count FROM stats WHERE user_id = ?", (user_id,))
    stats_data = cursor.fetchone()
    file_count = stats_data[0] if stats_data else 0
    single_id_count = stats_data[1] if stats_data else 0

    # মেসেজ ফরম্যাট (এখানেই শুধু পরিবর্তন করা হয়েছে যাতে 'Not Set' থাকলে 'সেট নেই' দেখায়)
    status_msg = (
        f"👤 **আপনার প্রোফাইল স্ট্যাটাস**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ইউজার আইডি:** `{user_id}`\n"
        f"💰 **মেইন ব্যালেন্স:** {balance} BDT\n"
        f"⏳ **পেন্ডিং ব্যালেন্স:** {pending_balance} BDT\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📁 **মোট ফাইল:** {file_count} টি\n"
        f"🆔 **সিঙ্গেল আইডি:** {single_id_count} টি\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 **সেভ করা পেমেন্ট মেথড:**\n"
        f"📱 রিচার্জ: `{recharge if (recharge and recharge != 'Not Set') else 'সেট নেই'}`\n"
        f"🟢 বিকাশ: `{bkash if (bkash and bkash != 'Not Set') else 'সেট নেই'}`\n"
        f"🟠 নগদ: `{nagad if (nagad and nagad != 'Not Set') else 'সেট নেই'}`\n"
        f"💜 রকেট: `{rocket if (rocket and rocket != 'Not Set') else 'সেট নেই'}`\n"
        f"🟡 বিন্যান্স: `{binance if (binance and binance != 'Not Set') else 'সেট নেই'}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"পেন্ডিং ব্যালেন্স এডমিন চেক করে মেইন ব্যালেন্সে দিয়ে দিবে। 🔥"
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
    if len(response_text) > 3500:
        # মেসেজ খুব বড় হলে পার্ট পার্ট করে পাঠানো
        for i in range(0, len(response_text), 4000):
            await message.answer(response_text[i:i+4000], parse_mode="Markdown")
    else:
        await message.answer(response_text, parse_mode="Markdown")
#==============
# --- উইথড্র অ্যাপ্রুভ এবং রিজেক্ট হ্যান্ডলার ---

@dp.callback_query_handler(lambda c: c.data.startswith('admin_payment_'), state="*")
async def process_admin_withdrawal(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("❌ আপনি অ্যাডমিন নন!", show_alert=True)

    data = call.data.split('_')
    action = data[2]  # approve অথবা reject
    user_id = int(data[3])
    amount = int(float(data[4]))

    if action == "approve":
        commission = float(data[5])
        
        # ১. রেফারার থাকলে তাকে কমিশন দেওয়া
        cursor.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
        ref_res = cursor.fetchone()
        if ref_res and ref_res[0] != 0:
            referrer_id = ref_res[0]
            cursor.execute("UPDATE users SET refer_balance = refer_balance + ? WHERE user_id = ?", (commission, referrer_id))
            try:
                await bot.send_message(referrer_id, f"🎁 আপনি রেফার কমিশন পেয়েছেন: {commission} ৳")
            except:
                pass
        
        db.commit()
        await call.message.edit_text(f"✅ ইউজার {user_id} এর {amount} ৳ উইথড্র সফলভাবে অ্যাপ্রুভ করা হয়েছে।")
        try:
            await bot.send_message(user_id, f"✅ আপনার {amount} ৳ উইথড্র রিকোয়েস্টটি অ্যাপ্রুভ করা হয়েছে।")
        except:
            pass

    elif action == "reject":
        # রিজেক্ট করলে ইউজারের ব্যালেন্স ফেরত দেওয়া
        cursor.execute("UPDATE users SET balance = balance + ?, withdraw_count = withdraw_count - 1 WHERE user_id = ?", (amount, user_id))
        db.commit()
        await call.message.edit_text(f"❌ ইউজার {user_id} এর উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে এবং টাকা ফেরত দেওয়া হয়েছে।")
        try:
            await bot.send_message(user_id, f"❌ আপনার {amount} ৳ উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে। টাকা আপনার ব্যালেন্সে ফেরত দেওয়া হয়েছে।")
        except:
            pass

    await call.answer()

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

@dp.message_handler(lambda message: message.text == "🏆LEADERBOARD")
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
@dp.message_handler(lambda message: message.text == "🎁INVITE BONUS")
async def referral_menu(message: types.Message):
    user_id = message.from_user.id
    
    # ডাটাবেস থেকে রেফার ব্যালেন্স এবং মেইন ব্যালেন্স আনা
    cursor.execute("SELECT refer_balance, balance, referral_count FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    ref_balance = res[0] if res else 0
    main_balance = res[1] if res else 0
    total_ref = res[2] if res else 0
    
    # ইনলাইন কিবোর্ড তৈরি (নতুন বাটনসহ)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💰 Add to Main Balance", callback_data="transfer_ref_request"),
        types.InlineKeyboardButton("📜 Rules", callback_data="ref_rules"),
        types.InlineKeyboardButton("📋 Refer List", callback_data="view_ref_list")
    )
    
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    
    text = (
        f"👥 **রেফারেল ড্যাশবোর্ড**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **মোট রেফারেল:** `{total_ref} জন`\n"  # <--- এখানে নতুন লাইন
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
    # এখানে REFER_TRANSFER_ENABLED বদলে REFER_ADD_ENABLED করে দেওয়া হয়েছে
    if not REFER_ADD_ENABLED:
        return await call.answer("⚠️ বর্তমানে রেফার ব্যালেন্স ট্রান্সফার অপশনটি সাময়িকভাবে বন্ধ আছে।\n 🔊⏰খোলার সময় রাত ছয়টা থেকে বারোটা পর্যন্ত", show_alert=True)
    
    user_id = call.from_user.id
    
    # ডাটাবেস থেকে ইউজারের রেফার ব্যালেন্স চেক করা
    cursor.execute("SELECT refer_balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    ref_bal = res[0] if res is not None else 0
    
    # যদি ব্যালেন্স ০ বা তার কম হয়
    if ref_bal <= 0:
        return await call.answer("⚠️ আপনার কোনো রেফার ব্যালেন্স নেই!", show_alert=True)
    
    # স্টেট সেট করা
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
# এটি টাকা রিসিভ করার হ্যান্ডলার
@dp.message_handler(state=BotState.waiting_for_transfer_amount)
async def send_transfer_request_to_admin(message: types.Message, state: FSMContext):
    # ইনপুটটি সংখ্যা কি না চেক করা
    input_text = message.text
    if not input_text.replace('.', '', 1).isdigit():
        return await message.answer("❌ অনুগ্রহ করে সঠিক সংখ্যা লিখুন (যেমন: ৫০ বা ৫০.৫)")

    amount = float(input_text)
    user_id = message.from_user.id
    
    # ডাটাবেস থেকে ইউজারের বর্তমান রেফার ব্যালেন্স চেক করা
    cursor.execute("SELECT refer_balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    current_ref_bal = res[0] if res else 0

    # চেক করা হচ্ছে ইউজারের পর্যাপ্ত ব্যালেন্স আছে কি না
    if amount > current_ref_bal:
        await state.finish() # ব্যালেন্স না থাকলে স্টেট বন্ধ করে দেওয়া ভালো
        return await message.answer(f"❌ আপনার পর্যাপ্ত রেফার ব্যালেন্স নেই!\nবর্তমান ব্যালেন্স: `{current_ref_bal:.2f} ৳`")

    if amount <= 0:
        return await message.answer("❌ সর্বনিম্ন ১ টাকা ট্রান্সফার করা যাবে।")

    # অ্যাডমিনের জন্য বাটন (ADMIN_ID আপনার ওপরে ডিফাইন করা থাকতে হবে)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Add Money", callback_data=f"ref_adm_add_{user_id}_{amount}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"ref_adm_rej_{user_id}_{amount}")
    )

    admin_text = (
        f"🔄 **নতুন ব্যালেন্স ট্রান্সফার রিকোয়েস্ট!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 নাম: {message.from_user.full_name}\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"💰 পরিমাণ: **{amount:.2f} ৳**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"অ্যাপ্রুভ করতে নিচের বাটনে ক্লিক করুন।"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="Markdown")
        await message.answer(f"✅ আপনার **{amount:.2f} ৳** ট্রান্সফার রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।\n⏳ অ্যাডমিন এপ্রুভ করলে মেইন ব্যালেন্সে যোগ হবে।")
    except Exception as e:
        await message.answer("⚠️ অ্যাডমিনকে মেসেজ পাঠানো সম্ভব হয়নি।")
    
    # কাজ শেষ হলে স্টেট ক্লিয়ার করুন
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
@dp.callback_query_handler(lambda c: c.data == 'ref_rules')
async def show_referral_rules(call: types.CallbackQuery):
    rules_text = (
        "📜 **রেফারেল সিস্টেমের নিয়মাবলী:**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "১. আপনার রেফার লিংকের মাধ্যমে নতুন কেউ জয়েন করলে সে আপনার সফল রেফার হিসেবে গণ্য হবে।\n\n"
        "২. আপনার রেফার করা মেম্বার যখন **প্রথম ১০ বার** উইথড্র করবে, প্রতিবার আপনি পেমেন্টের **৫% কমিশন** পাবেন।\n\n"
        "৩. রেফার কমিশন সরাসরি আপনার 'রেফার ব্যালেন্স'-এ জমা হবে।\n\n"
        "৪. রেফার ব্যালেন্স থেকে যেকোনো সময় টাকা 'Main Balance'-এ ট্রান্সফার করে নিতে পারবেন।\n\n"
        "৫. কোনো প্রকার ফেক রেফার বা স্প্যামিং করলে আপনার একাউন্ট পার্মানেন্টলি ব্লক করা হতে পারে।"
    )
    
    # এটি ইউজারের বর্তমান মেসেজটি পরিবর্তন করে রুলস দেখাবে
    # সাথে একটি 'Back' বাটন দিলে ইউজার আবার ড্যাশবোর্ডে ফিরতে পারবে
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="back_to_ref"))
    
    await call.message.edit_text(rules_text, reply_markup=kb, parse_mode="Markdown")
@dp.callback_query_handler(lambda c: c.data == 'back_to_ref')
async def back_to_main_menu(call: types.CallbackQuery):
    # রুলস মেসেজটি ডিলিট করে দিবে
    await call.message.delete()
    
    # ইউজারকে মেইন মেনু মেসেজ এবং বাটনগুলো পাঠিয়ে দিবে
    await call.message.answer("🏠 আপনি মেইন মেনুতে ফিরে এসেছেন। একটি অপশন বেছে নিন:", reply_markup=main_menu())
    
    # কলব্যাক অ্যানসার (যাতে লোডিং চিহ্ন চলে যায়)
    await call.answer()
@dp.callback_query_handler(lambda c: c.data == 'view_ref_list')
async def show_id_only_ref_list(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    # ডাটাবেস থেকে শুধু রেফারেলদের আইডি (user_id) খুঁজে বের করা
    cursor.execute("SELECT user_id FROM users WHERE referred_by = ?", (user_id,))
    ref_users = cursor.fetchall()
    
    # যদি কেউ এখনো কাউকে রেফার না করে থাকে
    if not ref_users:
        return await call.answer("❌ আপনার এখনো কোনো সফল রেফারেল নেই।", show_alert=True)

    text = "📋 **আপনার রেফারেল আইডি লিস্ট:**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    
    count = 1
    for ref in ref_users:
        r_id = ref[0]
        
        # প্রতিটি মেম্বারের শুধু আইডি নম্বরটি দেখাবে
        text += f"{count}. 🆔 `{r_id}`\n"
        count += 1
        
        # লিস্ট খুব বড় হয়ে গেলে ৫০ জন পর্যন্ত লিমিট রাখা ভালো
        if count > 50:
            text += "\n⚠️ *আরো অনেক মেম্বার আছে...*"
            break

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 **মোট রেফারেল:** `{len(ref_users)}` জন"

    # রেফারেল মেনুতে ফিরে যাওয়ার জন্য ব্যাক বাটন
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_to_ref"))
    
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except:
        await call.message.answer(text, reply_markup=kb, parse_mode="Markdown")
@dp.message_handler(commands=['add_user'])
async def admin_add_manual_user(message: types.Message):
    if message.from_user.id != ADMIN_ID: return # আপনার অ্যাডমিন চেক

    args = message.get_args().split()
    if len(args) < 2:
        return await message.answer("⚠️ নিয়ম: `/add_user আইডি নাম`", parse_mode="Markdown")

    new_id, name = int(args[0]), args[1]

    try:
        # নতুন ইউজারকে ডাটাবেসে ইনসার্ট করা (বাকি সব ডিফল্ট ০ থাকবে)
        sql = "INSERT INTO users (user_id, username, balance, referral_count, referred_by, refer_balance, withdraw_count) VALUES (?, ?, ?, ?, ?, ?, ?)"
        cursor.execute(sql, (new_id, name, 0.0, 0, 0, 0.0, 0))
        db.commit()
        await message.answer(f"✅ সফলভাবে নতুন ইউজার অ্যাড হয়েছে!\n🆔 আইডি: `{new_id}`\n📛 নাম: `{name}`")
    except Exception as e:
        await message.answer(f"❌ এরর: এই আইডিটি অলরেডি ডাটাবেসে থাকতে পারে।")
@dp.message_handler(commands=['set_referrer'])
async def admin_edit_referrer(message: types.Message):
    if message.from_user.id != ADMIN_ID: return

    args = message.get_args().split()
    if len(args) < 2:
        return await message.answer("⚠️ নিয়ম: `/set_referrer ইউজারের_আইডি রেফারারের_আইডি`", parse_mode="Markdown")

    target_id, new_ref_id = int(args[0]), int(args[1])

    # ইউজারের রেফারার আপডেট করা
    cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (new_ref_id, target_id))
    db.commit()
    
    await message.answer(f"✅ আপডেট সফল!\n👤 ইউজার `{target_id}` এখন থেকে 🤝 `{new_ref_id}` এর রেফারেল হিসেবে গণ্য হবে।")
@dp.message_handler(commands=['set_ref_bal'])
async def set_user_refer_balance_with_notify(message: types.Message):
    # আপনার অ্যাডমিন চেক (নিশ্চিত করুন ADMIN_ID আপনার কোডে ডিফাইন করা আছে)
    if message.from_user.id != ADMIN_ID: 
        return

    # কমান্ড থেকে আইডি এবং নতুন ব্যালেন্স নেওয়া (উদাহরণ: /set_ref_bal 12345 500)
    args = message.get_args().split()
    if len(args) < 2:
        return await message.answer("⚠️ সঠিক নিয়ম: `/set_ref_bal ইউজার_আইডি নতুন_টাকা`", parse_mode="Markdown")

    try:
        target_id = int(args[0])
        new_bal = float(args[1])
        
        # ১. ডাটাবেসে রেফারেল ব্যালেন্স আপডেট করা
        cursor.execute("UPDATE users SET refer_balance = ? WHERE user_id = ?", (new_bal, target_id))
        db.commit()
        
        # ২. অ্যাডমিনকে কনফার্মেশন মেসেজ দেওয়া
        await message.answer(f"✅ ইউজার `{target_id}` এর রেফার ব্যালেন্স আপডেট করে `{new_bal:.2f} ৳` করা হয়েছে।")

        # ৩. ইউজারের কাছে অটোমেটিক মেসেজ পাঠানো
        notification_text = (
            f"🔔 **ব্যালেন্স আপডেট নোটিশ!**\n\n"
            f"অ্যাডমিন আপনার রেফারেল ব্যালেন্স আপডেট করেছেন।\n"
            f"💰 **আপনার বর্তমান রেফার ব্যালেন্স:** `{new_bal:.2f} ৳`"
        )
        
        try:
            await bot.send_message(target_id, notification_text, parse_mode="Markdown")
        except Exception as e:
            # যদি ইউজার বট ব্লক করে রাখে বা আইডি ভুল হয়
            await message.answer(f"⚠️ ব্যালেন্স আপডেট হয়েছে, কিন্তু ইউজারকে মেসেজ পাঠানো যায়নি (বট ব্লক থাকতে পারে)।")

    except ValueError:
        await message.answer("❌ ভুল ফরম্যাট! আইডি এবং টাকা সঠিকভাবে দিন।")
    except Exception as e:
        await message.answer(f"❌ একটি এরর হয়েছে: {str(e)}")
        # ==========================================
# ==========================================
# সব ইউজারের জন্য প্রোফাইল লিঙ্ক দেখার কমান্ড
# ==========================================
@dp.message_handler(commands=['users'], user_id=ADMIN_ID)
async def list_all_users(message: types.Message):
    try:
        # ডাটাবেস থেকে শুধু আইডি নিয়ে আসা
        cursor.execute("SELECT user_id FROM users")
        all_users = cursor.fetchall()

        if not all_users:
            return await message.answer("<b>⚠️ ডাটাবেসে কোনো ইউজার পাওয়া যায়নি।</b>", parse_mode="HTML")

        response_text = "<b>📊 বটের ইউজার তালিকা:</b>\n\n"
        
        for index, user in enumerate(all_users, start=1):
            u_id = user[0]

            # ইউজারনেম থাকুক বা না থাকুক, এই লিঙ্কটি ১০০% কাজ করবে
            # 'View Profile' এ ক্লিক করলে সরাসরি আইডিতে নিয়ে যাবে
            user_info = f"{index}. <a href='tg://user?id={u_id}'>View Profile</a> | ID: <code>{u_id}</code>\n"
            
            # মেসেজ লিমিট চেক (৩০০০ ক্যারেক্টারের বেশি হলে নতুন মেসেজ পাঠাবে)
            if len(response_text) + len(user_info) > 3500:
                await message.answer(response_text, parse_mode="HTML")
                response_text = "<b>📊 তালিকা (বাকি অংশ):</b>\n\n"
            
            response_text += user_info

        await message.answer(response_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ সমস্যা হয়েছে: {str(e)}")
    # ==========================================
# '✅ জয়েন করেছি' বাটনের হ্যান্ডলার (নিরাপদ ভার্সন)
# ==========================================
@dp.callback_query_handler(text="check_join", state="*")
async def process_check_join(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        
        # আবার চেক করা হচ্ছে ইউজার গ্রুপে জয়েন করেছে কি না
        is_member = await check_joined(user_id)
        
        if is_member:
            # সুন্দর সাকসেস মেসেজ (অ্যালার্ট হিসেবে দেখাবে)
            await callback_query.answer(
                "✨ অভিনন্দন! আপনি সফলভাবে আমাদের গ্রুপে যোগ দিয়েছেন। এখন আপনি বটটি ব্যবহার করতে পারবেন।", 
                show_alert=True
            )
            
            # আগের "জয়েন করুন" মেসেজটি মুছে ফেলা হবে
            await callback_query.message.delete()
            
            # ইউজারকে মেইন মেনুতে নিয়ে যাওয়ার জন্য স্টার্ট ফাংশনটি কল করা
            await start(callback_query.message, state)
            
        else:
            # জয়েন না করলে লাল চিহ্নে সুন্দর সতর্কবার্তা
            await callback_query.answer(
                "⚠️ আপনি এখনো আমাদের গ্রুপে জয়েন করেননি!\n\nদয়া করে প্রথমে গ্রুপে জয়েন করুন, তারপর এই বাটনে আবার ক্লিক করুন।", 
                show_alert=True
            )
            
    except Exception as e:
        # কোনো যান্ত্রিক ত্রুটি হলে বট বন্ধ হবে না, শুধু আপনাকে ছোট করে জানাবে
        await callback_query.answer(f"❌ একটি ত্রুটি হয়েছে: {str(e)}", show_alert=False)
import io

# --- অ্যাডমিন কমান্ড: প্রোফাইল লিঙ্ক ও সব পেমেন্ট মেথডসহ রিপোর্ট ---
@dp.message_handler(commands=['getusers'], user_id=ADMIN_ID)
async def export_users_txt(message: types.Message):
    try:
        # ডাটাবেস থেকে প্রয়োজনীয় সব কলাম সিরিয়াল অনুযায়ী আনা হচ্ছে
        cursor.execute("""
            SELECT user_id, balance, referral_count, bkash_num, nagad_num, recharge_num 
            FROM users 
            ORDER BY rowid ASC
        """)
        users = cursor.fetchall()
        
        if not users:
            return await message.answer("❌ ডাটাবেসে কোনো ইউজার পাওয়া যায়নি!")

        # টেক্সট ফাইলের হেডার তৈরি
        output = "--- ইউজার রিপোর্ট (প্রোফাইল লিঙ্ক ও পেমেন্ট মেথডসহ) ---\n"
        output += f"মোট ইউজার সংখ্যা: {len(users)}\n"
        output += "--------------------------------------------------------------------------------------------------------------------------------------------\n"
        output += f"{'SL':<5} | {'User ID':<12} | {'Balance':<10} | {'Refer':<7} | {'Profile Link':<30} | {'bKash':<13} | {'Nagad':<13} | {'Recharge'}\n"
        output += "--------------------------------------------------------------------------------------------------------------------------------------------\n"
        
        serial = 1
        for user in users:
            u_id, balance, referrals, bkash, nagad, recharge = user
            
            # প্রোফাইল লিঙ্ক (ব্রাউজার ও টেলিগ্রাম উভয় জায়গায় কাজ করার জন্য)
            chat_link = f"https://t.me/{u_id}" 
            
            # পেমেন্ট তথ্য না থাকলে 'None' দেখাবে
            b_num = bkash if bkash else "None"
            n_num = nagad if nagad else "None"
            r_num = recharge if recharge else "None"
            
            # প্রতিটি লাইন সুন্দরভাবে সাজানো
            output += f"{serial:<5} | {u_id:<12} | {balance:<10.2f} | {referrals:<7} | {chat_link:<30} | {b_num:<13} | {n_num:<13} | {r_num}\n"
            serial += 1

        output += "--------------------------------------------------------------------------------------------------------------------------------------------\n"
        output += "রিপোর্ট জেনারেট হয়েছে: আপনার বটের সিকিউর অ্যাডমিন প্যানেল"

        # মেমোরিতে ফাইলটি তৈরি করা
        buf = io.BytesIO(output.encode('utf-8'))
        buf.name = "user_payment_details.txt"

        # অ্যাডমিনকে ফাইলটি পাঠিয়ে দেওয়া
        await bot.send_document(
            message.chat.id, 
            buf, 
            caption=f"✅ সফলভাবে {len(users)} জন ইউজারের পূর্ণাঙ্গ রিপোর্ট তৈরি করা হয়েছে।\n\n"
                    f"এই ফাইলে ইউজারদের ব্যালেন্স, প্রোফাইল লিঙ্ক এবং সেভ করা পেমেন্ট নম্বরগুলো সিরিয়াল অনুযায়ী আছে।"
        )
        
    except Exception as e:
        await message.answer(f"❌ ডাটা এক্সপোর্ট করতে সমস্যা হয়েছে: {str(e)}")
@dp.message_handler(commands=['withdraw_status'], user_id=ADMIN_ID)
async def toggle_withdraw(message: types.Message):
    global WITHDRAW_ENABLED
    command = message.get_args().lower()
    
    if command == "on":
        WITHDRAW_ENABLED = True
        await message.answer("✅ উইথড্র সিস্টেম এখন চালু করা হয়েছে।")
    elif command == "off":
        WITHDRAW_ENABLED = False
        await message.answer("❌ উইথড্র সিস্টেম এখন বন্ধ করা হয়েছে।")
    else:
        status = "চালু" if WITHDRAW_ENABLED else "বন্ধ"
        await message.answer(f"বর্তমান অবস্থা: {status}\n\nবন্ধ করতে লিখুন: `/withdraw_status off` \nচালু করতে লিখুন: `/withdraw_status on`", parse_mode="Markdown")
@dp.message_handler(commands=['refer_system'], user_id=ADMIN_ID)
async def toggle_refer_system(message: types.Message):
    global REFER_TRANSFER_ENABLED
    command = message.get_args().lower()
    
    if command == "on":
        REFER_TRANSFER_ENABLED = True
        await message.answer("✅ রেফার ট্রান্সফার সিস্টেম চালু করা হয়েছে।")
    elif command == "off":
        REFER_TRANSFER_ENABLED = False
        await message.answer("❌ রেফার ট্রান্সফার সিস্টেম বন্ধ করা হয়েছে।")
    else:
        status = "চালু" if REFER_TRANSFER_ENABLED else "বন্ধ"
        await message.answer(f"বর্তমান অবস্থা: {status}\n\nবন্ধ করতে: `/refer_system off` \nচালু করতে: `/refer_system on`")
@dp.message_handler(commands=['work_status'], user_id=ADMIN_ID)
async def toggle_work(message: types.Message):
    global IG_MOTHER_ENABLED, IG_2FA_ENABLED, IG_COOKIES_ENABLED
    args = message.get_args().split()
    
    if len(args) < 2:
        return await message.answer("⚠️ ফরম্যাট: `/work_status mother off` বা `/work_status 2fa on` ইত্যাদি।")

    work_type = args[0].lower()
    status = args[1].lower()
    
    # অন/অফ লজিক
    is_on = True if status == "on" else False
    status_text = "চালু" if is_on else "বন্ধ"

    if work_type == "mother":
        IG_MOTHER_ENABLED = is_on
        await message.answer(f"✅ IG Mother Account কাজ এখন {status_text}।")
    elif work_type == "2fa":
        IG_2FA_ENABLED = is_on
        await message.answer(f"✅ IG 2fa কাজ এখন {status_text}।")
    elif work_type == "cookies":
        IG_COOKIES_ENABLED = is_on
        await message.answer(f"✅ IG Cookies কাজ এখন {status_text}।")
    else:
        await message.answer("❌ ভুল কাজের নাম! সঠিক নাম: `mother`, `2fa`, বা `cookies`।")
@dp.message_handler(commands=['edit_pending'], user_id=ADMIN_ID)
async def edit_pending_balance(message: types.Message):
    args = message.get_args().split()
    
    if len(args) < 2:
        return await message.answer("❌ ভুল ফরম্যাট! এভাবে লিখুন:\n`/edit_pending [ইউজার_আইডি] [টাকার_পরিমাণ]`", parse_mode="Markdown")

    target_user_id = args[0]
    try:
        new_pending_amount = float(args[1])
    except ValueError:
        return await message.answer("❌ টাকার পরিমাণ অবশ্যই সংখ্যা হতে হবে।")

    # ডাটাবেসে আপডেট করা
    cursor.execute("UPDATE users SET pending_balance = ? WHERE user_id = ?", (new_pending_amount, target_user_id))
    db.commit()

    if cursor.rowcount > 0:
        await message.answer(f"✅ ইউজার `{target_user_id}` এর পেন্ডিং ব্যালেন্স আপডেট করে `{new_pending_amount}` BDT করা হয়েছে।", parse_mode="Markdown")
        
        # ইউজারকে নোটিফিকেশন পাঠানো (অপশনাল)
        try:
            await bot.send_message(target_user_id, f"🔔 আপনার পেন্ডিং ব্যালেন্স আপডেট করা হয়েছে। নতুন পেন্ডিং ব্যালেন্স: {new_pending_amount} BDT")
        except:
            pass
    else:
        await message.answer("❌ এই ইউজার আইডিটি ডাটাবেসে পাওয়া যায়নি।")
import io
@dp.message_handler(commands=['view_ids'], user_id=ADMIN_ID)
async def view_user_ids_html(message: types.Message):
    args = message.get_args()
    if not args: 
        return await message.answer("❌ সঠিক নিয়ম: `/view_ids [ইউজার_আইডি]`")

    # ১. Supabase থেকে ডাটাবেস কোয়েরি (সুপার ফাস্ট এবং নিরাপদ)
    try:
        # Supabase থেকে ডাটা আনা হচ্ছে
        res = supabase.table("user_id_logs").select("category, u_id, u_pass, two_fa, date_time").eq("user_id", str(args)).execute()
        
        # আপনার আগের HTML ডিজাইনের সাথে মিল রাখার জন্য ডাটা সাজিয়ে নেওয়া
        rows = [(d.get('category'), d.get('u_id'), d.get('u_pass'), d.get('two_fa'), d.get('date_time')) for d in res.data]
        
    except Exception as e:
        return await message.answer(f"❌ ডাটাবেস কানেকশন এরর: {str(e)}")

    if not rows: 
        return await message.answer(f"❌ এই আইডিতে কোনো ডাটা পাওয়া যায়নি।")

    # --- এর নিচের ২, ৩, ৪ নম্বর ধাপের HTML কোড আগের মতোই থাকবে, সেখানে কিছু ধরতে হবে না ---
    
    # ২. HTML স্টার্ট পার্ট (ডিজাইন অপরিবর্তিত)
    html_parts = [f"""<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>
        body{{font-family:sans-serif;background:#f4f4f9;padding:5px}}
        .b{{background:#fff;border-radius:8px;box-shadow:0 2px 5px #0002;margin-bottom:20px;overflow:auto;border:1px solid #ddd}}
        .t{{background:#333;color:#fff;padding:10px;font-weight:700}}
        .g{{display:flex;gap:5px;padding:8px;background:#eee}}
        .btn{{background:#ff9800;color:#fff;border:none;padding:6px 10px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:700}}
        table{{width:100%;border-collapse:collapse;min-width:500px}}
        th,td{{border:1px solid #eee;padding:8px;text-align:left;font-size:12px}}
        th{{background:#f8f8f8}}
        .toast{{visibility:hidden;background:#4CAF50;color:#fff;text-align:center;padding:8px;position:fixed;bottom:20px;left:50%;transform:translateX(-50%);border-radius:5px}}
        .show{{visibility:visible;animation:f 2s}}@keyframes f{{0%,100%{{opacity:0}}20%,80%{{opacity:1}}}}
    </style>
    <script>
        function cp(c){{
            let d="";const el=document.getElementsByClassName(c);
            if(el.length === 0) return;
            for(let e of el) d += e.innerText + "\\n";
            const t=document.createElement('textarea');
            t.value=d.trim();document.body.appendChild(t);t.select();
            document.execCommand('copy');document.body.removeChild(t);
            const x=document.getElementById("s");
            x.className="toast show";setTimeout(()=>{{x.className="toast"}},2000);
        }}
    </script></head><body><h3>Report ID: {args}</h3><div id="s" class="toast">কপি হয়েছে! ✅</div>"""]

    # ৩. ডাটা প্রসেসিং (NoneType Safety)
    cat_groups = {}
    for r in rows:
        # যদি ক্যাটাগরি না থাকে তবে 'Unknown' দেখাবে
        cat_name = str(r[0]) if r[0] is not None else "General"
        cat_groups.setdefault(cat_name, []).append(r)

    for cat, items in cat_groups.items():
        # ৪. কপি বাটন যাতে নষ্ট না হয় (Unique ID জেনারেশন)
        import hashlib
        s_cat = hashlib.md5(cat.encode()).hexdigest()[:8]
        
        content = f"""<div class='b'><div class='t'>{cat} ({len(items)})</div>
        <div class='g'>
            <button class='btn' onclick="cp('u-{s_cat}')">Usernames</button>
            <button class='btn' onclick="cp('p-{s_cat}')">Passwords</button>
            <button class='btn' onclick="cp('t-{s_cat}')">2FA</button>
        </div>
        <table><tr><th>No</th><th>User</th><th>Pass</th><th>2FA</th><th>Time</th></tr>"""
        
        for i, item in enumerate(items, 1):
            # ৫. প্রতিটি ভ্যালু চেক করা (যাতে কোনো চিহ্ন বা খালি ঘর থাকলে ক্র্যাশ না করে)
            u_id = str(item[1]) if item[1] else "-"
            u_pass = str(item[2]) if item[2] else "-"
            u_2fa = str(item[3]) if item[3] else "-"
            u_time = str(item[4]) if item[4] else "-"
            
            content += f"<tr><td>{i}</td><td class='u-{s_cat}'>{u_id}</td><td class='p-{s_cat}'>{u_pass}</td><td class='t-{s_cat}'>{u_2fa}</td><td style='color:#888'>{u_time}</td></tr>"
        
        content += "</table></div>"
        html_parts.append(content)

    html_parts.append("</body></html>")
    
    # ৬. সুপার ফাস্ট টেক্সট জয়েনিং
        # ৬. সুপার ফাস্ট টেক্সট জয়েনিং
    full_html = "".join(html_parts)
    
    try:
        file_data = io.BytesIO(full_html.encode('utf-8'))
        
        # Aiogram এর InputFile মেথড ব্যবহার করে ফাইল পাঠানো
        html_doc = types.InputFile(file_data, filename=f"Report_{args}.html")
        await message.reply_document(html_doc, caption=f"📊 `{args}` এর রিপোর্ট জেনারেট হয়েছে।")
        
    except Exception as e:
        await message.answer(f"❌ ফাইল সেন্ডিং এরর: {str(e)}")
        
@dp.message_handler(commands=['del_user_data'], user_id=ADMIN_ID)
async def delete_user_all_ids(message: types.Message):
    # কমান্ডটি হবে: /del_user_data [ইউজার_আইডি]
    target_user = message.get_args()
    
    if not target_user:
        return await message.answer("❌ সঠিক নিয়ম: `/del_user_data [ইউজার_আইডি]`")
    
    # প্রথমে চেক করে নিচ্ছি ওই ইউজারের আসলে কয়টি আইডি আছে
    cursor.execute("SELECT COUNT(*) FROM user_id_logs WHERE user_id = ?", (target_user,))
    total_ids = cursor.fetchone()[0]
    
    if total_ids == 0:
        return await message.answer(f"❌ ইউজার `{target_user}` এর কোনো ডাটা পাওয়া যায়নি।")
    
    # এখন ওই ইউজারের সব ডাটা ডিলিট করা হচ্ছে
    cursor.execute("DELETE FROM user_id_logs WHERE user_id = ?", (target_user,))
    db.commit()
    
    # ডাটাবেজ ফাইল থেকে ডিলিট করা ডাটার জায়গা খালি করা (VACUUM)
    cursor.execute("VACUUM")
    db.commit()

    await message.answer(f"✅ ইউজার `{target_user}` এর পাঠানো সকল ({total_ids} টি) আইডি ডাটাবেজ থেকে মুছে ফেলা হয়েছে।")
@dp.message_handler(commands=['clear_today'], user_id=ADMIN_ID)
async def clear_everything(message: types.Message):
    # ১. ডাটাবেসের সব রো ডিলিট করা
    cursor.execute("DELETE FROM user_id_logs")
    
    # ২. ডাটাবেস ফাইলটি রি-অর্গানাইজ করে সাইজ কমিয়ে ফেলা (খুবই জরুরি)
    cursor.execute("VACUUM")
    
    db.commit()
    
    await message.answer("♻️ **আজকের সব ডাটা সফলভাবে মুছে ফেলা হয়েছে!**\nআপনার ডাটাবেস এখন একদম খালি এবং ফাস্ট।")
@dp.message_handler(commands=['admin_stats'], user_id=ADMIN_ID)
async def get_overall_stats(message: types.Message):
    # ১. ডাটাবেসে মোট কতটি আইডি বা ডাটা জমা হয়েছে (Total Count)
    cursor.execute("SELECT COUNT(*) FROM user_id_logs")
    total_submissions = cursor.fetchone()[0]

    # ২. ক্যাটাগরি অনুযায়ী আলাদা আলাদা সংখ্যা (সিঙ্গেল আইডি বা ফাইল আলাদা দেখাবে)
    cursor.execute("SELECT category, COUNT(*) FROM user_id_logs GROUP BY category")
    category_data = cursor.fetchall()
    
    # ৩. বটের সকল ইউজারের মোট ব্যালেন্স
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0.0
    
    # ৪. সুন্দরভাবে মেসেজ সাজানো
    status_msg = "📊 **বটের সামগ্রিক পরিসংখ্যান**\n\n"
    status_msg += f"✅ **মোট জমানো ডাটা:** `{total_submissions}` টি\n"
    status_msg += "━━━━━━━━━━━━━━━━━━━━\n"
    
    if category_data:
        status_msg += "📂 **ক্যাটাগরি ভিত্তিক রিপোর্ট:**\n"
        for cat, count in category_data:
            # এখানে আপনার ক্যাটাগরির নাম অনুযায়ী 'Single' বা 'File' আলাদাভাবে দেখাবে
            status_msg += f"• {cat}: `{count}` টি\n"
    else:
        status_msg += "❌ এখনো কোনো আইডি বা ফাইল জমা পড়েনি।\n"
        
    status_msg += "━━━━━━━━━━━━━━━━━━━━\n"
    status_msg += f"💰 **বটের মোট ব্যালেন্স:** `{total_balance:.2f}` টাকা\n"
    status_msg += "*(সব ইউজারের ওয়ালেটে থাকা মোট টাকা)*"

    await message.answer(status_msg, parse_mode="Markdown")
   # ==========================================
# ৪. নতুন অ্যাডমিন প্যানেল কমান্ডসমূহ
# ==========================================

# ১. ইউজারের পেমেন্ট মেথড চেক করার কমান্ড
@dp.message_handler(commands=['check_payment'], user_id=ADMIN_ID)
async def admin_check_payment(message: types.Message):
    args = message.get_args()
    if not args.isdigit(): 
        return await message.answer("⚠️ আইডি দিন। উদাহরণ: `/check_payment 12345`", parse_mode="Markdown")
    
    cursor.execute("SELECT bkash_num, nagad_num, rocket_num, recharge_num, binance_id FROM users WHERE user_id=?", (int(args),))
    res = cursor.fetchone()
    if res:
        text = (f"💳 **ইউজার পেমেন্ট ইনফো (ID: {args})**\n\n"
                f"📱 রিচার্জ: `{res[3] or 'নেই'}`\n🟢 বিকাশ: `{res[0] or 'নেই'}`\n"
                f"🟠 নগদ: `{res[1] or 'নেই'}`\n💜 রকেট: `{res[2] or 'নেই'}`\n🟡 বিন্যান্স: `{res[4] or 'নেই'}`")
        await message.answer(text, parse_mode="Markdown")
    else:
        await message.answer("❌ এই আইডির কোনো ইউজার পাওয়া যায়নি।")

# ২. ইউজারের মেইন, রেফার এবং পেন্ডিং ব্যালেন্স চেক (দশমিক ছাড়া)
@dp.message_handler(commands=['check_balance'], user_id=ADMIN_ID)
async def admin_check_balance(message: types.Message):
    args = message.get_args()
    if not args.isdigit(): 
        return await message.answer("⚠️ আইডি দিন।", parse_mode="Markdown")
    
    cursor.execute("SELECT balance, refer_balance, pending_balance FROM users WHERE user_id=?", (int(args),))
    res = cursor.fetchone()
    if res:
        # ব্যালেন্স দেখানোর সময় int() ব্যবহার করা হয়েছে যাতে দশমিক না আসে
        await message.answer(f"💰 **ব্যালেন্স রিপোর্ট (ID: {args})**\n\n"
                             f"💵 মূল ব্যালেন্স: `{int(res[0])} ৳`\n"
                             f"👥 রেফার ব্যালেন্স: `{int(res[1])} ৳`\n"
                             f"⏳ পেন্ডিং ব্যালেন্স: `{int(res[2])} ৳`", parse_mode="Markdown")
    else:
        await message.answer("❌ ইউজার পাওয়া যায়নি।")

# ৩. ইউজারের মোট সফল রেফারেল সংখ্যা দেখার কমান্ড
@dp.message_handler(commands=['check_refer'], user_id=ADMIN_ID)
async def admin_check_referral(message: types.Message):
    args = message.get_args()
    if not args.isdigit(): 
        return await message.answer("⚠️ আইডি দিন।", parse_mode="Markdown")
    
    cursor.execute("SELECT referral_count FROM users WHERE user_id=?", (int(args),))
    res = cursor.fetchone()
    if res:
        await message.answer(f"👤 **ID:** `{args}`\n👥 **মোট সফল রেফার:** `{res[0]}` জন", parse_mode="Markdown")
    else:
        await message.answer("❌ ইউজার পাওয়া যায়নি।")
# এটি ফাইলের শেষে যোগ করুন
@dp.callback_query_handler(lambda c: c.data == 'add_to_main')
async def process_add_to_main(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    # ডাটাবেস থেকে ইউজারের বর্তমান রেফার ব্যালেন্স কত আছে তা দেখা
    cursor.execute("SELECT refer_balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    
    # সুইচটি অন আছে কিনা চেক করা (উপরে আপনার দেওয়া REFER_ADD_ENABLED = True)
    if not REFER_ADD_ENABLED:
        return await bot.answer_callback_query(callback_query.id, text="❌ এই সুবিধাটি বর্তমানে বন্ধ আছে।", show_alert=True)

    if result and result[0] > 0:
        amount = int(result[0])
        
        # ১. মেইন ব্যালেন্সে (balance) টাকা যোগ করা 
        # ২. রেফার ব্যালেন্স (refer_balance) ০ করে দেওয়া
        cursor.execute("UPDATE users SET balance = balance + ?, refer_balance = 0 WHERE user_id = ?", (amount, user_id))
        db.commit()
        
        # সফল হওয়ার নোটিফিকেশন দেখানো
        await bot.answer_callback_query(callback_query.id, text=f"✅ সফল! {amount} ৳ মেইন ব্যালেন্সে যোগ হয়েছে।", show_alert=True)
        
        # আগের মেসেজটি এডিট করে আপডেট ব্যালেন্স দেখানো
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=callback_query.message.message_id,
            text=f"✅ আপনার {amount} ৳ সফলভাবে মেইন ব্যালেন্সে যোগ করা হয়েছে।\n\nএখন আপনার রেফার ব্যালেন্স: 0 ৳",
            reply_markup=None # কাজ শেষ হলে বাটন সরিয়ে ফেলা
        )
    else:
        # ব্যালেন্স ০ থাকলে এই মেসেজ আসবে
        await bot.answer_callback_query(callback_query.id, text="❌ আপনার রেফার ব্যালেন্সে কোনো টাকা নেই।", show_alert=True)
    
if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
