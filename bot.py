import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- SOZLAMALAR ---
TOKEN = os.getenv("BOT_TOKEN", "8605987169:AAHSGvO5TfcrmvVzzcAM7PDCiKAJ3U0W7V8")

# PythonAnywhere uchun to'liq yo'l
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "finance_pro_v4.db")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

# --- BAZA ---
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

def db_init():
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, year INTEGER, month TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS custom_categories (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS custom_subcategories (id INTEGER PRIMARY KEY, user_id INTEGER, parent_cat TEXT, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, user_id INTEGER, year INTEGER, month TEXT, day INTEGER, category TEXT, subcategory TEXT, amount REAL)''')
    conn.commit()

db_init()

class Form(StatesGroup):
    choosing_year = State()
    choosing_month = State()
    main_menu = State()
    choosing_sub = State()
    choosing_day = State()
    entering_amount = State()
    add_cat = State()
    add_sub = State()
    deleting_sub = State()
    del_cat = State()
    ot_name = State()   
    ot_day = State()    
    ot_amount = State() 
    debt_day = State()
    debt_amount = State()

# --- YORDAMCHI FUNKSIYA ---
def get_previous_month(current_month):
    months = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]
    try:
        idx = months.index(current_month)
        return months[idx - 1] if idx > 0 else "Dekabr"
    except:
        return "Oldingi oy"

# --- KLAVIATURALAR ---
def get_main_kb(user_id):
    builder = ReplyKeyboardBuilder()
    cursor.execute("SELECT month FROM user_settings WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    current_month = res[0] if res else "Yanvar"
    prev_month = get_previous_month(current_month)
    builder.add(types.KeyboardButton(text=f"📉 {prev_month} oyidan qarzim"))
    std = ["🚗 Avtomobil", "🛒 Oziq-ovqat", "🌐 Aloqa", "🏠 Uy xarajatlari", "🎓 Ta'lim", "💳 Kredit/Qarz", "❤️ Oilam uchun", "🎁 Sovg'alar"]
    cursor.execute("SELECT name FROM custom_categories WHERE user_id=?", (user_id,))
    customs = [f"📂 {r[0]}" for r in cursor.fetchall()]
    for b in std + customs:
        builder.add(types.KeyboardButton(text=b))
    builder.add(types.KeyboardButton(text="➕ Kategoriya qo'shish"))
    builder.add(types.KeyboardButton(text="🗑 Kategoriya o'chirish"))
    builder.add(types.KeyboardButton(text="⚡️ Bir martalik xarajat"))
    builder.add(types.KeyboardButton(text="📊 Oylik hisobot"))
    builder.add(types.KeyboardButton(text="📈 Statistika"))
    builder.add(types.KeyboardButton(text="🗑 Oxirgi xarajatni o'chirish"))
    builder.add(types.KeyboardButton(text="📅 Oyni o'zgartirish"))
    builder.add(types.KeyboardButton(text="🗓 Yilni o'zgartirish"))
    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)

def get_days_kb():
    builder = ReplyKeyboardBuilder()
    for i in range(1, 32): builder.add(types.KeyboardButton(text=str(i)))
    builder.add(types.KeyboardButton(text="⬅️ Ortga qaytish"))
    builder.adjust(7)
    return builder.as_markup(resize_keyboard=True)

# --- START VA SOZLAMALAR ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    for y in [2025, 2026, 2027]: builder.add(types.KeyboardButton(text=f"📅 {y}"))
    await message.answer("👋 **Xush kelibsiz!**\nYilni tanlang:", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="Markdown")
    await state.set_state(Form.choosing_year)

@dp.message(Form.choosing_year)
async def set_year(message: types.Message, state: FSMContext):
    year = message.text.replace("📅 ", "")
    await state.update_data(year=year)
    builder = ReplyKeyboardBuilder()
    months = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]
    for m in months: builder.add(types.KeyboardButton(text=m))
    await message.answer("📍 **Oyni** tanlang:", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="Markdown")
    await state.set_state(Form.choosing_month)

@dp.message(Form.choosing_month)
async def set_month(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, year, month) VALUES (?, ?, ?)", (message.from_user.id, data['year'], message.text))
    conn.commit()
    await message.answer(f"✅ Saqlandi: {data['year']}-yil, {message.text}", reply_markup=get_main_kb(message.from_user.id), parse_mode="Markdown")
    await state.set_state(Form.main_menu)

# --- ASOSIY HANDLER ---
@dp.message(Form.main_menu)
async def main_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text

    if "🗓 Yilni o'zgartirish" in text: await cmd_start(message, state); return
    if "📅 Oyni o'zgartirish" in text:
        builder = ReplyKeyboardBuilder()
        months = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]
        for m in months: builder.add(types.KeyboardButton(text=m))
        await message.answer("🔄 Yangi oyni tanlang:", reply_markup=builder.as_markup(resize_keyboard=True))
        await state.set_state(Form.choosing_month); return
    if "📊 Oylik hisobot" in text: await show_report(message); return
    if "📈 Statistika" in text: await show_stats(message); return
    if "🗑 Oxirgi xarajat" in text: await delete_last(message); return
    if "➕ Kategoriya" in text: await message.answer("🆕 Yangi kategoriya nomi:"); await state.set_state(Form.add_cat); return
    if "🗑 Kategoriya o'chirish" in text:
        cursor.execute("SELECT name FROM custom_categories WHERE user_id=?", (user_id,))
        cats = cursor.fetchall()
        if not cats:
            await message.answer("❌ O'chirish uchun qo'shilgan kategoriya yo'q.", reply_markup=get_main_kb(user_id))
            return
        builder = ReplyKeyboardBuilder()
        for r in cats: builder.add(types.KeyboardButton(text=r[0]))
        builder.add(types.KeyboardButton(text="⬅️ Ortga qaytish"))
        builder.adjust(2)
        await message.answer("🗑 O'chirish uchun kategoriyani tanlang:", reply_markup=builder.as_markup(resize_keyboard=True))
        await state.set_state(Form.del_cat)
        return
    if "oyidan qarzim" in text:
        clean_name = text.replace("📉 ", "")
        await state.update_data(debt_name=clean_name)
        await message.answer(f"📅 **{clean_name}** uchun sanani tanlang:", reply_markup=get_days_kb(), parse_mode="Markdown")
        await state.set_state(Form.debt_day)
        return
    if "⚡️ Bir martalik" in text:
        await message.answer("📝 **Xarajat nomini kiriting:**\n(Masalan: Kafe yoki Bozorlik)", parse_mode="Markdown")
        await state.set_state(Form.ot_name)
        return

    clean_cat = text.replace("🚗 ", "").replace("🛒 ", "").replace("🌐 ", "").replace("🏠 ", "").replace("🎓 ", "").replace("💳 ", "").replace("❤️ ", "").replace("🎁 ", "").replace("📂 ", "")
    await state.update_data(current_cat=clean_cat)
    await show_subs(message, state, clean_cat)

# --- QARZ XARAJAT BOSQICHLARI ---
@dp.message(Form.debt_day)
async def debt_day_handler(message: types.Message, state: FSMContext):
    if "⬅️ Ortga" in message.text:
        await message.answer("🏠 Asosiy menyu", reply_markup=get_main_kb(message.from_user.id))
        await state.set_state(Form.main_menu); return
    await state.update_data(day=message.text)
    await message.answer(f"💰 Summani kiriting:", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    await state.set_state(Form.debt_amount)

@dp.message(Form.debt_amount)
async def debt_amount_handler(message: types.Message, state: FSMContext):
    try:
        val = float(message.text.replace(" ", ""))
        data = await state.get_data()
        cursor.execute("SELECT year, month FROM user_settings WHERE user_id=?", (message.from_user.id,))
        s = cursor.fetchone()
        cursor.execute("INSERT INTO expenses (user_id, year, month, day, category, subcategory, amount) VALUES (?,?,?,?,?,?,?)", 
                       (message.from_user.id, s[0], s[1], int(data['day']), "💰 Qarz", data['debt_name'], val))
        conn.commit()
        await message.answer(f"✅ Saqlandi!\n🔹 {data['debt_name']}\n💵 {val:,.0f} so'm", parse_mode="Markdown")
    except: await message.answer("⚠️ Faqat raqam kiriting.")
    await message.answer("🏠 Asosiy menyu", reply_markup=get_main_kb(message.from_user.id))
    await state.set_state(Form.main_menu)

# --- BIR MARTALIK XARAJAT BOSQICHLARI ---
@dp.message(Form.ot_name)
async def ot_name_handler(message: types.Message, state: FSMContext):
    await state.update_data(ot_name=message.text)
    cursor.execute("SELECT month FROM user_settings WHERE user_id=?", (message.from_user.id,))
    month = cursor.fetchone()[0]
    await message.answer(f"📅 **{month}** oyi uchun sanani tanlang:", reply_markup=get_days_kb(), parse_mode="Markdown")
    await state.set_state(Form.ot_day)

@dp.message(Form.ot_day)
async def ot_day_handler(message: types.Message, state: FSMContext):
    if "⬅️ Ortga" in message.text:
        await message.answer("🏠 Asosiy menyu", reply_markup=get_main_kb(message.from_user.id))
        await state.set_state(Form.main_menu); return
    await state.update_data(ot_day=message.text)
    await message.answer(f"💰 **{message.text}-sana uchun summani kiriting:**", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    await state.set_state(Form.ot_amount)

@dp.message(Form.ot_amount)
async def ot_amount_handler(message: types.Message, state: FSMContext):
    try:
        val = float(message.text.replace(" ", ""))
        data = await state.get_data()
        cursor.execute("SELECT year, month FROM user_settings WHERE user_id=?", (message.from_user.id,))
        s = cursor.fetchone()
        cursor.execute("INSERT INTO expenses (user_id, year, month, day, category, subcategory, amount) VALUES (?,?,?,?,?,?,?)", 
                       (message.from_user.id, s[0], s[1], int(data['ot_day']), "⚡️ Bir martalik", data['ot_name'], val))
        conn.commit()
        await message.answer(f"✅ **Saqlandi!**\n🔹 {data['ot_name']}\n💵 {val:,.0f} so'm", parse_mode="Markdown")
    except: await message.answer("⚠️ Xato! Faqat raqam kiriting.")
    await message.answer("🏠 Asosiy menyu", reply_markup=get_main_kb(message.from_user.id))
    await state.set_state(Form.main_menu)

# --- SUBKATEGORIYALAR ---
async def show_subs(message, state, cat_name):
    subs_dict = {"Avtomobil": ["⛽️ Yoqilg'i", "🔧 Remont", "👮 Jarima"], "Oziq-ovqat": ["🥩 Go'sht", "🍎 Meva", "🥟 Somsa"], "Aloqa": ["📱 Telefon", "🌐 Internet", "📶 Simkarta"], "Uy xarajatlari": ["🔥 Gaz", "💡 Svet", "💧 Suv", "🏘 Ijara"], "Ta'lim": ["📄 Kontrakt", "📚 Kurs"], "Oilam uchun": ["🚌 Yo'l kira", "🎓 Kurs"]}
    builder = ReplyKeyboardBuilder()
    for s in subs_dict.get(cat_name, []): builder.add(types.KeyboardButton(text=s))
    cursor.execute("SELECT name FROM custom_subcategories WHERE user_id=? AND parent_cat=?", (message.from_user.id, cat_name))
    custom_subs = [r[0] for r in cursor.fetchall()]
    for cs in custom_subs: builder.add(types.KeyboardButton(text=f"🔹 {cs}"))
    builder.add(types.KeyboardButton(text="➕ Subkategoriya qo'shish"), types.KeyboardButton(text="⬅️ Ortga qaytish"))
    if custom_subs: builder.add(types.KeyboardButton(text="❌ Sub-o'chirish"))
    builder.adjust(2); await message.answer(f"🛠 **{cat_name}**:", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="Markdown")
    await state.set_state(Form.choosing_sub)

@dp.message(Form.choosing_sub)
async def handle_sub(message: types.Message, state: FSMContext):
    if "⬅️ Ortga" in message.text:
        await message.answer("🏠 Asosiy menyu", reply_markup=get_main_kb(message.from_user.id))
        await state.set_state(Form.main_menu); return
    if "➕ Subkategoriya" in message.text:
        await message.answer("✍️ Yangi subkategoriya nomi:"); await state.set_state(Form.add_sub); return
    if "❌ Sub-o'chirish" in message.text:
        data = await state.get_data(); builder = ReplyKeyboardBuilder()
        cursor.execute("SELECT name FROM custom_subcategories WHERE user_id=? AND parent_cat=?", (message.from_user.id, data['current_cat']))
        for r in cursor.fetchall(): builder.add(types.KeyboardButton(text=r[0]))
        builder.add(types.KeyboardButton(text="⬅️ Ortga qaytish")); builder.adjust(2)
        await message.answer("🗑 O'chirishni tanlang:", reply_markup=builder.as_markup(resize_keyboard=True)); await state.set_state(Form.deleting_sub); return

    await state.update_data(current_sub=message.text)
    cursor.execute("SELECT month FROM user_settings WHERE user_id=?", (message.from_user.id,))
    month = cursor.fetchone()[0]
    await message.answer(f"📅 **{month}**.\nSanani tanlang:", reply_markup=get_days_kb(), parse_mode="Markdown")
    await state.set_state(Form.choosing_day)

@dp.message(Form.choosing_day)
async def handle_day(message: types.Message, state: FSMContext):
    if "⬅️ Ortga" in message.text:
        data = await state.get_data(); await show_subs(message, state, data['current_cat']); return
    await state.update_data(day=message.text)
    await message.answer(f"💰 **{message.text}-sana uchun summa:**", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    await state.set_state(Form.entering_amount)

@dp.message(Form.entering_amount)
async def handle_amount(message: types.Message, state: FSMContext):
    try:
        val = float(message.text.replace(" ", ""))
        data = await state.get_data()
        cursor.execute("SELECT year, month FROM user_settings WHERE user_id=?", (message.from_user.id,))
        s = cursor.fetchone()
        cursor.execute("INSERT INTO expenses (user_id, year, month, day, category, subcategory, amount) VALUES (?,?,?,?,?,?,?)", (message.from_user.id, s[0], s[1], int(data['day']), data['current_cat'], data['current_sub'], val))
        conn.commit()
        await message.answer(f"✅ Saqlandi: {data['day']}-{s[1]}\n💵 {val:,.0f} so'm")
    except: await message.answer("⚠️ Faqat raqam yozing.")
    await message.answer("🏠 Asosiy menyu", reply_markup=get_main_kb(message.from_user.id))
    await state.set_state(Form.main_menu)

# --- HISOBOTLAR ---
async def show_report(message):
    cursor.execute("SELECT year, month FROM user_settings WHERE user_id=?", (message.from_user.id,))
    s = cursor.fetchone()
    cursor.execute("SELECT day, category, subcategory, amount FROM expenses WHERE user_id=? AND year=? AND month=? ORDER BY category='💰 Qarz' DESC, day ASC", (message.from_user.id, s[0], s[1]))
    rows = cursor.fetchall()
    if not rows: await message.answer("📭 Ma'lumot yo'q."); return
    total = sum(r[3] for r in rows)
    res = f"📊 **{s[1]} ({s[0]}):**\n"
    for r in rows:
        if r[1] == "💰 Qarz":
            res += f"\n🔹 {r[2]} {r[3]:,.0f}\n"
        else:
            res += f"🔹 {r[0]}-sana {r[1]}({r[2]}) - {r[3]:,.0f}\n"
    res += f"\n💰 **Jami: {total:,.0f}**"
    await message.answer(res, parse_mode="Markdown")

async def show_stats(message):
    cursor.execute("SELECT year, month FROM user_settings WHERE user_id=?", (message.from_user.id,))
    s = cursor.fetchone()
    cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=? AND year=? AND month=? AND category!='💰 Qarz' GROUP BY category", (message.from_user.id, s[0], s[1]))
    rows = cursor.fetchall()
    if not rows: await message.answer("📉 Statistika uchun ma'lumot yo'q (qarzlardan tashqari)."); return
    total = sum(r[1] for r in rows)
    res = f"📈 **{s[1]} statistikasi:**\n"
    for r in rows:
        percent = (r[1]/total)*100
        res += f"{r[0]}: {percent:.1f}% ( {r[1]:,.0f} )\n"
    await message.answer(res, parse_mode="Markdown")

@dp.message(Form.add_cat)
async def add_cat_finish(message: types.Message, state: FSMContext):
    cursor.execute("INSERT INTO custom_categories (user_id, name) VALUES (?, ?)", (message.from_user.id, message.text))
    conn.commit(); await message.answer("✅ Kategoriya qo'shildi!", reply_markup=get_main_kb(message.from_user.id))
    await state.set_state(Form.main_menu)

@dp.message(Form.del_cat)
async def del_cat_finish(message: types.Message, state: FSMContext):
    if "⬅️ Ortga" in message.text:
        await message.answer("🏠 Asosiy menyu", reply_markup=get_main_kb(message.from_user.id))
        await state.set_state(Form.main_menu)
        return
    cursor.execute("DELETE FROM custom_categories WHERE user_id=? AND name=?", (message.from_user.id, message.text))
    cursor.execute("DELETE FROM custom_subcategories WHERE user_id=? AND parent_cat=?", (message.from_user.id, message.text))
    conn.commit()
    await message.answer(f"🗑 '{message.text}' kategoriyasi o'chirildi!", reply_markup=get_main_kb(message.from_user.id))
    await state.set_state(Form.main_menu)

@dp.message(Form.add_sub)
async def add_sub_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO custom_subcategories (user_id, parent_cat, name) VALUES (?, ?, ?)", (message.from_user.id, data['current_cat'], message.text))
    conn.commit(); await message.answer("✅ Subkategoriya qo'shildi."); await show_subs(message, state, data['current_cat'])

@dp.message(Form.deleting_sub)
async def del_sub_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("DELETE FROM custom_subcategories WHERE user_id=? AND parent_cat=? AND name=?", (message.from_user.id, data['current_cat'], message.text))
    conn.commit(); await message.answer("🗑 O'chirildi."); await show_subs(message, state, data['current_cat'])

async def delete_last(message):
    cursor.execute("DELETE FROM expenses WHERE id = (SELECT MAX(id) FROM expenses WHERE user_id=?)", (message.from_user.id,))
    conn.commit(); await message.answer("🗑 O'chirildi.")

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
