"""
Простий платіжний модуль - показ USDT TRC20 гаманця
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import logging
import os

from user_manager import UserManager
from translations import get_text
from config import SUBSCRIPTION_PRICE_USD

logger = logging.getLogger(__name__)

# Створюємо роутер для платежів
payment_router = Router()

user_manager = UserManager()

# Отримуємо адресу гаманця з .env
USDT_WALLET = os.getenv("USDT_TRC20_WALLET", "")


@payment_router.callback_query(F.data == "pay_crypto")
async def show_payment_info(callback: CallbackQuery):
    """Показує інформацію для оплати USDT TRC20"""
    user_id = callback.from_user.id
    lang = user_manager.get_language(user_id)
    
    if not USDT_WALLET:
        await callback.answer(
            get_text("wallet_not_configured", lang),
            show_alert=True
        )
        return
    
    # Формуємо повідомлення з перекладами
    text = f"""{get_text("payment_title", lang)}

{get_text("payment_amount", lang, amount=SUBSCRIPTION_PRICE_USD)}
{get_text("payment_network", lang)}

{get_text("payment_address", lang)}
`{USDT_WALLET}`

{get_text("payment_how_to", lang)}

{get_text("payment_step1", lang)}
{get_text("payment_step2", lang)}
{get_text("payment_step3", lang)}
{get_text("payment_step4", lang)}
{get_text("payment_step5", lang, amount=SUBSCRIPTION_PRICE_USD)}
{get_text("payment_step6", lang)}

{get_text("payment_after", lang)}
{get_text("payment_contact_admin", lang)}

{get_text("payment_important", lang)}
{get_text("payment_warning_network", lang)}
{get_text("payment_warning_amount", lang, amount=SUBSCRIPTION_PRICE_USD)}
{get_text("payment_warning_other", lang)}"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_text("btn_copy_address", lang),
                callback_data="copy_address"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text("btn_contact_admin", lang),
                url="https://t.me/onopandrey"
            )
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
    
    logger.info(f"💰 Показано інфо про оплату для user {user_id}")


@payment_router.callback_query(F.data == "copy_address")
async def copy_address_hint(callback: CallbackQuery):
    """Підказка про копіювання адреси"""
    user_id = callback.from_user.id
    lang = user_manager.get_language(user_id)
    
    await callback.answer(
        get_text("copy_address_hint", lang, wallet=USDT_WALLET),
        show_alert=True
    )

