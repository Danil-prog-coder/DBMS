# keybords.py
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Основное меню (кнопки под полем ввода)"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="💰 Задать баланс")
    builder.button(text="📈 Акции/Облигации")
    builder.button(text="📊 Мой портфель")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def balance_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления балансом (кнопки под сообщением)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Пополнить", callback_data="replenish_balance")
    builder.button(text="✏️ Изменить", callback_data="change_balance")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(2, 1)
    return builder.as_markup()


def security_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа ценных бумаг"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 Акции", callback_data="type_stock")
    builder.button(text="📄 Облигации", callback_data="type_bond")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(2, 1)
    return builder.as_markup()


def securities_list_keyboard(securities: list, security_type: str) -> InlineKeyboardMarkup:
    """Список доступных бумаг"""
    builder = InlineKeyboardBuilder()
    for sec in securities:
        # Формируем текст кнопки: Название - Цена (Изменение%)
        text = f"{sec['name']} - {sec['price']}₽ ({sec['change_percent']}%)"
        builder.button(text=text, callback_data=f"select_security_{sec['id']}")

    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def portfolio_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для портфеля"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Аналитика", callback_data="analytics")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()