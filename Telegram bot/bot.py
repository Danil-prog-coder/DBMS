
# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

# Импорты ваших модулей
from database import Database
from keybords import (
    main_menu_keyboard,
    balance_menu_keyboard,
    security_type_keyboard,
    securities_list_keyboard,
    portfolio_keyboard
)
from config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Инициализация базы данных
db = Database()


# ====== МАШИНА СОСТОЯНИЙ ======
class InvestmentState(StatesGroup):
    setting_balance = State()
    topping_up = State()
    changing_balance = State()
    security_type = State()
    purchase_amount = State()
    waiting_for_security_name = State()


# ====== ОБРАБОТЧИКИ МЕНЮ (ReplyKeyboard) ======

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    db.add_user(user_id)
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для управления инвестициями.\n"
        "Выберите действие в меню:",
        reply_markup=main_menu_keyboard()
    )


@dp.message(F.text == "💰 Задать баланс")
async def set_balance_menu(message: types.Message, state: FSMContext):
    await message.answer(
        "💳 Управление балансом:\nВыберите действие:",
        reply_markup=balance_menu_keyboard()
    )
    await state.set_state(InvestmentState.setting_balance)


@dp.message(F.text == "📈 Акции/Облигации")
async def securities_menu(message: types.Message, state: FSMContext):
    await message.answer(
        "📈 Выберите тип ценных бумаг:",
        reply_markup=security_type_keyboard()
    )
    await state.set_state(InvestmentState.security_type)


@dp.message(F.text == "📊 Мой портфель")
async def portfolio_menu(message: types.Message):
    user_id = message.from_user.id
    purchases = db.get_user_purchases(user_id)

    if not purchases:
        await message.answer(
            "📭 У вас пока нет бумаг в портфеле",
            reply_markup=portfolio_keyboard()
        )
        return

    text = "📋 **Ваши бумаги:**\n\n"
    for p in purchases:
        text += f"📄 {p['name']} ({p['type']})\n"
        text += f"💰 Сумма: {p['amount']:.2f} ₽\n"
        text += f"🔢 Количество: {p['quantity']}\n"
        text += f"📅 Дата: {p['purchase_date']}\n\n"

    await message.answer(text, reply_markup=portfolio_keyboard())


# ====== ОБРАБОТЧИКИ КНОПОК (InlineKeyboard) ======

@router.callback_query(F.data == "replenish_balance")
async def replenish_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💵 Введите сумму пополнения (числом):")
    await state.set_state(InvestmentState.topping_up)
    await callback.answer()


@router.callback_query(F.data == "change_balance")
async def change_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️ Введите новый баланс (числом):")
    await state.set_state(InvestmentState.changing_balance)
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            "🔙 Главное меню:",
            reply_markup=main_menu_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "🔙 Главное меню:",
            reply_markup=main_menu_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "type_stock")
async def select_stock_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(security_type="stock")
    securities = db.get_securities("stock")

    if not securities:
        await callback.message.answer("❌ Нет доступных акций")
        await callback.answer()
        return

    keyboard = securities_list_keyboard(securities, "stock")
    await callback.message.answer("📈 Выберите акцию:", reply_markup=keyboard)
    await state.set_state(InvestmentState.purchase_amount)
    await callback.answer()


@router.callback_query(F.data == "type_bond")
async def select_bond_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(security_type="bond")
    securities = db.get_securities("bond")

    if not securities:
        await callback.message.answer("❌ Нет доступных облигаций")
        await callback.answer()
        return

    keyboard = securities_list_keyboard(securities, "bond")
    await callback.message.answer("📄 Выберите облигацию:", reply_markup=keyboard)
    await state.set_state(InvestmentState.purchase_amount)
    await callback.answer()


@router.callback_query(F.data.startswith("select_security_"))
async def select_security(callback: CallbackQuery, state: FSMContext):
    security_id = int(callback.data.split("_")[-1])
    security = db.get_security_by_id(security_id)

    if not security:
        await callback.message.answer("❌ Бумага не найдена")
        await callback.answer()
        return

    await state.update_data(
        security_id=security_id,
        security_name=security['name'],
        security_price=security['price']
    )

    await callback.message.answer(
        f"📄 {security['name']}\n"
        f"💰 Цена: {security['price']:.2f} ₽\n"
        f"📊 Изменение: {security['change_percent']}%\n\n"
        "🔢 Введите количество:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(InvestmentState.purchase_amount)
    await callback.answer()


@router.callback_query(F.data == "analytics")
async def process_analytics(callback: CallbackQuery):
    user_id = callback.from_user.id
    purchases = db.get_user_purchases(user_id)

    if not purchases:
        await callback.message.answer("❌ Нет данных для аналитики")
        await callback.answer()
        return

    total_invested = sum(p['amount'] for p in purchases)
    current_value = sum(p['quantity'] * p['price'] for p in purchases)
    total_profit = current_value - total_invested
    profit_percent = (total_profit / total_invested * 100) if total_invested > 0 else 0

    stocks = [p for p in purchases if p['type'] == 'stock']
    bonds = [p for p in purchases if p['type'] == 'bond']

    text = "📊 Аналитика портфеля:\n\n"
    text += f"💵 Вложено: {total_invested:.2f} ₽\n"
    text += f"💰 Текущая стоимость: {current_value:.2f} ₽\n"
    text += f"📈 Общая прибыль: {total_profit:.2f} ₽ ({profit_percent:.2f}%)\n\n"

    if stocks:
        stocks_value = sum(s['quantity'] * s['price'] for s in stocks)
        stocks_percent = (stocks_value / total_invested * 100) if total_invested > 0 else 0
        text += f"📈 Акции: {stocks_value:.2f} ₽ ({len(stocks)} позиций, {stocks_percent:.1f}%)\n"

    if bonds:
        bonds_value = sum(b['quantity'] * b['price'] for b in bonds)
        bonds_percent = (bonds_value / total_invested * 100) if total_invested > 0 else 0
        text += f"📊 Облигации: {bonds_value:.2f} ₽ ({len(bonds)} позиций, {bonds_percent:.1f}%)\n"

    await callback.message.answer(text)
    await callback.answer()


# ====== ОБРАБОТЧИКИ ВВОДА ЧИСЕЛ (ИСПРАВЛЕНО) ======

@dp.message(InvestmentState.topping_up)
async def process_top_up(message: types.Message, state: FSMContext):
    try:
        clean_text = message.text.strip().replace(',', '.')
        amount = float(clean_text)

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля.")
            return

        user_id = message.from_user.id
        db.update_balance(user_id, amount)
        new_balance = db.get_balance(user_id)

        await message.answer(
            f"✅ Баланс пополнен на {amount:.2f} ₽\n"
            f"💰 Новый баланс: {new_balance:.2f} ₽",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Это не число! Введите сумму цифрами (например: 1000).")


@dp.message(InvestmentState.changing_balance)
async def process_balance_change(message: types.Message, state: FSMContext):
    try:
        clean_text = message.text.strip().replace(',', '.')
        new_balance = float(clean_text)

        if new_balance < 0:
            await message.answer("❌ Баланс не может быть отрицательным.")
            return

        user_id = message.from_user.id
        db.set_balance(user_id, new_balance)

        await message.answer(
            f"✅ Баланс изменён: {new_balance:.2f} ₽",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректное число.")


@dp.message(InvestmentState.purchase_amount)
async def process_purchase_amount(message: types.Message, state: FSMContext):
    try:
        clean_text = message.text.strip().replace(',', '.')
        quantity = float(clean_text)

        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше нуля.")
            return

        await state.update_data(quantity=quantity)

        data = await state.get_data()
        security_id = data.get("security_id")
        security_name = data.get("security_name", "Бумага")
        security_price = data.get("security_price", 0)

        total_amount = quantity * security_price
        current_balance = db.get_balance(message.from_user.id)

        if current_balance < total_amount:
            await message.answer(
                f"❌ Недостаточно средств!\nНужно: {total_amount:.2f} ₽\nВаш баланс: {current_balance:.2f} ₽",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()
            return

        db.update_balance(message.from_user.id, -total_amount)
        db.add_purchase(message.from_user.id, security_id, total_amount, quantity)
        new_balance = db.get_balance(message.from_user.id)

        await message.answer(
            f"✅ Покупка совершена!\n"
            f"📄 {security_name}\n🔢 Кол-во: {quantity}\n💰 Сумма: {total_amount:.2f} ₽\n💳 Остаток: {new_balance:.2f} ₽",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите количество цифрами (например: 10).")


# ====== ЗАПАСНОЙ ОБРАБОТЧИК ======
@dp.message()
async def echo_all(message: types.Message):
    current_state = await message.state.get_state()
    if current_state:
        await message.answer(f"⚠️ Я жду число (состояние: {current_state}). Введите цифры.")
    else:
        await message.answer(
            "🤔 Используйте кнопки меню:",
            reply_markup=main_menu_keyboard()
        )


# ====== ЗАПУСК ======
async def main():
    logging.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())