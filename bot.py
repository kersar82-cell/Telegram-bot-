import logging
import sqlite3
import os
import random
import string
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

app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def generate_numeric_id():
    # এটি ১১১,১১১ থেকে ৯৯,৯৯৯,৯৯৯ এর মধ্যে একটি বড় সংখ্যা তৈরি করবে
    return str(random.randint(111111, 99999999))
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

cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, address TEXT)''')
db.commit()
cursor.execute('''ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0''')
db.commit()
cursor.execute('''CREATE TABLE IF NOT EXISTS teams 
                  (team_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   team_name TEXT, 
                   leader_id INTEGER, 
                   daily_target INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS team_members 
                  (user_id INTEGER PRIMARY KEY, team_id INTEGER)''')
db.commit()

class BotState(StatesGroup):
    waiting_for_file = State()
    waiting_for_address = State()
    waiting_for_withdraw_amount = State()
    waiting_for_add_money = State()
    waiting_for_single_user = State()
    waiting_for_single_pass = State()
    waiting_for_single_2fa = State()
    waiting_for_block_reason = State() 
    waiting_for_target_id = State()
    waiting_for_admin_msg = State()
    waiting_for_team_name = State()
    waiting_for_referrer_info = State() # এটি নতুন যোগ করু
    waiting_for_team_name = State()   # টিমের নাম নেওয়ার জন্য
    waiting_for_team_target = State() # ডেইলি টার্গেট নেওয়ার জন্য (এটি নতুন যোগ করুন)
    
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # প্রথম সারি: দুই ধরণের কাজের বাটন
    keyboard.row("Work start 🔥", "🔥Work Start v2")
    # দ্বিতীয় সারি: টাকা তোলা এবং রেফারেল
    keyboard.row("💴Withdraw", "👥 Referral")
    # তৃতীয় সারি: সাপোর্ট এবং রুলস
    keyboard.row("🧑‍💻Support", "🔴Rules & Price")
    keyboard.row("👥 Team Work")
    return keyboard
    
# /start কমান্ডে মেইন মেনু ও ফ্রী ফায়ার বাটন
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish() 
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    db.commit()

    # ১. এখানে বাটন তৈরি হচ্ছে
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb = types.InlineKeyboardMarkup(row_width=2) # row_width=1
    # নিচের লাইনে 'url' এর জায়গায় আপনার গ্রুপের লিংক বসান 
    help_button = types.InlineKeyboardButton(text="🆘 Contact Support", url="https://t.me/instafbhub_support") 
    inline_kb.add(help_button)
    # ২. এখানে আপনার মেসেজটি লিখুন (লাইন ব্রেক বা ইন্টার দিতে \n ব্যবহার করুন)
        # ২. এখানে আপনার বড় মেসেজটি (রেট লিস্ট) বসাবেন
    welcome_text = """📢 আজকের কাজের আপডেট এবং রেট লিস্ট 📢
📌 Instagram 00 Follower (2FA): ২.৩০ ৳
📌 Instagram Cookies: ৩.৯০ ৳
📌 Instagram Mother: ৭ ৳
📌 Facebook FBc00Fnd: ৫.৮০ ৳

  Support: @Dinanhaji"""

    # ৩. মেসেজ পাঠানো (বাটনসহ এবং parse_mode যোগ করে)
    await message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    
    # ৪. মেইন মেনু দেখানো
    await message.answer("✅Instagram 2fa &\n Mother ACCOUNT ↓↓\n 🔥Work Start\n\n🟢 Instagram cookies &\n FB 00 Fnd 2fa↓↓\n🔥WorkStart v2", reply_markup=main_menu())
    
# ১. মেইন ওয়ার্ক স্টার্ট হ্যান্ডলার
@dp.message_handler(lambda message: message.text == "Work start 🔥", state="*")
async def work_start(message: types.Message, state: FSMContext):
    await state.finish() # সব স্টেট ক্লিয়ার করে কাজ শুরু করা
    
    # ইউজার ব্লক কি না চেক
    cursor.execute("SELECT user_id FROM blacklist WHERE user_id=?", (message.from_user.id,))
    if cursor.fetchone():
        return await message.answer("❌ দুঃখিত, আপনি ব্লকড!\nএডমিনের সাথে কথা বলুন 👍")
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("IG Mother Account", "IG 2fa")
    keyboard.row("🔄 রিফ্রেশ") 
    
    msg = """Nord VPN 🫱
    🤩Mail: `3tx0zztil1@xkxkud.com`
    Pass: `RJR83@RdFr2@`

    🤩Mail: `377guy1zb4@dollicons.com`
    Pass: `RJR83@RdFr2@`

    🤩Mail: `icufc65r6j@dollicons.com`
    Pass: `RJR83@RdFr2@`
    
    👍 যেকোনো সমস্যায়: @Dinanhaji !
    🔴 আপনার কাজের ক্যাটাগরি বেছে নিন:"""
    
    await message.answer(msg, reply_markup=keyboard, parse_mode="Markdown")

# ২. ক্যাটাগরি সিলেক্ট করার হ্যান্ডলার (এটি আগেরটির ঠিক নিচে থাকবে)
@dp.message_handler(lambda message: message.text in ["IG Mother Account", "IG 2fa"], state="*")
async def ask_work_type(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    
    inline_kb = types.InlineKeyboardMarkup(row_width=2)
    inline_kb.add(
        types.InlineKeyboardButton("🗃️ File", callback_data="type_file"),
        types.InlineKeyboardButton("👤 Single ID", callback_data="type_single")
    )
    await message.answer(f"✅ আপনি **{message.text}** বেছে নিয়েছেন।\nআপনার কাজের ধরণ বেছে নিন:", reply_markup=inline_kb, parse_mode="Markdown")
    
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
    today = datetime.date.today().strftime("%Y-%m-%d")
    cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
    cursor.execute("UPDATE stats SET single_id_count = single_id_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))

    category = data.get('category')
    amount_to_add = 0

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
    await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
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

    await bot.send_document(ADMIN_ID, message.document.file_id, 
                           caption=caption, 
                           reply_markup=keyboard, 
                           parse_mode="Markdown")
    
    await message.answer("✅ আপনার ফাইলটি জমা হয়েছে। \n🔥এডমিন চেক করে ব্যালেন্স এড করে দিবে।")
    await state.finish()


# ==========================================
# ৩. উইথড্র ও পেমেন্ট মেথড চেঞ্জ লজিক
# ==========================================
@dp.message_handler(lambda message: message.text == "💴Withdraw")
async def withdraw_process(message: types.Message):
    cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    balance, address = res[0], res[1]

    if not address:
        await message.answer("💌আপনার পেমেন্ট মেথড দিন ।\n 🗣️(যেমন: বিকাশ/নগদ/রকেট/বাইনান্স এড্রেস)\n👀 মেথড পাঠানোর ফরমেট: \n🟢 Bikash :01789*****\n 🟢Nagad :0197976***\n 🟢Binance : 0givkbgbj****")
        await BotState.waiting_for_address.set()
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Change Payment Method ⚙️", callback_data="change_method"))
        
        await message.answer(f"💰 আপনার বর্তমান ব্যালেন্স: {balance} ৳\n📍 বর্তমান পেমেন্ট এড্রেস: {address}\n\n🚨আপনি কত টাকা উইথড্র করতে চান লিখুন\n💡 (অবশ্যই ৫০ টাকার উপরে হতে হবে ।):", reply_markup=keyboard)
        await BotState.waiting_for_withdraw_amount.set()

@dp.callback_query_handler(text="change_method", state="*")
async def change_method_callback(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.answer("আপনার নতুন পেমেন্ট মেথড বা নম্বরটি দিন:")
    await BotState.waiting_for_address.set()
    await call.answer()

@dp.message_handler(state=BotState.waiting_for_address)
async def save_address(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE users SET address=? WHERE user_id=?", (message.text, message.from_user.id))
    db.commit()
    await message.answer(f"✅ সফল! আপনার পেমেন্ট এড্রেস আপডেট হয়েছে।\n🔥এখন 'Withdraw' বাটনে ক্লিক করে টাকা তুলতে পারেন।", reply_markup=main_menu())
    await state.finish()

@dp.message_handler(state=BotState.waiting_for_withdraw_amount)
async def withdraw_done(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (message.from_user.id,))
        balance, address = cursor.fetchone()

        if amount > balance:
            await message.answer("❌ পর্যাপ্ত ব্যালেন্স নেই!")
        else:
            new_balance = balance - amount
            cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, message.from_user.id))
            db.commit()
            
            await bot.send_message(ADMIN_ID, f"🔔 উইথড্র রিকোয়েস্ট!\n🆔 আইডি: `{message.from_user.id}`\n💵 পরিমাণ: {amount} ৳\n📍 এড্রেস: {address}")
            await message.answer(f"✅ উইথড্র সফল! {amount} ৳ কেটে নেওয়া হয়েছে।\nবর্তমান ব্যালেন্স: {new_balance} ৳", reply_markup=main_menu())
        await state.finish()
    except:
        await message.answer("❌ শুধু সংখ্যা লিখুন। অথবা মেথড চেঞ্জ বাটনে ক্লিক করুন।\n🤨 বুঝতে সমস্যা হলে আবার নতুন করে /start করুন")

# ==========================================
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

# ==========================================
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
    except:
        await message.answer(f"⚠️ ইউজার `{uid}` কে মেসেজ পাঠানো যায়নি।")
# ১. রেফারেল বাটনে ক্লিক করলে ডাটাবেস থেকে আসল সংখ্যা দেখাবে
@dp.message_handler(lambda message: message.text == "👥 Referral")
async def referral_command(message: types.Message):
    user_id = message.from_user.id
    
    # ডাটাবেস থেকে ইউজারের রেফারেল সংখ্যা খুঁজে আনা
    cursor.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    
    # যদি ডাটাবেসে তথ্য না থাকে তবে ০ দেখাবে
    ref_count = res[0] if res and res[0] is not None else 0
    
    bot_info = await bot.get_me()
    refer_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    # আপনার স্ক্রিনশটের ডিজাইন অনুযায়ী মেসেজ
    text = (f"👥 **আপনার মোট রেফারেল:** {ref_count} জন\n"
            f"🔗 **আপনার লিঙ্ক:** `{refer_link}`\n\n"
            f".......📮**Attention**.......\n\n"
            f"🔴 প্রত্যেক রেফারের জন্য ৫ টাকা পাবেন।\n"
            f"🚨 👀 ওই টাকা তখনই পাবেন যখন ওই ইউজার ৫০ টাকার উপরে ব্যালেন্স করবে।\n"
            f"🔥 আপনি কার মাধ্যমে এই বটে এসেছেন?\n\n\n"
            f"💣 তার Username অথবা User ID লিখে নিচে পাঠান\n...↓↓↓↓নইতো /start দিন")
    
    await message.answer(text, parse_mode="Markdown")
    # ইউজারের ইনপুট নেওয়ার জন্য স্টেট সেট করা
    await BotState.waiting_for_referrer_info.set()

# ২. ইউজার যখন রেফারারের তথ্য লিখে পাঠাবে (ইনপুট হ্যান্ডলার)
@dp.message_handler(state=BotState.waiting_for_referrer_info)
async def process_referral_info(message: types.Message, state: FSMContext):
    referrer_detail = message.text # ইউজার যা লিখে পাঠাবে বট তা গ্রহণ করবে
    sender_name = message.from_user.full_name
    sender_id = message.from_user.id
    
    # অ্যাডমিনকে নোটিফিকেশন পাঠানো
    admin_msg = (f"📢 **নতুন রেফারেল রিপোর্ট!**\n\n"
                 f"👤 **প্রেরক:** {sender_name}\n"
                 f"🆔 **আইডি:** `{sender_id}`\n"
                 f"━━━━━━━━━━━━━━━\n"
                 f"📝 **যার মাধ্যমে এসেছে:** {referrer_detail}")
    
    try:
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except:
        pass
        
    success_text = ("🚨 এক আইডি দিয়ে বার বার রেফার করলে আপনাকে\n এবং ওই আইডিকে টেলিগ্রাম থেকে ব্লক করা হবে!\n\n"
                    "🟢 আপনার রেফারেল রিসিভ করা হয়েছে।\n"
                    "👌 ধন্যবাদ")
    
    await message.answer(success_text, reply_markup=main_menu())
    await state.finish()
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
# --- ১. কিবোর্ড ফাংশন ---
def rules_price_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # বাটনগুলো সুন্দর করে দুই সারিতে সাজানো হয়েছে
    keyboard.row("IG 2fa Rules", "IG Cookies Rules")
    keyboard.row("Ig mother account Rules", "Fb 00 fnd 2fa Rules")
    keyboard.row("🔙 ফিরে যান") 
    return keyboard

# --- ২. মেইন বাটন হ্যান্ডলার (🔴Rules & Price) ---
@dp.message_handler(lambda message: message.text == "🔴Rules & Price", state="*")
async def rules_price_handler(message: types.Message, state: FSMContext):
    # ইউজার অন্য কোনো কাজে আটকে থাকলে সেটা ক্লিয়ার করে মেনু দেখাবে
    await message.answer(
        "👉 **যে ক্যাটাগরির নিয়ম এবং রেট জানতে চান,**\n\n👇 নিচের বাটন থেকে সেটি সিলেক্ট করুন:",
        reply_markup=rules_price_menu(),
        parse_mode="Markdown"
    )

# --- ৩. সাব-বাটন হ্যান্ডলার (রুলস দেখানোর জন্য) ---
@dp.message_handler(lambda message: message.text in ["IG 2fa Rules", "IG Cookies Rules", "Ig mother account Rules", "Fb 00 fnd 2fa Rules"], state="*")
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
                    
    # --- ফিরে যাওয়ার গ্লোবাল হ্যান্ডলার ---
@dp.message_handler(lambda message: message.text in ["🔙 ফিরে যান", "⬅️ Back", "🔙 Back to Main Menu"], state="*")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    # ইউজার কোনো কাজের মাঝপথে থাকলে সেই স্টেট ক্লিয়ার করে দেওয়া
    await state.finish()
    
    # মেইন মেনু দেখানো (নিশ্চিত করুন main_menu() ফাংশনটি আপনার কোডে আছে)
    await message.answer("🏠 আপনি মেইন মেনুতে ফিরে এসেছেন। নিচের বাটন থেকে অপশন বেছে নিন:", reply_markup=main_menu())
                           
# --- ১. টিম ওয়ার্ক মেইন মেনু ---
@dp.message_handler(lambda message: message.text == "👥 Team Work")
async def team_work_home(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🤝 Join Team", "📊 My Status")
    keyboard.row("🔙 মেইন মেনু")
    await message.answer("👥 **টিম ওয়ার্ক প্যানেলে আপনাকে স্বাগতম।**", reply_markup=keyboard, parse_mode="Markdown")

# --- ২. জয়েন টিম অপশন (শর্ত অনুযায়ী) ---
@dp.message_handler(lambda message: message.text == "🤝 Join Team")
async def join_team_options_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🏗️ Create Team", "🔗 Join Existing Team")
    keyboard.row("🔙 ফিরে যান")
    await message.answer("নিচের অপশন থেকে একটি বেছে নিন:", reply_markup=keyboard)

# --- ৩. ক্রিয়েট টিম লজিক (লিমিট সহ) ---
@dp.message_handler(lambda message: message.text == "🏗️ Create Team")
async def start_team_creation(message: types.Message):
    user_id = message.from_user.id
    
    # এডমিন কি না চেক করা (এডমিনের জন্য কোনো লিমিট নেই)
    if user_id != ADMIN_ID:
        # ডাটাবেসে চেক করা এই ইউজার ইতিমধ্যে কয়টি টিমের লিডার
        cursor.execute("SELECT COUNT(*) FROM teams WHERE leader_id=?", (user_id,))
        team_count = cursor.fetchone()[0]
        
        # এখানে ১ এর জায়গায় আপনি যত ইচ্ছা লিমিট দিতে পারেন
        if team_count >= 1:
            return await message.answer("❌ আপনি ইতিমধ্যে একটি টিম খুলেছেন। একজন ইউজার একটির বেশি টিম খুলতে পারবেন না।")

    await message.answer("📝 আপনার টিমের একটি নাম দিন:")
    await BotState.waiting_for_team_name.set()

@dp.message_handler(state=BotState.waiting_for_team_name)
async def get_team_target(message: types.Message, state: FSMContext):
    await state.update_data(t_name=message.text)
    await message.answer("🎯 প্রতিদিন কতগুলো আইডি জমা দিতে পারবেন? (সংখ্যা লিখুন)")
    await BotState.waiting_for_team_target.set()

@dp.message_handler(state=BotState.waiting_for_team_target)
async def finalize_team(message: types.Message, state: FSMContext):
    try:
        target = int(message.text)
        data = await state.get_data()
        t_name = data.get('t_name')
        
        # র্যান্ডম ইউনিক আইডি তৈরি
        unique_id = generate_numeric_id()
        
        # ডাটাবেসে সেভ
        cursor.execute("INSERT INTO teams (team_id, team_name, leader_id, daily_target) VALUES (?, ?, ?, ?)", 
                       (unique_id, t_name, message.from_user.id, target))
        db.commit()
        
        # লিডারকে মেম্বার হিসেবে অ্যাড করা
        cursor.execute("INSERT OR REPLACE INTO team_members (user_id, team_id) VALUES (?, ?)", 
                       (message.from_user.id, unique_id))
        db.commit()
        
        await message.answer(f"✅ **টিম তৈরি হয়েছে!**\n\n📛 নাম: {t_name}\n🎯 লক্ষ্য: {target}\n🆔 ইউনিক টিম আইডি: `{unique_id}`", reply_markup=main_menu(), parse_mode="Markdown")
        await state.finish()
    except ValueError:
        await message.answer("❌ ভুল! টার্গেট অবশ্যই সংখ্যায় লিখুন।")

# --- ৪. সচল টিম লিস্ট দেখা ---
@dp.message_handler(lambda message: message.text == "🔗 Join Existing Team")
async def show_all_teams_handler(message: types.Message):
    cursor.execute("SELECT team_id, team_name FROM teams")
    teams = cursor.fetchall()
    if not teams: return await message.answer("কোনো টিম নেই।")
    
    txt = "📍 **সচল টিমের আইডিগুলো:**\n\n"
    for t in teams:
        txt += f"🔹 {t[1]} — আইডি: `{t[0]}`\n"
    txt += "\n🤝 জয়েন করতে লিখুন: `/join আইডি`"
    await message.answer(txt, parse_mode="Markdown")
    # --- মাই স্ট্যাটাস (লিডারদের জন্য ইনকাম রিপোর্ট সহ) ---
@dp.message_handler(lambda message: message.text == "📊 My Status", state="*")
async def my_status_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # ইউজার কোন টিমে আছে তা বের করা
    cursor.execute("SELECT team_id FROM team_members WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    
    if not res:
        return await message.answer("❌ আপনি বর্তমানে কোনো টিমে যুক্ত নেই।")
    
    t_id = res[0]
    
    # টিমের তথ্য এবং লিডার কে তা বের করা
    cursor.execute("SELECT team_name, leader_id, daily_target FROM teams WHERE team_id=?", (t_id,))
    t_info = cursor.fetchone()
    team_name, leader_id, target = t_info[0], t_info[1], t_info[2]

    # মেম্বার সংখ্যা গণনা
    cursor.execute("SELECT COUNT(user_id) FROM team_members WHERE team_id=?", (t_id,))
    member_count = cursor.fetchone()[0]

    # টিমের মোট কাজের স্ট্যাটাস (ফাইল এবং সিঙ্গেল আইডি)
    cursor.execute('''SELECT SUM(stats.file_count), SUM(stats.single_id_count) 
                      FROM team_members 
                      LEFT JOIN stats ON team_members.user_id = stats.user_id 
                      WHERE team_members.team_id=?''', (t_id,))
    work_stats = cursor.fetchone()
    total_files = work_stats[0] if work_stats[0] else 0
    total_singles = work_stats[1] if work_stats[1] else 0

    # মূল মেসেজ তৈরি
    msg = (
        f"📊 **টিম স্ট্যাটাস রিপোর্ট**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 নাম: {team_name}\n"
        f"👑 **টিম লিডার আইডি:** `{t_info[1]}`\n"
        f"🆔 আইডি: `{t_id}`\n"
        f"👨‍👩‍👧‍👦 মোট মেম্বার: {member_count} জন\n"
        f"🎯 লক্ষ্য: {target} টি\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📈 মোট কাজ:\n"
        f"📁 ফাইল: {total_files} টি | 🆔 আইডি: {total_singles} টি\n"
    )

    # --- লিডার চেক এবং টাকা হিসাব করা ---
    if user_id == leader_id:
        # এখানে আপনার রেট বসান (যেমন: প্রতি ফাইল ৫ টাকা, প্রতি আইডি ২ টাকা)
        # আপনি আপনার রেট অনুযায়ী নিচের সংখ্যাগুলো বদলে নিতে পারেন
        file_rate = 5.0  # একটি ফাইলের দাম
        id_rate = 2.0    # একটি আইডির দাম
        
        total_money = (total_files * file_rate) + (total_singles * id_rate)
        
        msg += (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 **টিমের মোট ইনকাম: {total_money:.2f} ৳**\n"
            f"⚠️ (এই অংশটি শুধু আপনি লিডার হিসেবে দেখতে পাচ্ছেন)\n"
        )
    
    msg += "━━━━━━━━━━━━━━━━━━"
    await message.answer(msg, parse_mode="Markdown")

# --- টিম লিডার আইডি পরিবর্তন করার আপডেট কোড ---
@dp.message_handler(commands=['change_leader_id'])
async def change_leader_id_handler(message: types.Message):
    # আপনার অ্যাডমিন আইডি এখানে দিন
    MY_ADMIN_ID = 123456789  # <--- আপনার নিজের আইডি দিন

    if message.from_user.id != MY_ADMIN_ID:
        return

    args = message.get_args().split()
    
    if len(args) < 2:
        return await message.answer("❌ **সঠিক নিয়ম:**\n`/change_leader_id পুরাতন_আইডি নতুন_আইডি`", parse_mode="Markdown")

    try:
        # আইডিগুলোকে সংখ্যায় (Integer) রূপান্তর করা হচ্ছে
        old_id = int(args[0])
        new_id = int(args[1])
        
        # ১. teams টেবিলে লিডার আইডি আপডেট
        cursor.execute("UPDATE teams SET leader_id = ? WHERE leader_id = ?", (new_id, old_id))
        
        # ২. team_members টেবিলে মেম্বার আইডি আপডেট
        cursor.execute("UPDATE team_members SET user_id = ? WHERE user_id = ?", (new_id, old_id))
        
        # ৩. stats টেবিলে কাজের রেকর্ড আপডেট
        cursor.execute("UPDATE stats SET user_id = ? WHERE user_id = ?", (new_id, old_id))
        
        # ৪. users টেবিলে ব্যালেন্স ও অন্যান্য ডাটা আপডেট
        cursor.execute("UPDATE users SET user_id = ? WHERE user_id = ?", (new_id, old_id))
        
        # ৫. blacklist টেবিলে আইডি আপডেট
        cursor.execute("UPDATE blacklist SET user_id = ? WHERE user_id = ?", (new_id, old_id))

        # আপনার ডাটাবেস কানেকশন Db বড় হাতের, তাই Db.commit()
        Db.commit() 
        
        # কতগুলো রো (Row) আপডেট হয়েছে তা চেক করা
        if cursor.rowcount > 0:
            await message.answer(f"✅ **আইডি সফলভাবে আপডেট হয়েছে!**\n\nপুরাতন: `{old_id}`\nনতুন: `{new_id}`", parse_mode="Markdown")
        else:
            await message.answer(f"⚠️ ডাটাবেসে `{old_id}` আইডিটি খুঁজে পাওয়া যায়নি। আইডি সঠিক আছে কি না চেক করুন।")
            
    except ValueError:
        await message.answer("❌ আইডি অবশ্যই শুধু সংখ্যা হতে হবে!")
    except Exception as e:
        await message.answer(f"❌ ডাটাবেস এরর: {str(e)}")
    
if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
