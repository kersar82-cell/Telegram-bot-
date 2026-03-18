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

cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, address TEXT)''')
db.commit()
cursor.execute('''ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0''')
db.commit()
# টিম টেবিল: যেখানে টিমের নাম এবং লিডারের আইডি থাকবে
cursor.execute('''CREATE TABLE IF NOT EXISTS teams 
                  (team_id INTEGER PRIMARY KEY AUTOINCREMENT, team_name TEXT, leader_id INTEGER)''')

# মেম্বার টেবিল: কে কোন টিমে আছে তা ট্র্যাক করার জন্য
cursor.execute('''CREATE TABLE IF NOT EXISTS team_members 
                  (user_id INTEGER PRIMARY KEY, team_id INTEGER)''')
db.commit()
# এটি ডাটাবেস সেকশনে যোগ করুন
cursor.execute('''CREATE TABLE IF NOT EXISTS user_history 
                  (user_id INTEGER, message_text TEXT, date TEXT)''')
db.commit()
# ডাটাবেজে username কলাম যোগ করা (একবার রান হলেই হবে)
try:
    cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    db.commit()
except:
    pass
    

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
    
    
# /start কমান্ডে মেইন মেনু ও বাটন
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    
    user_id = message.from_user.id
    # ইউজারনেম ফরম্যাট করা
    username = f"@{message.from_user.username}" if message.from_user.username else "No_Username"
    
    # ইউজার আইডি এবং ইউজারনেম সেভ বা আপডেট করা
    cursor.execute("""
        INSERT INTO users (user_id, username) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username = excluded.username
    """, (user_id, username))
    db.commit()


    inline_kb = types.InlineKeyboardMarkup(row_width=2)
    help_button = types.InlineKeyboardButton(text="🆘 Contact Support", url="https://t.me/instafbhub_support") 
    inline_kb.add(help_button)

    welcome_text = """📢 আজকের কাজের আপডেট এবং রেট লিস্ট 📢
📌 Instagram 2FA: ২.৩০ ৳
📌 Instagram Cookies: ৩.৯০ ৳
📌 Instagram Mother: ৭ ৳
📌 Facebook FBc00Fnd: ৫.৮০ ৳

Support: @Dinanhaji"""

    # এই লাইনগুলোই এরর দিচ্ছিল, এখন এগুলো async def-এর ভেতরে আছে
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
        # শুধুমাত্র সিঙ্গেল আইডি জমা দিলে ব্যালেন্স আপডেট হবে
    if amount_to_add > 0:
        # ১. ইউজারের নিজের ব্যালেন্স আপডেট
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount_to_add, message.from_user.id))
        
        # ২. টিম মেম্বার হলে লিডারকে কমিশন দেওয়া (আইডিয়া ২)
        cursor.execute("SELECT team_id FROM team_members WHERE user_id=?", (message.from_user.id,))
        team_res = cursor.fetchone()
        
        if team_res:
            t_id = team_res[0]
            # টিমের লিডার কে তা খুঁজে বের করা
            cursor.execute("SELECT leader_id FROM teams WHERE team_id=?", (t_id,))
            leader_data = cursor.fetchone()
            
            if leader_data:
                leader_id = leader_data[0]
                # লিডার পাবে প্রতি আইডিতে ০.১০ টাকা কমিশন
                leader_commission = 0.10 
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (leader_commission, leader_id))
                
                # ৩. টিম স্ট্যাটাস আপডেট (আইডিয়া ১ এর জন্য - ঐচ্ছিক)
                # এখানে আপনি চাইলে টিমের মোট কাজের সংখ্যাও আপডেট করতে পারেন
    
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
# ==========================================
# ৩. উইথড্র ও পেমেন্ট মেথড লজিক (Updated)
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
        res = cursor.fetchone()
        balance, address = res[0], res[1]

        if amount > balance:
            await message.answer("❌ পর্যাপ্ত ব্যালেন্স নেই!")
        elif amount < 50:
            await message.answer("❌ সর্বনিম্ন ৫০ টাকা উইথড্র করতে হবে।")
        else:
            # ডাটাবেসে রিকোয়েস্ট সেভ করা
            cursor.execute("INSERT INTO withdraw_requests (user_id, amount, status) VALUES (?, ?, 'pending')", 
                           (message.from_user.id, amount))
            req_id = cursor.lastrowid
            
            # ব্যালেন্স কাটা
            new_balance = balance - amount
            cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, message.from_user.id))
            db.commit()
            
            # অ্যাডমিনের জন্য বাটন
            keyboard = types.InlineKeyboardMarkup()
            btn_approve = types.InlineKeyboardButton("✅ Approve", callback_data=f"wd_approve_{req_id}")
            btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"wd_reject_{req_id}")
            keyboard.add(btn_approve, btn_reject)
            
            # অ্যাডমিনকে জানানো
            admin_msg = (f"🔔 **নতুন উইথড্র রিকোয়েস্ট!**\n\n"
                         f"🆔 আইডি: `{message.from_user.id}`\n"
                         f"💵 পরিমাণ: {amount} ৳\n"
                         f"📍 এড্রেস: {address}\n"
                         f"🔢 রিকোয়েস্ট আইডি: {req_id}")
            
            await bot.send_message(ADMIN_ID, admin_msg, reply_markup=keyboard, parse_mode="Markdown")
            
            # ইউজারকে জানানো
            await message.answer(f"✅ উইথড্র রিকোয়েস্ট পাঠানো হয়েছে। {amount} ৳ কেটে নেওয়া হয়েছে।\n💰 বর্তমান ব্যালেন্স: {new_balance} ৳\n🕒 অ্যাডমিন এপ্রুভ করলে আপনি মেসেজ পাবেন।", reply_markup=main_menu())
        
        await state.finish()
    except Exception as e:
        await message.answer("❌ ভুল ইনপুট। শুধু সংখ্যা লিখুন।")
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
