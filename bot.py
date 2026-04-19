import logging
import sqlite3
import os 
import asyncio
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from supabase import create_client, Client

# আপনার ডাটাবেস তথ্য
SUPABASE_URL = "https://wvczkeugwcfhyizibafs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind2Y3prZXVnd2NmaHlpemliYWZzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjE2NzQ1NywiZXhwIjoyMDkxNzQzNDU3fQ.xERE9HIq7fttGUaow9VwKn_A1YaoRr-w7OMf4eFJm3I"

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
def save_user_start(user_id, first_name):
    try:
        # 'user_list' নামে একটি টেবিল সুপাবেসে থাকতে হবে
        # যেখানে user_id হবে Primary Key
        data = {
            "user_id": str(user_id),
            "name": str(first_name)
        }
        supabase.table("user_list").upsert(data).execute()
    except Exception as e:
        print(f"Error saving user: {e}")
                    
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
    try:
        # Supabase থেকে চেক করা হচ্ছে ইউজার ব্লক কি না
        res = await asyncio.to_thread(supabase.table("blacklist").select("user_id").eq("user_id", user_id).execute)
        return len(res.data) > 0
    except Exception:
        return False
        
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
    
    # ১. চেক করি ইউজার আগে থেকে Supabase-এ আছে কি না (অ্যাসিঙ্ক্রোনাসভাবে)
    response = await asyncio.to_thread(supabase.table("users").select("user_id").eq("user_id", user_id).execute)

    # ২. যদি ইউজার একদম নতুন হয়
    if not response.data:
        referrer_id = 0
        if args and args.isdigit():
            temp_id = int(args)
            # চেক করা হচ্ছে ইউজার নিজের লিংকে নিজে ক্লিক করেছে কি না
            if temp_id != user_id:
                referrer_id = temp_id
                
                # ১. রেফারারের কাউন্ট ১ বাড়ানো (balances টেবিলে)
                ref_user = await asyncio.to_thread(supabase.table("balances").select("referral_count").eq("user_id", referrer_id).execute)
                if ref_user.data:
                    new_count = ref_user.data[0]['referral_count'] + 1
                    await asyncio.to_thread(supabase.table("balances").update({"referral_count": new_count}).eq("user_id", referrer_id).execute)
                
                # ২. রেফারারকে মেসেজ পাঠানো
                try:
                    await bot.send_message(referrer_id, "🔔 **অভিনন্দন!**\n\nআপনার রেফারেল লিঙ্ক ব্যবহার করে একজন নতুন ইউজার জয়েন করেছে। 🥳")
                except:
                    pass

        # ৩. ডাটাবেসে নতুন ইউজার সেভ করা (নতুন ৩টি টেবিলে)
        await asyncio.to_thread(supabase.table("users").insert({"user_id": user_id, "username": username, "referred_by": referrer_id}).execute)
        await asyncio.to_thread(supabase.table("balances").insert({"user_id": user_id}).execute)
        await asyncio.to_thread(supabase.table("payment_methods").insert({"user_id": user_id}).execute)
            
    else:
        # যদি ইউজার আগে থেকেই থাকে, শুধু ইউজারনেম আপডেট করা (users টেবিলে)
        await asyncio.to_thread(supabase.table("users").update({"username": username}).eq("user_id", user_id).execute)

    # ৩. ইনলাইন বাটন ও ওয়েলকাম মেসেজ সেটআপ
    inline_kb = types.InlineKeyboardMarkup(row_width=2)
    help_button = types.InlineKeyboardButton(text="🆘 Contact Support", url="https://t.me/INSTAFB_SUPPORT") 
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

        # =========================================================
# ইনস্টাগ্রাম ওয়ার্ক লজিক (High Concurrency Supported)
# =========================================================

# ১. ইনস্টাগ্রাম মেনু ওপেন
@dp.message_handler(lambda message: message.text == "💻INSTAGRAM WORK", state="*")
async def work_start(message: types.Message, state: FSMContext):
    # ইউজার যদি অন্য কোনো স্টেটে আটকে থাকে, সেটা ক্লিয়ার করে দেবে
    await state.finish() 
    
    # ব্লক লিস্ট চেক (Supabase থেকে)
    if await is_blocked(message.from_user.id):
        return await message.answer("❌ দুঃখিত, আপনি ব্লকড! আপনি আর কাজ জমা দিতে পারবেন না। \nএডমিনের সাথে কথা বলুন 👍")
    
    # ইনলাইন কিবোর্ডের বদলে নরমাল রিপ্লাই কিবোর্ড (যাতে নিচে বাটনগুলো সুন্দর করে বসে)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("IG Mother Account", "IG 2fa")
    keyboard.row("IG Cookies", "🔄 রিফ্রেশ") 
    
    # আপনার ভিপিএনের তথ্য
    msg = """🔐NORD VPN
🌐Email > gaughan9999@hotmail.co.uk
🔐Pass  > Auders*1

🌐Email > betzcampaign@gmail.com
🔐Pass  > Hnhnddio1986!

🌐Email > thomasvcrowl@gmail.com
🔐Pass  > HeretiC762!!"""

    await message.answer(msg, reply_markup=keyboard)
    
# এই হ্যান্ডলারটি এখন একদম পারফেক্ট কাজ করবে
# ==========================================
# ধাপ ২: ক্যাটাগরি সিলেক্ট এবং অটোমেটিক ইউজারনেম
# ==========================================
@dp.message_handler(lambda message: message.text in ["IG Mother Account", "IG 2fa", "IG Cookies"], state="*")
async def ask_work_type(message: types.Message, state: FSMContext):
    category = message.text
    
    # অন/অফ চেক (সুইচ বন্ধ থাকলে কাজ করতে দিবে না)
    if category == "IG Mother Account" and not IG_MOTHER_ENABLED:
        return await message.answer("⚠️ দুঃখিত, বর্তমানে IG Mother Account কাজ সাময়িকভাবে বন্ধ আছে।")
    if category == "IG 2fa" and not IG_2FA_ENABLED:
        return await message.answer("⚠️ দুঃখিত, বর্তমানে IG 2fa কাজ সাময়িকভাবে বন্ধ আছে।")
    if category == "IG Cookies" and not IG_COOKIES_ENABLED:
        return await message.answer("⚠️ দুঃখিত, বর্তমানে IG Cookies কাজ সাময়িকভাবে বন্ধ আছে।")

    # অটোমেটিক ইউজারনেম এবং ফিক্সড পাসওয়ার্ড জেনারেট
    username = generate_ig_username()
    fixed_password = "UserPass@2026" 

    # ডাটাগুলো বটের মেমোরিতে (State) সেভ রাখা
    await state.update_data(auto_user=username, auto_pass=fixed_password, category=category)

    # ইনলাইন বাটন তৈরি
    inline_kb = types.InlineKeyboardMarkup(row_width=1)
    inline_kb.add(
        types.InlineKeyboardButton("🔐 2FA কোড দিন", callback_data="ask_auto_2fa"),
        types.InlineKeyboardButton("🔄 নতুন ইউজারনেম", callback_data="regen_ig_user"),
        types.InlineKeyboardButton("🔙 ফিরে যান", callback_data="back_to_main")
    )

    # HTML ফরম্যাটে মেসেজ (কপি করার সুবিধার জন্য <code> ট্যাগ)
    text = (
        f"<b>✅ আপনি বেছে নিয়েছেন:</b> {category}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>👤 Username:</b> <code>{username}</code>\n"
        f"<b>🔑 Password:</b> <code>{fixed_password}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>💡 উপরের তথ্য দিয়ে লগিন করুন। ইউজারনেম না মিললে '🔄 নতুন ইউজারনেম' বাটনে ক্লিক করুন। কাজ শেষে ২এফএ কোড দিন।</i>"
    )

    await message.answer(text, reply_markup=inline_kb, parse_mode="HTML")


# ==========================================
# ধাপ ৩: নতুন ইউজারনেম জেনারেট বাটন (High Concurrency Supported)
# ==========================================
@dp.callback_query_handler(lambda c: c.data == "regen_ig_user", state="*")
async def regenerate_user_logic(call: types.CallbackQuery, state: FSMContext):
    # ১. প্রথমেই কলব্যাক অ্যানসার করে দেওয়া যাতে ইউজারের স্ক্রিনে লোডিং আটকে না থাকে
    await call.answer("⏳ জেনারেট হচ্ছে...")
    
    # ২. নন-ব্লকিং ভাবে ইউজারনেম জেনারেট করা (১০০০ জন একসাথে চাপলেও বট হ্যাং হবে না)
    new_username = await asyncio.to_thread(generate_ig_username)
    
    # ৩. মেমোরি থেকে আগের ক্যাটাগরি এবং পাসওয়ার্ড নেওয়া
    user_data = await state.get_data()
    category = user_data.get("category", "IG Work")
    fixed_pass = user_data.get("auto_pass", "UserPass@2026")

    # ৪. মেমোরিতে নতুন ইউজারনেমটি আপডেট করে রাখা
    await state.update_data(auto_user=new_username)

    # ৫. ইনলাইন বাটনগুলো সেট করা
    inline_kb = types.InlineKeyboardMarkup(row_width=1)
    btn_2fa = types.InlineKeyboardButton("🔐 2FA কোড দিন", callback_data="ask_auto_2fa")
    btn_regen = types.InlineKeyboardButton("🔄 নতুন ইউজারনেম (Regenerate)", callback_data="regen_ig_user")
    btn_back = types.InlineKeyboardButton("🔙 ফিরে যান", callback_data="back_to_main")
    inline_kb.add(btn_2fa, btn_regen, btn_back)

    # ৬. HTML ফরম্যাটে মেসেজ তৈরি
    text = (
        f"<b>📌 ক্যাটাগরি:</b> {category}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>👤 Username:</b> <code>{new_username}</code> (Updated ✨)\n"
        f"<b>🔑 Password:</b> <code>{fixed_pass}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>💡 নতুন ইউজারনেম জেনারেট হয়েছে। এটি কপি করে লগিন করুন এবং কাজ শেষে ২এফএ কোড দিন।</i>"
    )
    
    try:
        # মেসেজটি এডিট করা হচ্ছে
        await call.message.edit_text(text, reply_markup=inline_kb, parse_mode="HTML")
    except Exception:
        # একই নাম বারবার আসলে টেলিগ্রাম এডিট করতে দেয় না, তাই Error ইগনোর করা হলো
        pass 
    
# ==========================================
# ধাপ ৪: 2FA কোড চাওয়া
# ==========================================
@dp.callback_query_handler(lambda c: c.data == "ask_auto_2fa", state="*")
async def trigger_2fa_input(call: types.CallbackQuery):
    # ১. দ্রুত রেসপন্স করে ইউজারের লোডিং থামিয়ে দেওয়া
    await call.answer()
    
    # ২. ইউজারকে 2FA দেওয়ার স্টেটে নিয়ে যাওয়া
    await BotState.waiting_for_auto_2fa.set()
    
    # ৩. HTML ফরম্যাটে মেসেজ দিয়ে কোড চাওয়া
    await call.message.answer(
        "🔐 <b>অনুগ্রহ করে আপনার 2FA (Two-Factor Authentication) কোডটি নিচে লিখে পাঠান:</b>", 
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )

# ==========================================
# ধাপ ৫: "🔙 ফিরে যান" বাটনের কাজ
# ==========================================
@dp.callback_query_handler(lambda c: c.data == "back_to_main", state="*")
async def go_back_to_home(call: types.CallbackQuery, state: FSMContext):
    # ১. দ্রুত রেসপন্স
    await call.answer()
    
    # ২. সব স্টেট ক্লিয়ার করা
    await state.finish() 
    
    # ৩. মেসেজ ডিলিট করা (কেউ একসাথে দুবার চাপলে যাতে বট ক্র্যাশ না করে তাই try-except)
    try:
        await call.message.delete() 
    except Exception:
        pass
        
    # ৪. মেইন মেনু পাঠানো
    await call.message.answer("🏠 আপনি মেইন মেনুতে ফিরে এসেছেন।", reply_markup=main_menu())
# ==========================================
# ধাপ ৬: ২এফএ রিসিভ, সুপার-ফাস্ট সেভ এবং ব্যালেন্স অ্যাড
# ==========================================
@dp.message_handler(state=BotState.waiting_for_auto_2fa)
async def process_auto_2fa_submission(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    username = user_data.get('auto_user')
    password = user_data.get('auto_pass')
    category = user_data.get('category')
    tfa_code = message.text # ইউজারের পাঠানো কোড
    user_id = message.from_user.id

    if not username or not password:
        await state.finish()
        return await message.answer("⚠️ সেশন এরর! দয়া করে মেনু থেকে আবার ক্যাটাগরি সিলেক্ট করুন।", reply_markup=main_menu())

    # ১. ইউজারকে আটকে না রেখে প্রথমেই স্টেট ক্লিয়ার করে দিচ্ছি!
    await state.finish()

    final_category = f"{category} [✅ Done]"
    import datetime
    bd_now = datetime.datetime.now() + datetime.timedelta(hours=6)
    dt_log = bd_now.strftime("%d/%m/%Y %I:%M %p") 
    today = datetime.date.today().strftime("%Y-%m-%d")

    amount_to_add = 0 
    if category == "IG Cookies":
        amount_to_add = 4
    elif category == "IG Mother Account":
        amount_to_add = 7
    elif category == "IG 2fa":
        amount_to_add = 3

    try:
        # --- সমান্তরাল (Parallel) ডাটাবেস অপারেশন ---
        # এই তিনটি কাজ আলাদা থ্রেডে চলবে, ফলে বট হ্যাং হবে না
        
        def save_log_task():
            log_data = {
                "user_id": user_id, 
                "category": final_category, 
                "u_id": str(username), 
                "u_pass": str(password), 
                "two_fa": str(tfa_code), 
                "date_time": dt_log
            }
            supabase.table("user_id_logs").insert(log_data).execute()

        def update_stats_task():
            stats_res = supabase.table("daily_stats").select("single_id_count").eq("user_id", user_id).eq("date", today).execute()
            if stats_res.data:
                current_count = stats_res.data[0].get('single_id_count', 0)
                supabase.table("daily_stats").update({"single_id_count": current_count + 1}).eq("user_id", user_id).eq("date", today).execute()
            else:
                supabase.table("daily_stats").insert({"user_id": user_id, "date": today, "single_id_count": 1}).execute()

        def update_balance_task():
            if amount_to_add > 0:
                bal_res = supabase.table("balances").select("pending_balance").eq("user_id", user_id).execute()
                if bal_res.data:
                    current_pending = bal_res.data[0].get('pending_balance', 0)
                    supabase.table("balances").update({"pending_balance": current_pending + amount_to_add}).eq("user_id", user_id).execute()

        # ২. তিনটি কাজ একসাথে (Gather) রান করানো হচ্ছে
        await asyncio.gather(
            asyncio.to_thread(save_log_task),
            asyncio.to_thread(update_stats_task),
            asyncio.to_thread(update_balance_task)
        )

        # ৩. অ্যাডমিনকে রিপোর্ট পাঠানো
        admin_report = (
            f"🚀 <b>নতুন অটো-টাস্ক সম্পন্ন!</b>\n"
            f"👤 <b>ইউজার:</b> {message.from_user.full_name}\n"
            f"🆔 <b>আইডি:</b> <code>{user_id}</code>\n"
            f"📂 <b>ক্যাটাগরি:</b> {category}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{username}</code>\n"
            f"🔑 <b>Pass:</b> <code>{password}</code>\n"
            f"🔐 <b>2FA:</b> <code>{tfa_code}</code>"
        )
        try:
            await bot.send_message(FILE_ADMIN_ID, admin_report, parse_mode="HTML")
        except:
            pass

        # ৪. সাকসেস মেসেজ ও নতুন কিবোর্ড
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(f"➕ আরেকটি {category} পাঠান") 
        markup.add("🏠 মেইন মেনু")
        
        await message.answer(
            f"<b>✅ আইডি সফলভাবে জমা হয়েছে!</b>\n\n"
            f"👤 ইউজারনেম: <code>{username}</code>\n"
            f"📊 স্ট্যাটাস: <b>🟢 সম্পন্ন (Done)</b>\n\n"
            f"ধন্যবাদ! আপনার তথ্য ডাটাবেসে সেভ করা হয়েছে এবং ব্যালেন্স যোগ হয়েছে।", 
            reply_markup=markup, parse_mode="HTML"
        )

    except Exception as e:
        print(f"Final Submit Error: {e}")
        await message.answer("❌ ডাটাবেস ব্যস্ত আছে। দয়া করে একটু পর আবার চেষ্টা করুন।", reply_markup=main_menu())


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
# --- উইথড্র বাটনে ক্লিক করার পর মাধ্যম সিলেক্ট করার মেনু ---
@dp.callback_query_handler(text="start_withdraw")
async def start_withdraw_menu(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📱 Mobile Recharge", callback_data="wd_recharge"),
        types.InlineKeyboardButton("💸 Send Money", callback_data="wd_sendmoney")
    )
    await call.message.edit_text("আপনি কোন মাধ্যমে টাকা উইথড্র করতে চান? 👇", reply_markup=kb)
    await call.answer()
            
# --- ১. পেমেন্ট মেথড টাইপ সিলেকশন (Recharge vs Send Money) ---
@dp.callback_query_handler(text="add_method")
async def select_method_type(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📱 Mobile Recharge", callback_data="set_recharge"),
        types.InlineKeyboardButton("💸 Send Money", callback_data="set_sendmoney")
    )
    await call.message.edit_text("আপনি কোন মাধ্যমে নম্বর সেভ করতে চান? 👇", reply_markup=kb)
    # --- ১. মোবাইল রিচার্জ নম্বর সেভ করা (সংশোধিত) ---
@dp.message_handler(state=BotState.waiting_for_recharge_num)
async def save_recharge_db(message: types.Message, state: FSMContext):
    num = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    full_name = message.from_user.full_name
    
    # Supabase-এর payment_methods টেবিলে সেভ করা
    await asyncio.to_thread(supabase.table("payment_methods").update({"recharge_num": num}).eq("user_id", user_id).execute)
    
    # অ্যাডমিনকে জানানো
    admin_text = (
        f"📱 নতুন রিচার্জ নম্বর সেট!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {full_name}\n"
        f"🆔 আইডি: {user_id}\n"
        f"🔗 ইউজারনেম: @{username}\n"
        f"📞 নম্বর: {num}"
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        print(f"অ্যাডমিনকে মেসেজ পাঠাতে এরর: {e}")
    
    await message.answer(
        f"✅ আপনার <b>Mobile Recharge</b> নম্বর <code>{num}</code> সফলভাবে সেভ হয়েছে!", 
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    
    await state.finish()
# --- ২. সেন্ড মানি (বিকাশ/নগদ/রকেট/বাইনান্স) নম্বর সেভ করা (সংশোধিত) ---
@dp.message_handler(state=BotState.waiting_for_method_num)
async def save_sendmoney_db(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_type = data.get('p_type') # bkash, nagad, etc.
    num = message.text
    user_id = message.from_user.id
    
    # কোন কলামে সেভ হবে তা নির্ধারণ করা
    column = f"{p_type}_num" if p_type != "binance" else "binance_id"
    
    # Supabase-এর payment_methods টেবিলে সেভ করা
    await asyncio.to_thread(supabase.table("payment_methods").update({column: num}).eq("user_id", user_id).execute)
    
    # অ্যাডমিনকে জানানো
    admin_text = (
        f"💸 **নতুন পেমেন্ট মেথড সেট!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {message.from_user.full_name}\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"💳 মেথড: {p_type.upper()}\n"
        f"🔢 নম্বর/ID: `{num}`"
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    except Exception as e:
        pass
    
    await message.answer(f"✅ আপনার **{p_type.upper()}** তথ্য সফলভাবে সেভ হয়েছে!", reply_markup=main_menu())
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

# --- ১. উইথড্র পরিমাণ গ্রহণ এবং অ্যাডমিনকে পাঠানো (High Concurrency Supported) ---
@dp.message_handler(state=BotState.waiting_for_withdraw_amount)
async def process_withdraw_final(message: types.Message, state: FSMContext):
    try:
        amount = int(float(message.text))
    except (ValueError, TypeError):
        return await message.answer("❌ অনুগ্রহ করে সঠিক সংখ্যা লিখুন (যেমন: ১০০)")

    user_id = message.from_user.id
    
    # 🚀 High Concurrency: তিনটি টেবিল থেকে একসাথে ডাটা আনা হচ্ছে (৩ গুণ ফাস্ট!)
    bal_task = asyncio.to_thread(supabase.table("balances").select("main_balance, withdraw_count").eq("user_id", user_id).execute)
    pay_task = asyncio.to_thread(supabase.table("payment_methods").select("*").eq("user_id", user_id).execute)
    usr_task = asyncio.to_thread(supabase.table("users").select("referred_by").eq("user_id", user_id).execute)

    # তিনটির রেসপন্সের জন্য একসাথে অপেক্ষা করা হচ্ছে
    bal_res, pay_res, usr_res = await asyncio.gather(bal_task, pay_task, usr_task)

    if not bal_res.data or not pay_res.data:
        await state.finish()
        return await message.answer("❌ ডাটাবেসে আপনার তথ্য পাওয়া যায়নি।")

    balance = bal_res.data[0].get('main_balance', 0)
    wd_count = bal_res.data[0].get('withdraw_count', 0)
    
    p_data = pay_res.data[0]
    bkash = p_data.get('bkash_num')
    nagad = p_data.get('nagad_num')
    rocket = p_data.get('rocket_num')
    binance = p_data.get('binance_id')
    recharge = p_data.get('recharge_num')
    
    if amount > int(balance):
        return await message.answer(f"❌ আপনার ব্যালেন্স পর্যাপ্ত নয়! বর্তমান: {int(balance)} ৳")
    
    if amount <= 19:
        return await message.answer("❌ সর্বনিম্ন ২০ টাকা উইথড্র করা যাবে।")

    data = await state.get_data()
    w_type = data.get('withdraw_type')

    commission = int(amount * 0.05)
    next_wd_number = (wd_count or 0) + 1
    new_balance = int(balance - amount)

    # 🚀 ডাটাবেস আপডেট (নন-ব্লকিং)
    await asyncio.to_thread(supabase.table("balances").update({"main_balance": new_balance, "withdraw_count": next_wd_number}).eq("user_id", user_id).execute)

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

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"admin_payment_approve_{user_id}_{amount}_{commission}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_payment_reject_{user_id}_{amount}")
    )

    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="HTML")
        await message.answer("✅ আপনার উইথড্র রিকোয়েস্ট সফলভাবে জমা হয়েছে!", reply_markup=main_menu())
    except Exception:
        # মেসেজ না গেলে ব্যালেন্স রিফান্ড (নন-ব্লকিং)
        await asyncio.to_thread(supabase.table("balances").update({"main_balance": balance, "withdraw_count": wd_count}).eq("user_id", user_id).execute)
        await message.answer("❌ সিস্টেম এরর! অ্যাডমিনকে রিকোয়েস্ট পাঠানো যায়নি। টাকা রিফান্ড করা হয়েছে।")
    
    await state.finish()
    
    
    # ৪. এরপর অ্যাডমিনকে মেসেজ পাঠানো

# ==========================================
# ==========================================
@dp.message_handler(commands=['check_user'], user_id=ADMIN_ID)
async def admin_check_user_details(message: types.Message):
    args = message.get_args()
    if not args.isdigit(): 
        return await message.answer("⚠️ সঠিক ইউজার আইডি দিন।\nউদাহরণ: `/check_user 12345678`", parse_mode="Markdown")
    
    user_id = int(args)
    
    # ডাটাবেস থেকে সব তথ্য আনা (users এবং balances টেবিল থেকে)
    usr_res = await asyncio.to_thread(supabase.table("users").select("username").eq("user_id", user_id).execute)
    bal_res = await asyncio.to_thread(supabase.table("balances").select("main_balance, refer_balance, pending_balance, referral_count").eq("user_id", user_id).execute)
    
    if usr_res.data and bal_res.data:
        # ডাটাগুলো আলাদা করা
        balance = bal_res.data[0].get("main_balance", 0)
        refer_bal = bal_res.data[0].get("refer_balance", 0)
        pending_bal = bal_res.data[0].get("pending_balance", 0)
        ref_count = bal_res.data[0].get("referral_count", 0)
        
        # ইউজারনেম না থাকলে বা None হলে বিকল্প টেক্সট
        db_username = usr_res.data[0].get("username")
        if not db_username:
            db_username = "ইউজারনেম নেই"
        
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
            # Supabase-এর balances টেবিলের main_balance আপডেট করা হচ্ছে
            await asyncio.to_thread(supabase.table("balances").update({"main_balance": float(args[1])}).eq("user_id", int(args[0])).execute)
            await message.answer(f"✅ ইউজার {args[0]} এর ব্যালেন্স এডিট করা হয়েছে।")
        except: 
            await message.answer("ফরম্যাট: /edit আইডি টাকা")

@dp.message_handler(commands=['broadcast'])
async def admin_broadcast(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        text = message.get_args()
        
        # Supabase-এর users টেবিল থেকে সব ইউজারের আইডি আনা হচ্ছে
        res = await asyncio.to_thread(supabase.table("users").select("user_id").execute)
        
        if res.data:
            for user in res.data:
                try: 
                    await bot.send_message(user['user_id'], text)
                except: 
                    pass
                    
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
            uid = int(data['target_id'])
            
            # Supabase থেকে বর্তমান ব্যালেন্স আনা
            bal_res = await asyncio.to_thread(supabase.table("balances").select("main_balance").eq("user_id", uid).execute)
            
            if bal_res.data:
                current_bal = bal_res.data[0].get('main_balance', 0)
                new_bal = current_bal + amount
                # নতুন ব্যালেন্স আপডেট করা
                await asyncio.to_thread(supabase.table("balances").update({"main_balance": new_bal}).eq("user_id", uid).execute)
            else:
                # যদি ডাটা না থাকে, নতুন করে ইনসার্ট করা
                await asyncio.to_thread(supabase.table("balances").insert({"user_id": uid, "main_balance": amount}).execute)
                
            await bot.send_message(uid, f"✅আপনার একাউন্টে {amount} ৳ যোগ করেছে।")
            await message.answer(f"✅ {amount} ৳ সফলভাবে যোগ করা হয়েছে।")
        except Exception as e: 
            await message.answer("❌ ভুল ইনপুট।")
        await state.finish()

# ==========================================
# --- অ্যাডমিন প্যানেল: ইউজার সার্চ ও বিস্তারিত রিপোর্ট ---
@dp.message_handler(commands=['search'], user_id=ADMIN_ID)
async def admin_search(message: types.Message):
    args = message.get_args()
    if not args: return await message.answer("⚠️ আইডি দিন। যেমন: `/search 12345678`")
    
    try:
        target_id = int(args)
        
        # ব্যালেন্স এবং পেমেন্ট মেথড আনা
        bal_res = await asyncio.to_thread(supabase.table("balances").select("main_balance").eq("user_id", target_id).execute)
        pay_res = await asyncio.to_thread(supabase.table("payment_methods").select("bkash_num, nagad_num, rocket_num, binance_id, recharge_num").eq("user_id", target_id).execute)
        
        if bal_res.data:
            balance = bal_res.data[0].get('main_balance', 0)
            
            # পেমেন্ট মেথড চেক করা (যেকোনো একটি সেভ করা নম্বর দেখানোর জন্য)
            address = "নেই"
            if pay_res.data:
                p = pay_res.data[0]
                address = p.get('bkash_num') or p.get('nagad_num') or p.get('rocket_num') or p.get('binance_id') or p.get('recharge_num') or "নেই"
            
            import datetime
            today = datetime.date.today().strftime("%Y-%m-%d")
            
            # আজকের কাজের হিসাব (daily_stats টেবিল থেকে)
            stats_res = await asyncio.to_thread(supabase.table("daily_stats").select("file_count, single_id_count").eq("user_id", target_id).eq("date", today).execute)
            
            if stats_res.data:
                s_file = stats_res.data[0].get('file_count', 0)
                s_single = stats_res.data[0].get('single_id_count', 0)
            else:
                s_file, s_single = 0, 0
            
            text = (f"👤 **ইউজার রিপোর্ট (ID: `{target_id}`)**\n\n"
                    f"💵 ব্যালেন্স: {balance} টাকা\n"
                    f"💳 পেমেন্ট মেথড: `{address}`\n"
                    f"📊 আজ জমা দিয়েছে:\n"
                    f"📁 ফাইল: {s_file} টি\n"
                    f"👤 সিঙ্গেল আইডি: {s_single} টি")
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
        
        # Supabase-এর blacklist টেবিলে সেভ করা (upsert ব্যবহার করা হলো যাতে আগে থেকে থাকলে এরর না দেয়)
        await asyncio.to_thread(supabase.table("blacklist").upsert({"user_id": uid}).execute)
        
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
        
        # Supabase থেকে আনব্লক (ডিলিট) করা
        await asyncio.to_thread(supabase.table("blacklist").delete().eq("user_id", uid).execute)
        
        await message.answer(f"✅ ইউজার `{uid}` এখন আনব্লক।")
        await bot.send_message(uid, "✅ আপনাকে আনব্লক করা হয়েছে।\nআর ভুল করবেন না❌")
        
    except: 
        await message.answer("সঠিক ফরম্যাট: `/unblock আইডি`")

@dp.callback_query_handler(lambda c: c.data.startswith('block_'), user_id=ADMIN_ID)
async def block_callback(call: types.CallbackQuery, state: FSMContext):
    uid = int(call.data.split('_')[1])
    
    # Supabase-এর blacklist টেবিলে সেভ করা
    await asyncio.to_thread(supabase.table("blacklist").upsert({"user_id": uid}).execute)
    
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
        await state.finish() # এরর হলেও স্টেট ক্লিয়ার করা ভালো

@dp.message_handler(commands=['edit_ref'], user_id=ADMIN_ID)
async def admin_edit_referral(message: types.Message):
    try:
        args = message.get_args().split()
        if len(args) < 2:
            return await message.answer("⚠️ ফরম্যাট: `/edit_ref আইডি সংখ্যা`")
        
        target_id, new_count = int(args[0]), int(args[1])
        
        # Supabase-এর balances টেবিলে রেফারেল সংখ্যা আপডেট করা
        await asyncio.to_thread(supabase.table("balances").update({"referral_count": new_count}).eq("user_id", target_id).execute)
        
        await message.answer(f"✅ ইউজার `{target_id}` এর রেফারেল সংখ্যা আপডেট করে `{new_count}` করা হয়েছে।")
        try:
            await bot.send_message(target_id, f"📢 আপনার মোট রেফারেল সংখ্যা আপডেট করা হয়েছে।\nবর্তমান রেফারেল: {new_count} জন।")
        except: 
            pass
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
@dp.message_handler(state=BotState.waiting_for_single_2fa)
async def send_to_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id 
    
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
        
        final_category = f"{category} [✅ Single]"
        
        # ২ ও ৩. Supabase-এর user_id_logs টেবিলে সরাসরি সেভ করা (SQLite এর বদলে)
        import datetime
        bd_now = datetime.datetime.now() + datetime.timedelta(hours=6)
        dt_log = bd_now.strftime("%d/%m/%Y %I:%M %p") 
        
        log_data = {
            "user_id": user_id, 
            "category": final_category, 
            "u_id": str(uid), 
            "u_pass": str(pw), 
            "two_fa": str(two_fa), 
            "date_time": dt_log
        }
        await asyncio.to_thread(supabase.table("user_id_logs").insert(log_data).execute)
        
        # ৪. ব্যালেন্স আপডেট করা (balances টেবিলের pending_balance এ)
        id_price = 4.5 
        bal_res = await asyncio.to_thread(supabase.table("balances").select("pending_balance").eq("user_id", user_id).execute)
        if bal_res.data:
            current_pending = bal_res.data[0].get('pending_balance', 0)
            await asyncio.to_thread(supabase.table("balances").update({"pending_balance": current_pending + id_price}).eq("user_id", user_id).execute)
        
        # ৫. ইউজারের সিঙ্গেল আইডি কাউন্ট বাড়ানো (daily_stats টেবিলে)
        today = datetime.date.today().strftime("%Y-%m-%d")
        stats_res = await asyncio.to_thread(supabase.table("daily_stats").select("single_id_count").eq("user_id", user_id).eq("date", today).execute)
        
        if stats_res.data:
            current_count = stats_res.data[0].get('single_id_count', 0)
            await asyncio.to_thread(supabase.table("daily_stats").update({"single_id_count": current_count + 1}).eq("user_id", user_id).eq("date", today).execute)
        else:
            await asyncio.to_thread(supabase.table("daily_stats").insert({"user_id": user_id, "date": today, "single_id_count": 1}).execute)
        
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
    
    try:
        # ১. ব্যালেন্স ইনফো আনা (balances টেবিল থেকে)
        balance_res = await asyncio.to_thread(supabase.table("balances").select("main_balance, pending_balance").eq("user_id", user_id).execute)
        
        if balance_res.data:
            balance = balance_res.data[0].get('main_balance', 0)
            pending_balance = balance_res.data[0].get('pending_balance', 0)
        else:
            balance = pending_balance = 0

        # ২. পেমেন্ট মেথড ইনফো আনা (payment_methods টেবিল থেকে)
        payment_res = await asyncio.to_thread(supabase.table("payment_methods").select("bkash_num, nagad_num, rocket_num, binance_id, recharge_num").eq("user_id", user_id).execute)
        
        if payment_res.data:
            p_data = payment_res.data[0]
            bkash = p_data.get('bkash_num')
            nagad = p_data.get('nagad_num')
            rocket = p_data.get('rocket_num')
            binance = p_data.get('binance_id')
            recharge = p_data.get('recharge_num')
        else:
            bkash = nagad = rocket = binance = recharge = None

        # ৩. কাজের স্ট্যাটাস আনা (daily_stats টেবিল থেকে ইউজারের সব দিনের কাজের যোগফল)
        stats_res = await asyncio.to_thread(supabase.table("daily_stats").select("file_count, single_id_count").eq("user_id", user_id).execute)
        
        if stats_res.data:
            # যতদিনের কাজ আছে সবগুলোর count যোগ করা হচ্ছে
            file_count = sum(item.get('file_count', 0) for item in stats_res.data)
            single_id_count = sum(item.get('single_id_count', 0) for item in stats_res.data)
        else:
            file_count = single_id_count = 0

    except Exception as e:
        # যদি ডাটাবেসে কানেক্ট হতে কোনো সমস্যা হয়
        print(f"Status check error: {e}")
        return await message.answer("❌ দুঃখিত, ডাটাবেস থেকে আপনার তথ্য আনতে সমস্যা হচ্ছে। একটু পর আবার চেষ্টা করুন।")

    # মেসেজ ফরম্যাট (HTML এ কনভার্ট করা হয়েছে)
    status_msg = (
        f"👤 <b>আপনার প্রোফাইল স্ট্যাটাস</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ইউজার আইডি:</b> <code>{user_id}</code>\n"
        f"💰 <b>মেইন ব্যালেন্স:</b> {balance} BDT\n"
        f"⏳ <b>পেন্ডিং ব্যালেন্স:</b> {pending_balance} BDT\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📁 <b>মোট ফাইল:</b> {file_count} টি\n"
        f"🆔 <b>সিঙ্গেল আইডি:</b> {single_id_count} টি\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>সেভ করা পেমেন্ট মেথড:</b>\n"
        f"📱 রিচার্জ: <code>{recharge if (recharge and recharge != 'Not Set') else 'সেট নেই'}</code>\n"
        f"🟢 বিকাশ: <code>{bkash if (bkash and bkash != 'Not Set') else 'সেট নেই'}</code>\n"
        f"🟠 নগদ: <code>{nagad if (nagad and nagad != 'Not Set') else 'সেট নেই'}</code>\n"
        f"💜 রকেট: <code>{rocket if (rocket and rocket != 'Not Set') else 'সেট নেই'}</code>\n"
        f"🟡 বিন্যান্স: <code>{binance if (binance and binance != 'Not Set') else 'সেট নেই'}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"পেন্ডিং ব্যালেন্স এডমিন চেক করে মেইন ব্যালেন্সে দিয়ে দিবে। 🔥"
    )
    
    await message.answer(status_msg, parse_mode="HTML")

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
    try:
        # Supabase থেকে সব ইউজারের ডাটা আনা
        res = await asyncio.to_thread(supabase.table("users").select("user_id, username").execute)
        users = res.data
        
        if not users:
            return await message.answer("❌ ডাটাবেসে কোনো ইউজার পাওয়া যায়নি।")
        
        # ইনচার্জ বা অ্যাডমিনের জন্য মেসেজ হেডার
        response_text = "👥 **বটের সকল ইউজার লিস্ট:**\n━━━━━━━━━━━━━━━\n"
        
        count = 0
        for index, user in enumerate(users, 1):
            uid = user.get('user_id')
            uname = user.get('username')
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
            
    except Exception as e:
        print(f"All users fetch error: {e}")
        await message.answer("❌ ডাটাবেস থেকে ইউজার লিস্ট আনতে সমস্যা হয়েছে।")
        
import datetime
@dp.message_handler(commands=['todaystats'], user_id=ADMIN_ID)
async def get_today_stats(message: types.Message):
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        # ১. Supabase থেকে সব ইউজার এবং তাদের আজকের কাজের তথ্য আনা
        users_res = await asyncio.to_thread(supabase.table("users").select("user_id, username").execute)
        stats_res = await asyncio.to_thread(supabase.table("daily_stats").select("user_id, file_count, single_id_count").eq("date", today).execute)
        
        if not users_res.data:
            return await message.answer("❌ ডাটাবেসে কোনো ইউজার পাওয়া যায়নি।")

        # আজকের কাজের ডাটাগুলো সহজে মেলানোর জন্য একটি ডিকশনারি (Dictionary) তৈরি করা
        today_stats = {}
        if stats_res.data:
            for stat in stats_res.data:
                today_stats[stat['user_id']] = stat

        worked_list = []      # যারা কাজ করেছে
        not_worked_list = []  # যারা কাজ করেনি

        # ২. ইউজারদের ডাটা চেক করে লিস্টে যোগ করা
        for user in users_res.data:
            uid = user.get('user_id')
            uname = user.get('username')
            username = uname if uname else "No Username"

            # ইউজারের আজকের কাজ আছে কি না চেক করা
            user_stat = today_stats.get(uid, {})
            f_count = user_stat.get('file_count', 0)
            s_count = user_stat.get('single_id_count', 0)

            if f_count > 0 or s_count > 0:
                worked_list.append(f"✅ 🆔 `{uid}` | {username}\n   └📁 ফাইল: {f_count} | 🆔 সিঙ্গেল: {s_count}")
            else:
                not_worked_list.append(f"❌ 🆔 `{uid}` | {username}")

        # ৩. মেসেজ সাজানো
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

        # ৪. মেসেজ পাঠানো (অনেক বড় হলে ভাগ করে পাঠানো)
        if len(response_text) > 3500:
            # মেসেজ খুব বড় হলে পার্ট পার্ট করে পাঠানো
            for i in range(0, len(response_text), 4000):
                await message.answer(response_text[i:i+4000], parse_mode="Markdown")
        else:
            await message.answer(response_text, parse_mode="Markdown")
            
    except Exception as e:
        print(f"Today stats error: {e}")
        await message.answer("❌ ডাটাবেস থেকে রিপোর্ট আনতে সমস্যা হয়েছে।")
                                     
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
        
        # ১. রেফারার থাকলে তাকে কমিশন দেওয়া (users এবং balances টেবিল ব্যবহার করে)
        usr_res = await asyncio.to_thread(supabase.table("users").select("referred_by").eq("user_id", user_id).execute)
        
        if usr_res.data and usr_res.data[0].get('referred_by') != 0:
            referrer_id = usr_res.data[0].get('referred_by')
            
            # রেফারারের বর্তমান রেফার ব্যালেন্স আনা
            ref_bal_res = await asyncio.to_thread(supabase.table("balances").select("refer_balance").eq("user_id", referrer_id).execute)
            
            if ref_bal_res.data:
                current_ref_bal = ref_bal_res.data[0].get('refer_balance', 0)
                # রেফার ব্যালেন্স আপডেট করা
                await asyncio.to_thread(supabase.table("balances").update({"refer_balance": current_ref_bal + commission}).eq("user_id", referrer_id).execute)
                
                try:
                    await bot.send_message(referrer_id, f"🎁 আপনি রেফার কমিশন পেয়েছেন: {commission} ৳")
                except:
                    pass
        
        await call.message.edit_text(f"✅ ইউজার {user_id} এর {amount} ৳ উইথড্র সফলভাবে অ্যাপ্রুভ করা হয়েছে।")
        try:
            await bot.send_message(user_id, f"✅ আপনার {amount} ৳ উইথড্র রিকোয়েস্টটি অ্যাপ্রুভ করা হয়েছে।")
        except:
            pass

    elif action == "reject":
        # ২. রিজেক্ট করলে ইউজারের ব্যালেন্স ফেরত দেওয়া (balances টেবিল থেকে)
        bal_res = await asyncio.to_thread(supabase.table("balances").select("main_balance, withdraw_count").eq("user_id", user_id).execute)
        
        if bal_res.data:
            current_bal = bal_res.data[0].get('main_balance', 0)
            current_wd = bal_res.data[0].get('withdraw_count', 0)
            
            # ব্যালেন্স ফেরত এবং উইথড্র কাউন্ট কমানো
            await asyncio.to_thread(supabase.table("balances").update({
                "main_balance": current_bal + amount, 
                "withdraw_count": current_wd - 1
            }).eq("user_id", user_id).execute)
            
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
        return await message.answer("⚠️ নিয়ম: <code>/add_fake NAME BALANCE</code> \nউদাহরণ: <code>/add_fake Worker1 5000</code>", parse_mode="HTML")

    fake_name = args[0].replace("_", " ")
    try:
        balance = float(args[1])
    except:
        return await message.answer("❌ ব্যালেন্স অবশ্যই নম্বর হতে হবে।")

    # ফেক ইউআইডি জেনারেট
    fake_uid = random.randint(1000000000, 9999999999) 

    try:
        # Supabase-এ সেভ (users এবং balances দুটি টেবিলে আলাদা করে)
        await asyncio.to_thread(supabase.table("users").insert({"user_id": fake_uid, "username": fake_name}).execute)
        await asyncio.to_thread(supabase.table("balances").insert({"user_id": fake_uid, "main_balance": balance}).execute)

        await message.answer(f"✅ ফেক ইউজার যুক্ত হয়েছে!\n🆔 UID: <code>{fake_uid}</code>\n💰 ব্যালেন্স: {balance} ৳", parse_mode="HTML")
    except Exception as e:
        await message.answer("❌ ডাটাবেসে সেভ করতে এরর হয়েছে।")

# ২. লিডারবোর্ড দেখানো
@dp.message_handler(lambda message: message.text == "🏆LEADERBOARD")
async def show_leaderboard(message: types.Message):
    user_id = message.from_user.id
    
    # আপনার চেক ব্লক ফাংশনটি
    if await is_blocked(user_id):
        return await message.answer("❌ দুঃখিত, আপনাকে ব্লক করা হয়েছে। \n\n✅আপনি 24 hrs পরে বটটি ব্যবহার করতে পারবেন না।")
        
    try:
        # এটি balances টেবিলের সবার মধ্যে তুলনা করে টপ ৫ জনের UID এবং Balance আনবে
        top_res = await asyncio.to_thread(supabase.table("balances").select("user_id, main_balance").order("main_balance", desc=True).limit(5).execute)
        top_rows = top_res.data

        if not top_rows:
            return await message.answer("🏆 লিডারবোর্ড এখনো খালি!")

        # ইউজারের নিজের পজিশন কত নম্বরে সেটা বের করা
        # প্রথমে নিজের ব্যালেন্স চেক
        my_bal_res = await asyncio.to_thread(supabase.table("balances").select("main_balance").eq("user_id", user_id).execute)
        my_balance = my_bal_res.data[0].get('main_balance', 0) if my_bal_res.data else 0
        
        # এরপর নিজের থেকে বেশি ব্যালেন্স কতজনের আছে তা বের করে র‍্যাংক হিসাব করা
        rank_res = await asyncio.to_thread(supabase.table("balances").select("user_id").gt("main_balance", my_balance).execute)
        user_rank = len(rank_res.data) + 1 if rank_res.data else 1

        # মেসেজ তৈরি (সম্পূর্ণ HTML ফরম্যাটে)
        text = "🏆 <b>সর্বোচ্চ ব্যালেন্সধারী ৫ জন কর্মী</b> 🏆\n"
        text += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        
        for i, row in enumerate(top_rows):
            uid = row.get('user_id')
            balance = row.get('main_balance')
            
            emoji = emojis[i] if i < len(emojis) else f"{i+1}️⃣"
            
            # এখানে আসল বা ফেক যার ব্যালেন্স বেশি হবে, তার UID-ই উপরে দেখাবে
            text += f"{emoji} <b>UID:</b> <code>{uid}</code>\n└─ 💰 ব্যালেন্স: {balance} ৳\n\n"

        text += "━━━━━━━━━━━━━━━━━━━\n"
        text += f"🎯 <b>আপনার বর্তমান পজিশন:</b> {user_rank} নম্বর!\n"
        text += "🔥 বেশি কাজ করে লিডারবোর্ডের শীর্ষে আসুন!"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        print(f"Leaderboard error: {e}")
        await message.answer("❌ লিডারবোর্ড লোড করতে সমস্যা হচ্ছে।")
# ৩. ফেক বা রিয়েল ইউজারের ব্যালেন্স এডিট করার কমান্ড (অ্যাডমিনের জন্য)
@dp.message_handler(commands=['edit_fake'], user_id=ADMIN_ID)
async def edit_fake_balance(message: types.Message):
    args = message.get_args().split()
    if len(args) != 2:
        return await message.answer("⚠️ নিয়ম: <code>/edit_fake USER_ID NEW_BALANCE</code>", parse_mode="HTML")

    target_uid = args[0]
    try:
        new_balance = float(args[1])
    except:
        return await message.answer("❌ ব্যালেন্স নম্বর হতে হবে।")

    try:
        # Supabase-এর balances টেবিলে ব্যালেন্স আপডেট করা
        await asyncio.to_thread(supabase.table("balances").update({"main_balance": new_balance}).eq("user_id", target_uid).execute)
        
        await message.answer(f"✅ সাকসেস!\n🆔 আইডি: <code>{target_uid}</code>\n💰 ব্যালেন্স সেট: <code>{new_balance}</code> ৳", parse_mode="HTML")
    except Exception as e:
        await message.answer("❌ ব্যালেন্স আপডেট করতে সমস্যা হয়েছে।")

# ৪. ফেক বা রিয়েল ইউজার ডিলিট করার কমান্ড
@dp.message_handler(commands=['del_fake'], user_id=ADMIN_ID)
async def delete_fake_user(message: types.Message):
    # নিয়ম: /del_fake [ইউজার_আইডি]
    args = message.get_args().split()
    
    if len(args) != 1:
        return await message.answer("⚠️ সঠিক নিয়ম: <code>/del_fake USER_ID</code> \n\n"
                                   "উদাহরণ: <code>/del_fake 123456</code> \n"
                                   "(লিডারবোর্ড থেকে আইডি কপি করে এখানে বসান)", parse_mode="HTML")

    target_uid = args[0]

    try:
        # সব টেবিল থেকে ওই আইডির ডাটা মুছে ফেলা
        await asyncio.to_thread(supabase.table("users").delete().eq("user_id", target_uid).execute)
        await asyncio.to_thread(supabase.table("balances").delete().eq("user_id", target_uid).execute)
        await asyncio.to_thread(supabase.table("daily_stats").delete().eq("user_id", target_uid).execute)
        await asyncio.to_thread(supabase.table("payment_methods").delete().eq("user_id", target_uid).execute)
        await asyncio.to_thread(supabase.table("user_id_logs").delete().eq("user_id", target_uid).execute)
        
        await message.answer(f"🗑️ সফলভাবে ডিলিট করা হয়েছে!\n🆔 আইডি: <code>{target_uid}</code> এখন আর ডাটাবেস বা লিডারবোর্ডে দেখাবে না।", parse_mode="HTML")
    except Exception as e:
        await message.answer("❌ ইউজার ডিলিট করতে কারিগরি সমস্যা হয়েছে।")
    # ==========================================
# ব্লক করা ইউজারদের তালিকা দেখার কমান্ড
# ==========================================
@dp.message_handler(commands=['check_blocks'], user_id=ADMIN_ID)
async def list_blocked_users(message: types.Message):
    try:
        # Supabase থেকে ব্লকড ইউজারদের তথ্য আনা
        bl_res = await asyncio.to_thread(supabase.table("blacklist").select("user_id").execute())
        blocked_list = bl_res.data

        if not blocked_list:
            return await message.answer("✅ বর্তমানে কোনো ইউজার ব্লক নেই।")

        response = "🚫 <b>ব্লক করা ইউজারদের তালিকা:</b>\n\n"
        for index, row in enumerate(blocked_list, start=1):
            uid = row.get('user_id')
            
            # ইউজারনেম খুঁজে বের করার চেষ্টা করা (users টেবিল থেকে)
            usr_res = await asyncio.to_thread(supabase.table("users").select("username").eq("user_id", uid).execute())
            
            username = f"@{usr_res.data[0].get('username')}" if usr_res.data and usr_res.data[0].get('username') else "নাম পাওয়া যায়নি"
            response += f"{index}. ID: <code>{uid}</code> | User: {username}\n"

        await message.answer(response, parse_mode="HTML")
    except Exception as e:
        await message.answer("❌ ডাটাবেস থেকে ব্লকলিস্ট আনতে সমস্যা হয়েছে।")


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
            await bot.send_message(target_uid, f"✅ <b>আপনার উইথড্র অ্যাপ্রুভ হয়েছে!</b>\n💰 পরিমাণ: {amount} ৳\nটাকা আপনার একাউন্টে পাঠিয়ে দেওয়া হয়েছে।", parse_mode="HTML")
        except: pass
            
        # ২. অ্যাডমিন মেসেজ আপডেট (এখানে আর কোনো প্রশ্ন করবে না)
        await call.message.edit_text(call.message.html_text + f"\n\n✅ <b>Status: Approved (সফল)</b>", parse_mode="HTML")
        await call.answer("পেমেন্ট অ্যাপ্রুভড!", show_alert=True)

    elif action == "reject":
        try:
            # টাকা ফেরত দেওয়া (balances টেবিল থেকে)
            bal_res = await asyncio.to_thread(supabase.table("balances").select("main_balance").eq("user_id", target_uid).execute())
            if bal_res.data:
                current_bal = bal_res.data[0].get('main_balance', 0)
                await asyncio.to_thread(supabase.table("balances").update({"main_balance": current_bal + amount}).eq("user_id", target_uid).execute())
            
            try:
                await bot.send_message(target_uid, f"❌ <b>আপনার উইথড্র রিজেক্ট করা হয়েছে।</b>\n💰 {amount} ৳ ফেরত দেওয়া হয়েছে।", parse_mode="HTML")
            except: pass
                
            await call.message.edit_text(call.message.html_text + "\n\n❌ <b>Status: Rejected (টাকা ফেরত)</b>", parse_mode="HTML")
            await call.answer("রিজেক্ট করা হয়েছে!", show_alert=True)
            
        except Exception as e:
            await call.answer("❌ টাকা রিফান্ড করতে সমস্যা হয়েছে।", show_alert=True)
        
# --- ধাপ ২: রেফারেল মেনু আপডেট (Supabase ভার্সন) ---
@dp.message_handler(lambda message: message.text == "🎁INVITE BONUS")
async def referral_menu(message: types.Message):
    user_id = message.from_user.id
    
    try:
        # Supabase-এর balances টেবিল থেকে রেফার ও মেইন ব্যালেন্স আনা
        res = await asyncio.to_thread(supabase.table("balances").select("refer_balance, main_balance, referral_count").eq("user_id", user_id).execute)
        
        if res.data:
            ref_balance = res.data[0].get('refer_balance', 0)
            main_balance = res.data[0].get('main_balance', 0)
            total_ref = res.data[0].get('referral_count', 0)
        else:
            ref_balance = main_balance = total_ref = 0
            
        # ইনলাইন কিবোর্ড তৈরি
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("💰 Add to Main Balance", callback_data="transfer_ref_request"),
            types.InlineKeyboardButton("📜 Rules", callback_data="ref_rules"),
            types.InlineKeyboardButton("📋 Refer List", callback_data="view_ref_list")
        )
        
        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        text = (
            f"👥 <b>রেফারেল ড্যাশবোর্ড</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>মোট রেফারেল:</b> <code>{total_ref} জন</code>\n"
            f"💵 <b>রেফার ব্যালেন্স:</b> <code>{ref_balance:.2f} ৳</code>\n"
            f"💰 <b>মেইন ব্যালেন্স:</b> <code>{main_balance:.2f} ৳</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>আপনার রেফার লিংক:</b>\n<code>{ref_link}</code>\n\n"
            f"✨ রেফার ব্যালেন্স মেইন ব্যালেন্সে নিতে নিচের বাটনে ক্লিক করুন। 👇"
        )
        
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        await message.answer("❌ রেফারেল তথ্য লোড করতে সমস্যা হয়েছে।")

# --- ১. ইউজার যখন বাটনে ক্লিক করবে (ট্রান্সফার রিকোয়েস্ট) ---
@dp.callback_query_handler(text="transfer_ref_request")
async def ask_transfer_amount(call: types.CallbackQuery, state: FSMContext):
    # রেফার ট্রান্সফার এনাবল কি না চেক করা
    if not REFER_ADD_ENABLED:
        return await call.answer("⚠️ বর্তমানে রেফার ব্যালেন্স ট্রান্সফার অপশনটি সাময়িকভাবে বন্ধ আছে।\n🔊⏰খোলার সময় রাত ছয়টা থেকে বারোটা পর্যন্ত", show_alert=True)
    
    user_id = call.from_user.id
    
    try:
        # ডাটাবেস থেকে রেফার ব্যালেন্স চেক করা
        res = await asyncio.to_thread(supabase.table("balances").select("refer_balance").eq("user_id", user_id).execute)
        ref_bal = res.data[0].get('refer_balance', 0) if res.data else 0
        
        if ref_bal <= 0:
            return await call.answer("⚠️ আপনার কোনো রেফার ব্যালেন্স নেই!", show_alert=True)
        
        # স্টেট সেট করা
        await BotState.waiting_for_transfer_amount.set() 
        
        text = (
            f"💰 আপনার বর্তমান রেফার ব্যালেন্স: <code>{ref_bal:.2f} ৳</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"আপনি কত টাকা মেইন ব্যালেন্সে নিতে চান? পরিমাণটি সংখ্যায় লিখুন (যেমন: ২০):"
        )
        await call.message.answer(text, parse_mode="HTML")
        await call.answer()
    except Exception as e:
        await call.answer("❌ ব্যালেন্স চেক করতে সমস্যা হয়েছে।", show_alert=True)
            
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
    
    try:
        # ডাটাবেস থেকে ইউজারের বর্তমান রেফার ব্যালেন্স চেক করা (Supabase balances টেবিল)
        res = await asyncio.to_thread(supabase.table("balances").select("refer_balance").eq("user_id", user_id).execute())
        current_ref_bal = res.data[0].get('refer_balance', 0) if res.data else 0

        # চেক করা হচ্ছে ইউজারের পর্যাপ্ত ব্যালেন্স আছে কি না
        if amount > current_ref_bal:
            await state.finish() # ব্যালেন্স না থাকলে স্টেট বন্ধ করে দেওয়া ভালো
            return await message.answer(f"❌ আপনার পর্যাপ্ত রেফার ব্যালেন্স নেই!\nবর্তমান ব্যালেন্স: <code>{current_ref_bal:.2f} ৳</code>", parse_mode="HTML")

        if amount <= 0:
            return await message.answer("❌ সর্বনিম্ন ১ টাকা ট্রান্সফার করা যাবে।")

        # অ্যাডমিনের জন্য বাটন (ADMIN_ID আপনার ওপরে ডিফাইন করা থাকতে হবে)
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("✅ Add Money", callback_data=f"ref_adm_add_{user_id}_{amount}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"ref_adm_rej_{user_id}_{amount}")
        )

        admin_text = (
            f"🔄 <b>নতুন ব্যালেন্স ট্রান্সফার রিকোয়েস্ট!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 নাম: {message.from_user.full_name}\n"
            f"🆔 আইডি: <code>{user_id}</code>\n"
            f"💰 পরিমাণ: <b>{amount:.2f} ৳</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"অ্যাপ্রুভ করতে নিচের বাটনে ক্লিক করুন।"
        )

        try:
            await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="HTML")
            await message.answer(f"✅ আপনার <b>{amount:.2f} ৳</b> ট্রান্সফার রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।\n⏳ অ্যাডমিন এপ্রুভ করলে মেইন ব্যালেন্সে যোগ হবে।", parse_mode="HTML")
        except Exception as e:
            await message.answer("⚠️ অ্যাডমিনকে মেসেজ পাঠানো সম্ভব হয়নি।")
            
    except Exception as e:
        await message.answer("❌ কারিগরি ত্রুটির কারণে রিকোয়েস্ট পাঠানো যায়নি।")
    
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
        try:
            # ১. Supabase থেকে বর্তমান ব্যালেন্স আনা (balances টেবিল)
            bal_res = await asyncio.to_thread(supabase.table("balances").select("main_balance, refer_balance").eq("user_id", target_uid).execute())
            
            if bal_res.data:
                current_main = bal_res.data[0].get('main_balance', 0)
                current_ref = bal_res.data[0].get('refer_balance', 0)
                
                # মেইন ব্যালেন্স যোগ এবং রেফার ব্যালেন্স বিয়োগ করা
                new_main = current_main + amount
                new_ref = current_ref - amount
                
                # ডাটাবেসে আপডেট করা
                await asyncio.to_thread(supabase.table("balances").update({
                    "main_balance": new_main,
                    "refer_balance": new_ref
                }).eq("user_id", target_uid).execute())

                # ২. ইউজারকে সুখবর পাঠানো (HTML ফরম্যাটে)
                try:
                    success_text = (
                        f"🎉 <b>অভিনন্দন!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"আপনার <b>{amount:.2f} ৳</b> রেফার ব্যালেন্স থেকে মেইন ব্যালেন্সে সফলভাবে যুক্ত হয়েছে।\n"
                        f"এখন আপনি এই টাকা উইথড্র করতে পারবেন। ধন্যবাদ! ✨"
                    )
                    await bot.send_message(target_uid, success_text, parse_mode="HTML")
                except:
                    pass

                # ৩. অ্যাডমিন মেসেজ আপডেট করা
                await call.message.edit_text(call.message.html_text + f"\n\n✅ <b>Status: Money Added to Main Balance</b>", parse_mode="HTML")
                await call.answer("টাকা সফলভাবে মেইন ব্যালেন্সে যোগ হয়েছে!", show_alert=True)
            else:
                await call.answer("❌ ইউজারের ডাটাবেস তথ্য পাওয়া যায়নি!", show_alert=True)
                
        except Exception as e:
            await call.answer("❌ ডাটাবেস আপডেট করতে সমস্যা হয়েছে।", show_alert=True)

    elif action == "rej":
        # রিজেক্ট করলে শুধু স্ট্যাটাস আপডেট হবে (টাকা ইউজারের রেফার ব্যালেন্সেই থেকে যাবে)
        try:
            await bot.send_message(target_uid, f"❌ দুঃখিত! আপনার <b>{amount:.2f} ৳</b> ব্যালেন্স ট্রান্সফার রিকোয়েস্ট অ্যাডমিন রিজেক্ট করেছে।", parse_mode="HTML")
        except:
            pass

        await call.message.edit_text(call.message.html_text + "\n\n❌ <b>Status: Request Rejected</b>", parse_mode="HTML")
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
    
    try:
        # Supabase-এর users টেবিল থেকে শুধু রেফারেলদের আইডি খুঁজে বের করা
        res = await asyncio.to_thread(supabase.table("users").select("user_id").eq("referred_by", user_id).execute())
        ref_users = res.data
        
        # যদি কেউ এখনো কাউকে রেফার না করে থাকে
        if not ref_users:
            return await call.answer("❌ আপনার এখনো কোনো সফল রেফারেল নেই。", show_alert=True)

        text = "📋 <b>আপনার রেফারেল আইডি লিস্ট:</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        
        count = 1
        for ref in ref_users:
            r_id = ref.get('user_id')
            
            # প্রতিটি মেম্বারের শুধু আইডি নম্বরটি দেখাবে
            text += f"{count}. 🆔 <code>{r_id}</code>\n"
            count += 1
            
            # লিস্ট খুব বড় হয়ে গেলে ৫০ জন পর্যন্ত লিমিট রাখা ভালো
            if count > 50:
                text += "\n⚠️ <i>আরো অনেক মেম্বার আছে...</i>"
                break

        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👥 <b>মোট রেফারেল:</b> <code>{len(ref_users)}</code> জন"

        # রেফারেল মেনুতে ফিরে যাওয়ার জন্য ব্যাক বাটন
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_to_ref"))
        
        try:
            await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except:
            await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
            
    except Exception as e:
        await call.answer("❌ ডাটাবেস থেকে তালিকা আনতে সমস্যা হয়েছে।", show_alert=True)
        
@dp.message_handler(commands=['add_user'])
async def admin_add_manual_user(message: types.Message):
    if message.from_user.id != ADMIN_ID: return 

    args = message.get_args().split()
    if len(args) < 2:
        return await message.answer("⚠️ নিয়ম: <code>/add_user আইডি নাম</code>", parse_mode="HTML")

    try:
        new_id = int(args[0])
        name = args[1]
        
        # ১. Users টেবিলে ডাটা ইনসার্ট
        await asyncio.to_thread(supabase.table("users").insert({
            "user_id": new_id, 
            "username": name,
            "referred_by": 0
        }).execute)
        
        # ২. Balances টেবিলে ডিফল্ট ডাটা ইনসার্ট
        await asyncio.to_thread(supabase.table("balances").insert({
            "user_id": new_id,
            "main_balance": 0.0,
            "refer_balance": 0.0,
            "pending_balance": 0.0,
            "referral_count": 0,
            "withdraw_count": 0
        }).execute)
        
        await message.answer(f"✅ সফলভাবে নতুন ইউজার অ্যাড হয়েছে!\n🆔 আইডি: <code>{new_id}</code>\n📛 নাম: <code>{name}</code>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ এরর: এই আইডিটি অলরেডি ডাটাবেসে থাকতে পারে অথবা ইনপুট ভুল।")
@dp.message_handler(commands=['set_ref_bal'])
async def set_user_refer_balance_with_notify(message: types.Message):
    # অ্যাডমিন চেক
    if message.from_user.id != ADMIN_ID: 
        return

    # কমান্ড থেকে আইডি এবং নতুন ব্যালেন্স নেওয়া
    args = message.get_args().split()
    if len(args) < 2:
        return await message.answer("⚠️ সঠিক নিয়ম: <code>/set_ref_bal ইউজার_আইডি নতুন_টাকা</code>", parse_mode="HTML")

    try:
        target_id = int(args[0])
        new_bal = float(args[1])
        
        # ১. Supabase-এর balances টেবিলে রেফার ব্যালেন্স আপডেট করা
        await asyncio.to_thread(supabase.table("balances").update({"refer_balance": new_bal}).eq("user_id", target_id).execute)
        
        # ২. অ্যাডমিনকে কনফার্মেশন মেসেজ দেওয়া
        await message.answer(f"✅ ইউজার <code>{target_id}</code> এর রেফার ব্যালেন্স আপডেট করে <code>{new_bal:.2f} ৳</code> করা হয়েছে।", parse_mode="HTML")

        # ৩. ইউজারের কাছে অটোমেটিক মেসেজ পাঠানো
        notification_text = (
            f"🔔 <b>ব্যালেন্স আপডেট নোটিশ!</b>\n\n"
            f"অ্যাডমিন আপনার রেফারেল ব্যালেন্স আপডেট করেছেন।\n"
            f"💰 <b>আপনার বর্তমান রেফার ব্যালেন্স:</b> <code>{new_bal:.2f} ৳</code>"
        )
        
        try:
            await bot.send_message(target_id, notification_text, parse_mode="HTML")
        except Exception:
            # যদি ইউজার বট ব্লক করে রাখে বা আইডি ভুল হয়
            await message.answer(f"⚠️ ব্যালেন্স আপডেট হয়েছে, কিন্তু ইউজারকে মেসেজ পাঠানো যায়নি (বট ব্লক থাকতে পারে)।")

    except ValueError:
        await message.answer("❌ ভুল ফরম্যাট! আইডি এবং টাকা সঠিকভাবে সংখ্যায় দিন।")
    except Exception as e:
        await message.answer(f"❌ একটি এরর হয়েছে: {str(e)}")
    
# সব ইউজারের জন্য প্রোফাইল লিঙ্ক দেখার কমান্ড
# ==========================================
@dp.message_handler(commands=['users'], user_id=ADMIN_ID)
async def list_all_users(message: types.Message):
    try:
        # Supabase থেকে সব ইউজারের আইডি নিয়ে আসা
        res = await asyncio.to_thread(supabase.table("users").select("user_id").execute)
        all_users = res.data

        if not all_users:
            return await message.answer("<b>⚠️ ডাটাবেসে কোনো ইউজার পাওয়া যায়নি।</b>", parse_mode="HTML")

        response_text = "<b>📊 বটের ইউজার তালিকা:</b>\n\n"
        
        for index, user in enumerate(all_users, start=1):
            u_id = user.get('user_id')

            # প্রোফাইল লিঙ্কসহ ইউজারের তথ্য
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
        
        # আবার চেক করা হচ্ছে ইউজার গ্রুপে জয়েন করেছে কি না (আপনার check_joined ফাংশন অনুযায়ী)
        is_member = await check_joined(user_id)
        
        if is_member:
            # সুন্দর সাকসেস মেসেজ (অ্যালার্ট হিসেবে দেখাবে)
            await callback_query.answer(
                "✨ অভিনন্দন! আপনি সফলভাবে আমাদের গ্রুপে যোগ দিয়েছেন। এখন আপনি বটটি ব্যবহার করতে পারবেন।", 
                show_alert=True
            )
            
            # আগের "জয়েন করুন" মেসেজটি মুছে ফেলা হবে
            try:
                await callback_query.message.delete()
            except:
                pass
            
            # ইউজারকে মেইন মেনুতে নিয়ে যাওয়ার জন্য স্টার্ট ফাংশনটি কল করা
            # নিশ্চিত করুন আপনার কোডে 'start' ফাংশনটি (async def start) ডিফাইন করা আছে
            await start(callback_query.message, state)
            
        else:
            # জয়েন না করলে লাল চিহ্নে সুন্দর সতর্কবার্তা
            await callback_query.answer(
                "⚠️ আপনি এখনো আমাদের গ্রুপে জয়েন করেননি!\n\nদয়া করে প্রথমে গ্রুপে জয়েন করুন, তারপর এই বাটনে আবার ক্লিক করুন।", 
                show_alert=True
            )
            
    except Exception as e:
        # কোনো যান্ত্রিক ত্রুটি হলে বট বন্ধ হবে না
        print(f"Check join error: {e}")
        await callback_query.answer("❌ একটি ত্রুটি হয়েছে। পুনরায় চেষ্টা করুন।", show_alert=False)
            
import io

# --- অ্যাডমিন কমান্ড: প্রোফাইল লিঙ্ক ও সব পেমেন্ট মেথডসহ রিপোর্ট (Supabase) ---
@dp.message_handler(commands=['getusers'], user_id=ADMIN_ID)
async def export_users_txt(message: types.Message):
    try:
        # ১. Supabase থেকে ডাটা আনা (users, balances, payment_methods)
        usr_res = await asyncio.to_thread(supabase.table("users").select("user_id").execute)
        bal_res = await asyncio.to_thread(supabase.table("balances").select("user_id, main_balance, referral_count").execute)
        pay_res = await asyncio.to_thread(supabase.table("payment_methods").select("user_id, bkash_num, nagad_num, recharge_num").execute)
        
        if not usr_res.data:
            return await message.answer("❌ ডাটাবেসে কোনো ইউজার পাওয়া যায়নি!")

        # ডাটাগুলো মেলানোর জন্য ডিকশনারি তৈরি করা
        balances = {item['user_id']: item for item in bal_res.data}
        payments = {item['user_id']: item for item in pay_res.data}

        # টেক্সট ফাইলের হেডার তৈরি
        output = "--- ইউজার রিপোর্ট (প্রোফাইল লিঙ্ক ও পেমেন্ট মেথডসহ) ---\n"
        output += f"মোট ইউজার সংখ্যা: {len(usr_res.data)}\n"
        output += "-" * 140 + "\n"
        output += f"{'SL':<5} | {'User ID':<12} | {'Balance':<10} | {'Refer':<7} | {'Profile Link':<30} | {'bKash':<13} | {'Nagad':<13} | {'Recharge'}\n"
        output += "-" * 140 + "\n"
        
        serial = 1
        for user in usr_res.data:
            u_id = user.get('user_id')
            
            # ব্যালেন্স এবং রেফার তথ্য নেওয়া
            u_bal_info = balances.get(u_id, {})
            balance = u_bal_info.get('main_balance', 0.0)
            referrals = u_bal_info.get('referral_count', 0)
            
            # পেমেন্ট তথ্য নেওয়া
            u_pay_info = payments.get(u_id, {})
            bkash = u_pay_info.get('bkash_num', "None")
            nagad = u_pay_info.get('nagad_num', "None")
            recharge = u_pay_info.get('recharge_num', "None")
            
            # প্রোফাইল লিঙ্ক
            chat_link = f"https://t.me/{u_id}" 
            
            # প্রতিটি লাইন সুন্দরভাবে সাজানো
            output += f"{serial:<5} | {u_id:<12} | {balance:<10.2f} | {referrals:<7} | {chat_link:<30} | {str(bkash):<13} | {str(nagad):<13} | {str(recharge)}\n"
            serial += 1

        output += "-" * 140 + "\n"
        output += "রিপোর্ট জেনারেট হয়েছে: আপনার বটের সিকিউর অ্যাডমিন প্যানেল"

        # মেমোরিতে ফাইলটি তৈরি করা
        buf = io.BytesIO(output.encode('utf-8'))
        buf.name = "user_payment_details.txt"

        # অ্যাডমিনকে ফাইলটি পাঠিয়ে দেওয়া
        await bot.send_document(
            message.chat.id, 
            buf, 
            caption=f"✅ সফলভাবে {len(usr_res.data)} জন ইউজারের পূর্ণাঙ্গ রিপোর্ট তৈরি করা হয়েছে।\n\n"
                    f"এই ফাইলে ইউজারদের ব্যালেন্স, প্রোফাইল লিঙ্ক এবং পেমেন্ট নম্বরগুলো সিরিয়াল অনুযায়ী আছে।"
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        await message.answer(f"❌ ডাটা এক্সপোর্ট করতে সমস্যা হয়েছে।")
    
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
        return await message.answer("❌ ভুল ফরম্যাট! এভাবে লিখুন:\n<code>/edit_pending [ইউজার_আইডি] [টাকার_পরিমাণ]</code>", parse_mode="HTML")

    target_user_id = args[0]
    try:
        new_pending_amount = float(args[1])
    except ValueError:
        return await message.answer("❌ টাকার পরিমাণ অবশ্যই সংখ্যা হতে হবে।")

    try:
        # Supabase-এর balances টেবিলে পেন্ডিং ব্যালেন্স আপডেট করা
        res = await asyncio.to_thread(supabase.table("balances").update({"pending_balance": new_pending_amount}).eq("user_id", target_user_id).execute)

        if res.data:
            await message.answer(f"✅ ইউজার <code>{target_user_id}</code> এর পেন্ডিং ব্যালেন্স আপডেট করে <code>{new_pending_amount}</code> BDT করা হয়েছে।", parse_mode="HTML")
            
            # ইউজারকে নোটিফিকেশন পাঠানো
            try:
                await bot.send_message(target_user_id, f"🔔 আপনার পেন্ডিং ব্যালেন্স আপডেট করা হয়েছে। নতুন পেন্ডিং ব্যালেন্স: {new_pending_amount} BDT")
            except:
                pass
        else:
            await message.answer("❌ এই ইউজার আইডিটি ডাটাবেসে পাওয়া যায়নি।")
            
    except Exception as e:
        await message.answer(f"❌ এরর: {str(e)}")
        

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
        
# ১. নির্দিষ্ট ইউজারের সব আইডি লগ ডিলিট করা
@dp.message_handler(commands=['del_user_data'], user_id=ADMIN_ID)
async def delete_user_all_ids(message: types.Message):
    # কমান্ডটি হবে: /del_user_data [ইউজার_আইডি]
    target_user = message.get_args()
    
    if not target_user:
        return await message.answer("❌ সঠিক নিয়ম: <code>/del_user_data [ইউজার_আইডি]</code>", parse_mode="HTML")
    
    try:
        # প্রথমে চেক করে নিচ্ছি ওই ইউজারের আসলে কয়টি ডাটা আছে
        res = await asyncio.to_thread(supabase.table("user_id_logs").select("count", count="exact").eq("user_id", str(target_user)).execute)
        total_ids = res.count if res.count else 0
        
        if total_ids == 0:
            return await message.answer(f"❌ ইউজার <code>{target_user}</code> এর কোনো ডাটা পাওয়া যায়নি।", parse_mode="HTML")
        
        # এখন ওই ইউজারের সব ডাটা ডিলিট করা হচ্ছে
        await asyncio.to_thread(supabase.table("user_id_logs").delete().eq("user_id", str(target_user)).execute)
        
        await message.answer(f"✅ ইউজার <code>{target_user}</code> এর পাঠানো সকল (<code>{total_ids}</code> টি) আইডি ডাটাবেজ থেকে মুছে ফেলা হয়েছে।", parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ ডাটা ডিলিট করতে সমস্যা হয়েছে: {str(e)}")

# ২. আইডি লগ টেবিল পুরোপুরি খালি করা (অত্যন্ত সাবধানে ব্যবহার করবেন)
@dp.message_handler(commands=['clear_today'], user_id=ADMIN_ID)
async def clear_everything(message: types.Message):
    try:
        # Supabase-এ সব ডাটা ডিলিট করতে হলে সাধারণত একটি ফিল্টার দিতে হয় যা সবার জন্য সত্য
        # এখানে আমরা user_id লগ টেবিলের সব ডাটা মুছে দিচ্ছি (neq 0 মানে সব আইডি)
        await asyncio.to_thread(supabase.table("user_id_logs").delete().neq("user_id", "0").execute)
        
        await message.answer("♻️ <b>লগ ডাটাবেসের সব ডাটা সফলভাবে মুছে ফেলা হয়েছে!</b>\nআপনার ডাটাবেস এখন একদম খালি এবং ফাস্ট।", parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ টেবিল খালি করতে সমস্যা হয়েছে: {str(e)}")
        
@dp.message_handler(commands=['admin_stats'], user_id=ADMIN_ID)
async def get_overall_stats(message: types.Message):
    try:
        # ১. Supabase থেকে মোট কতটি আইডি বা ডাটা জমা হয়েছে তা আনা
        # user_id_logs টেবিল থেকে টোটাল রো কাউন্ট নেওয়া হচ্ছে
        logs_res = await asyncio.to_thread(supabase.table("user_id_logs").select("category", count="exact").execute)
        total_submissions = logs_res.count if logs_res.count else 0

        # ২. ক্যাটাগরি অনুযায়ী আলাদা আলাদা সংখ্যা বের করা
        # পাইথনের মাধ্যমেই ক্যাটাগরিগুলো গুছিয়ে নিচ্ছি
        category_counts = {}
        if logs_res.data:
            for item in logs_res.data:
                cat = item.get('category', 'Unknown')
                category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # ৩. বটের সকল ইউজারের মোট ব্যালেন্স (balances টেবিল থেকে)
        bal_res = await asyncio.to_thread(supabase.table("balances").select("main_balance").execute)
        total_balance = sum(item.get('main_balance', 0) for item in bal_res.data) if bal_res.data else 0.0
        
        # ৪. সুন্দরভাবে মেসেজ সাজানো (HTML ফরম্যাট)
        status_msg = "📊 <b>বটের সামগ্রিক পরিসংখ্যান</b>\n\n"
        status_msg += f"✅ <b>মোট জমানো ডাটা:</b> <code>{total_submissions}</code> টি\n"
        status_msg += "━━━━━━━━━━━━━━━━━━━━\n"
        
        if category_counts:
            status_msg += "📂 <b>ক্যাটাগরি ভিত্তিক রিপোর্ট:</b>\n"
            for cat, count in category_counts.items():
                status_msg += f"• {cat}: <code>{count}</code> টি\n"
        else:
            status_msg += "❌ এখনো কোনো আইডি বা ফাইল জমা পড়েনি।\n"
            
        status_msg += "━━━━━━━━━━━━━━━━━━━━\n"
        status_msg += f"💰 <b>বটের মোট ব্যালেন্স:</b> <code>{total_balance:.2f}</code> টাকা\n"
        status_msg += "<i>(সব ইউজারের ওয়ালেটে থাকা মোট টাকা)</i>"

        await message.answer(status_msg, parse_mode="HTML")

    except Exception as e:
        print(f"Admin stats error: {e}")
        await message.answer("❌ পরিসংখ্যান রিপোর্ট তৈরি করতে সমস্যা হয়েছে।")
 #==============================
# ৪. নতুন অ্যাডমিন প্যানেল কমান্ডসমূহ
# ==========================================

# ১. ইউজারের পেমেন্ট মেথড চেক করার কমান্ড (Supabase payment_methods টেবিল থেকে)
@dp.message_handler(commands=['check_payment'], user_id=ADMIN_ID)
async def admin_check_payment(message: types.Message):
    args = message.get_args()
    if not args.isdigit(): 
        return await message.answer("⚠️ আইডি দিন। উদাহরণ: <code>/check_payment 123456</code>", parse_mode="HTML")
    
    try:
        # payment_methods টেবিল থেকে তথ্য আনা হচ্ছে
        res = await asyncio.to_thread(supabase.table("payment_methods").select("bkash_num, nagad_num, rocket_num, recharge_num, binance_id").eq("user_id", int(args)).execute)
        
        if res.data:
            data = res.data[0]
            text = (f"💳 <b>ইউজার পেমেন্ট ইনফো (ID: {args})</b>\n\n"
                    f"📱 রিচার্জ: <code>{data.get('recharge_num') or 'নেই'}</code>\n"
                    f"🟢 বিকাশ: <code>{data.get('bkash_num') or 'নেই'}</code>\n"
                    f"🟠 নগদ: <code>{data.get('nagad_num') or 'নেই'}</code>\n"
                    f"💜 রকেট: <code>{data.get('rocket_num') or 'নেই'}</code>\n"
                    f"🟡 বিন্যান্স: <code>{data.get('binance_id') or 'নেই'}</code>")
            await message.answer(text, parse_mode="HTML")
        else:
            await message.answer("❌ এই আইডির কোনো পেমেন্ট তথ্য পাওয়া যায়নি।")
    except Exception as e:
        await message.answer(f"❌ এরর: {str(e)}")

# ২. ইউজারের মেইন, রেফার এবং পেন্ডিং ব্যালেন্স চেক (দশমিক ছাড়া)
@dp.message_handler(commands=['check_balance'], user_id=ADMIN_ID)
async def admin_check_balance(message: types.Message):
    args = message.get_args()
    if not args.isdigit(): 
        return await message.answer("⚠️ সঠিক আইডি দিন।", parse_mode="HTML")
    
    try:
        # balances টেবিল থেকে ব্যালেন্সের তথ্য আনা হচ্ছে
        res = await asyncio.to_thread(supabase.table("balances").select("main_balance, refer_balance, pending_balance").eq("user_id", int(args)).execute)
        
        if res.data:
            data = res.data[0]
            # int() ব্যবহার করা হয়েছে যাতে দশমিক না আসে
            await message.answer(f"💰 <b>ব্যালেন্স রিপোর্ট (ID: {args})</b>\n\n"
                                 f"💵 মূল ব্যালেন্স: <code>{int(data.get('main_balance', 0))} ৳</code>\n"
                                 f"👥 রেফার ব্যালেন্স: <code>{int(data.get('refer_balance', 0))} ৳</code>\n"
                                 f"⏳ পেন্ডিং ব্যালেন্স: <code>{int(data.get('pending_balance', 0))} ৳</code>", parse_mode="HTML")
        else:
            await message.answer("❌ ইউজার পাওয়া যায়নি।")
    except Exception as e:
        await message.answer(f"❌ এরর: {str(e)}")

# ৩. ইউজারের মোট সফল রেফারেল সংখ্যা দেখার কমান্ড
@dp.message_handler(commands=['check_refer'], user_id=ADMIN_ID)
async def admin_check_referral(message: types.Message):
    args = message.get_args()
    if not args.isdigit(): 
        return await message.answer("⚠️ সঠিক আইডি দিন।", parse_mode="HTML")
    
    try:
        # balances টেবিল থেকে রেফারেল কাউন্ট আনা হচ্ছে
        res = await asyncio.to_thread(supabase.table("balances").select("referral_count").eq("user_id", int(args)).execute)
        
        if res.data:
            ref_count = res.data[0].get('referral_count', 0)
            await message.answer(f"👤 <b>ID:</b> <code>{args}</code>\n"
                                 f"👥 <b>মোট সফল রেফার:</b> <code>{ref_count}</code> জন", parse_mode="HTML")
        else:
            await message.answer("❌ ইউজার পাওয়া যায়নি।")
    except Exception as e:
        await message.answer(f"❌ এরর: {str(e)}")
        

# এটি ফাইলের শেষে যোগ করুন
@dp.callback_query_handler(lambda c: c.data == 'add_to_main')
async def process_add_to_main(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    # সুইচটি অন আছে কিনা চেক করা
    if not REFER_ADD_ENABLED:
        return await bot.answer_callback_query(callback_query.id, text="❌ এই সুবিধাটি বর্তমানে বন্ধ আছে।", show_alert=True)

    try:
        # Supabase থেকে ইউজারের বর্তমান রেফার ব্যালেন্স এবং মেইন ব্যালেন্স আনা
        res = await asyncio.to_thread(supabase.table("balances").select("refer_balance, main_balance").eq("user_id", user_id).execute)
        
        if res.data:
            ref_bal = res.data[0].get('refer_balance', 0)
            main_bal = res.data[0].get('main_balance', 0)
            
            if ref_bal > 0:
                # মেইন ব্যালেন্সে যোগ এবং রেফার ব্যালেন্স ০ করা
                new_main_bal = main_bal + ref_bal
                
                await asyncio.to_thread(supabase.table("balances").update({
                    "main_balance": new_main_bal, 
                    "refer_balance": 0
                }).eq("user_id", user_id).execute)
                
                # সফল হওয়ার নোটিফিকেশন দেখানো
                await bot.answer_callback_query(callback_query.id, text=f"✅ সফল! {int(ref_bal)} ৳ মেইন ব্যালেন্সে যোগ হয়েছে।", show_alert=True)
                
                # আগের মেসেজটি এডিট করে আপডেট দেখানো
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=callback_query.message.message_id,
                    text=f"✅ আপনার <b>{int(ref_bal)} ৳</b> সফলভাবে মেইন ব্যালেন্সে যোগ করা হয়েছে।\n\nএখন আপনার রেফার ব্যালেন্স: <b>0 ৳</b>",
                    reply_markup=None, # বাটন সরিয়ে ফেলা
                    parse_mode="HTML"
                )
            else:
                # ব্যালেন্স ০ থাকলে
                await bot.answer_callback_query(callback_query.id, text="❌ আপনার রেফার ব্যালেন্সে কোনো টাকা নেই।", show_alert=True)
        else:
            await bot.answer_callback_query(callback_query.id, text="❌ ডাটাবেসে তথ্য পাওয়া যায়নি।", show_alert=True)
            
    except Exception as e:
        print(f"Add to main error: {e}")
        await bot.answer_callback_query(callback_query.id, text="❌ কারিগরি সমস্যা হয়েছে।", show_alert=True)
            
if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
