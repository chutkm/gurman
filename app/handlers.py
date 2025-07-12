import locale
from lib2to3.fixes.fix_input import context
from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, InputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import timedelta
import re
from sqlalchemy import types, select, Update
from datetime import datetime
import asyncio
import io
import logging
from aiogram import types
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from aiogram.types import BufferedInputFile

from app.utils.llm_interface import ask_llm_ollama

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_TIME, 'russian')
import app.keyboards as kb
import app.database.requests_bot as rq_b
from app.database.models import async_session, Clients, Menu, Reservations, Tables, Restaurants, Preorder, EventTypes, \
    EventApplications
import app.utils.request_web as pars
router = Router()

# Состояния для FSM
class Register_number(StatesGroup):
    phone = State()  # Состояние для ввода телефона

# Состояния для обработки бронирования
class Register(StatesGroup):
    reservation_id = State()
    rest_id = State()
    rest_address = State()
    date = State()
    time = State()
    hours = State()
    number_of_guests = State()
    table_choice = State()

    preorder = State()
    name = State()
    confirm = State()


class CancelReservation(StatesGroup):
    name = State()
    date = State()
    time = State()
    number_of_guests = State()
    confirm_cancel = State()


class Edit(StatesGroup):
    date = State()
    time = State()
    number_of_guests = State()
    name = State()
    number = State()
    confirm = State()


class ReviewForm(StatesGroup):
    text = State()
    rating = State()


class EventApplicationStates(StatesGroup):
    event_type = State()               # Выбор типа мероприятия (свадьба, банкет и т.д.)
    restaurant_choice = State()        # Выбор ресторана или подтверждение "нет предпочтений"
    requested_date = State()           # Желаемая дата проведения
    guest_count = State()              # Количество гостей
    message_to_manager = State()       # Дополнительное сообщение менеджеру
    confirm_application = State()      # Подтверждение отправки заявки

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Обрабатывает команду /start. Заполняет данные пользователя и запрашивает телефон при необходимости.
    """
    try:
        # Добавляем пользователя в базу без номера телефона
        await rq_b.set_user(
            tg_id=message.from_user.id,
            tg_user_name=message.from_user.username
        )

        # Отправляем приветственное фото
        photo_path = 'D:/PycharmProjects/gurman/рестик_привет_cut.jpg'
        photo = FSInputFile(photo_path)
        await message.answer_photo(photo)

        # Приветственное сообщение
        await message.answer(
            "Приветствуем вас в сервисе Gourman, который поможет найти идеальное место, где можно вкусно покушать! 🤩"
        )

        # Проверяем, указан ли номер телефона
        phone_missing = await rq_b.check_number(message.from_user.id)
        if phone_missing:
            await message.answer(
                "Для дальнейшей работы с нами отправьте свой номер телефона или введите его вручную:",
                reply_markup=kb.get_number()
            )
            await state.set_state(Register_number.phone)
        else:
            await message.answer("Мы уже тебя ждем!", reply_markup=kb.main)

    except Exception as e:
        print(f"Ошибка в обработке команды /start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()


@router.message(Register_number.phone)
async def register_number(message: Message, state: FSMContext):
    """
    Обрабатывает ввод номера телефона и завершает регистрацию.
    """
    try:
        # Получаем номер телефона из контакта или текста
        phone = message.contact.phone_number if message.contact else message.text.strip()

        # Проверка формата номера
        if not re.match(r"^\+7\d{10}$", phone):
            await message.answer(
                "Пожалуйста, введите номер в формате +7XXXXXXXXXX."
            )
            return

        # Обновляем номер телефона в базе данных
        async with async_session() as session:
            from sqlalchemy import update
            await session.execute(
                update(Clients)
                .where(Clients.tg_id == message.from_user.id)
                .values(phone_number=phone)
            )
            await session.commit()

        # Сообщение об успешной регистрации
        await message.answer(
            "Регистрация успешно завершена! 🤩",
            reply_markup=kb.main
        )
        await state.clear()

    except Exception as e:
        print(f"Ошибка при регистрации номера телефона: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()




@router.callback_query(F.data.startswith("cancel_history:"))
async def cancel_booking(callback: CallbackQuery):
    """
    Обрабатывает отмену бронирования.
    """
    booking_id = int(callback.data.split(":")[1])
    try:
        async with async_session() as session:
            from sqlalchemy import update
            # Обновляем статус бронирования на "отменено"
            await session.execute(
                update(Reservations)
                .where(Reservations.reservation_id == booking_id)
                .values(reservation_status='отменено')
            )
            await session.commit()
        await callback.message.edit_text("Бронирование успешно отменено.")
        await callback.answer("Бронирование отменено.")
    except Exception as e:
        print(f"Ошибка при отмене бронирования: {e}")
        await callback.answer("Произошла ошибка при отмене.")



@router.callback_query(lambda c: c.data == 'back')
async def process_back_button(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    await callback_query.message.answer(
        'Вы вернулись в главное меню.',
        reply_markup=kb.main
    )

@router.callback_query(lambda c: c.data == 'back_category_find')
async def process_back_button(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    await callback_query.message.answer(
        'Вы вернулись в главное меню.',
        reply_markup=kb.back_to_categories_keyboard()
    )


@router.message(F.text == 'Мои бронирования')
async def my_bookings(message: Message):
    """
    Обрабатывает кнопку "Мои бронирования".
    """
    try:
        user_id = message.from_user.id
        async with async_session() as session:
            # Запрос для получения всех бронирований пользователя
            query = (
                select(
                    Reservations,  # Данные из таблицы бронирований
                    Tables.table_number,  # Номер столика
                    Restaurants.address,  # Адрес ресторана
                    Restaurants.restaurant_name
                )
                .join(Clients, Reservations.client_id == Clients.client_id)
                .join(Tables, Reservations.table_id == Tables.table_id)
                .join(Restaurants, Tables.restaurant_id == Restaurants.restaurant_id)
                .where(
                    Clients.tg_id == user_id,
                    Reservations.reservation_date_time >= datetime.now() ,Reservations.reservation_status == 'подтверждено'
                )
            )
            result = await session.execute(query)
            bookings = result.all()

            if not bookings:
                await message.answer("У вас нет активных бронирований.")
                return

            # Сортировка актуальных бронирований по дате
            bookings.sort(key=lambda x: x[0].reservation_date_time)

            # Генерация сообщений для актуальных бронирований
            await message.answer("📌 Актуальные бронирования:")
            for booking, table_number, address,restaurant_name in bookings:
                text = (
                    f"📍 Ресторан : {restaurant_name}\n\n"
                    # f"  по адресу: {address}\n\n"
                    f"📅 Дата и время: {booking.reservation_date_time.strftime('%d-%m-%Y %H:%M')}\n"
                    f"⏳ Часы бронирования: {booking.reservation_hours}\n"
                    f"👥 Количество гостей: {booking.guest_count}\n"
                    f"💺 Столик: {table_number}\n"
                    f"📌 Состояние бронирования: {booking.reservation_status}\n"
                )
                await message.answer(
                    text,
                    reply_markup=kb.booking_keyboard(booking.reservation_id, True)
                )
    except Exception as e:
        logging.exception("Ошибка при обработке бронирований.")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.callback_query(F.data.startswith("preorder_history:"))
async def view_preorder(callback: CallbackQuery):
    """
    Обрабатывает запрос на просмотр предзаказов.
    """
    try:
        # Проверяем формат данных и извлекаем ID бронирования
        data_parts = callback.data.split(":")
        if len(data_parts) < 2 or not data_parts[1].isdigit():
            await callback.answer("Неверный формат данных. Попробуйте еще раз.")
            return

        booking_id = int(data_parts[1])

        async with async_session() as session:
            # Запрос для получения информации о предзаказах по ID бронирования
            query = (
                select(
                    Menu.name_dish,  # Название блюда
                    Preorder.quantity  # Количество
                )
                .join(Menu, Preorder.menu_id == Menu.menu_id)  # Джоин с меню
                .where(Preorder.reservation_id == booking_id)  # Условие по ID бронирования
            )
            result = await session.execute(query)
            preorders = result.all()

            if not preorders:
                await callback.message.edit_text("Нет предзаказов для этого бронирования.")
                return

            # Формирование текста для вывода
            text = "📋 Ваши предзаказы:\n\n"
            for name_dish, quantity in preorders:
                text += f"🍽 {name_dish}: {quantity} шт.\n"

            # await callback.message.edit_text(text)
            # await callback.answer("Предзаказы отображены.")
            # Отправляем предзаказ отдельным сообщением
            await callback.message.answer(text)
            await callback.answer()
    except Exception as e:
        print(f"Ошибка при просмотре предзаказов: {e}")
        await callback.answer("Произошла ошибка при просмотре предзаказов.")


# handlers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext


# Импортируем отдельную функцию для работы с БД


@router.callback_query(F.data.startswith("review_history:"))
async def start_review(callback: CallbackQuery, state: FSMContext):
    _, reservation_id = callback.data.split(":")
    await state.update_data(reservation_id=reservation_id)
    await callback.message.answer("Пожалуйста, напишите ваш отзыв:")
    await state.set_state(ReviewForm.text)


@router.message(ReviewForm.text)
async def ask_rating(message: Message, state: FSMContext):
    await state.update_data(review_text=message.text)
    await message.answer("Теперь поставьте оценку от 1 до 5:")
    await state.set_state(ReviewForm.rating)

@router.message(ReviewForm.rating)
async def handle_save_review(message: Message, state: FSMContext):
    data = await state.get_data()

    try:
        rating = int(message.text)
        if not 1 <= rating <= 5:
            await message.answer("Пожалуйста, введите число от 1 до 5.")
            return
    except ValueError:
        await message.answer("Неверный формат. Введите число от 1 до 5.")
        return

    review_text = data['review_text']
    reservation_id = data['reservation_id']

    async with async_session() as session:
        result = await session.execute(
            select(Clients.client_id).where(Clients.tg_id == message.from_user.id)
        )
        client_id_db = result.scalar()

    if not client_id_db:
        await message.answer("Вы не зарегистрированы. Введите /start.")
        return

    success = await rq_b.save_review_to_db(
        client_id=client_id_db,
        review_text=review_text,
        rating=rating,
        reservation_id=reservation_id
    )

    if success:
        await message.answer("Спасибо за ваш отзыв!")
    else:
        await message.answer("Ошибка при сохранении отзыва. Попробуйте позже.")

    await state.clear()

from app.utils.request_web import fetch_restoclub_promotions



@router.message(F.text == "Акции и новинки")
async def sales(message: Message):
    keyboard = kb.salas_new_kb()
    await message.answer("Выберите интересующий пункт:", reply_markup=keyboard)

@router.callback_query(F.data == 'new_dishes')
async def new_dishes_info(callback: CallbackQuery):
    text = """
🍽️ Новинки в меню:

1. 🥐 Вафли с моцареллой и салатом  
   — Автор: Андрей Жданов (шеф Modus, Москва)

2. 🐟 Мимоза с форелью и тобико 
   — Автор: Алексей Гаврилин («Клёво Сочи Морской Порт»)

3. 🍗 Цыплёнок с гречкой  
   — Автор: Руслан Петров (Mishka, Москва)

4. 🐟 Заливное из рыбы  
   — Автор: Влад Пискунов («Матрёшка», Maison Dellos)

5. 🐺 Вагури – баранина по-бухарски  
   — Автор: Руслан Италмазов (LALI, Family Garden, Красная Поляна)
"""
    await callback.message.edit_text(text)



def format_news_message(news_list: list) -> str:
    if not news_list:
        return "❌ Новости не найдены."

    message = "🗞️ <b>Последние новости ресторанной индустрии:</b>\n\n"
    for item in news_list:
        title = item["title"]
        description = item["description"]
        link = item["link"].replace(" ", "")  # удаляем пробелы на случай ошибки
        message += f"📌 <b>{title}</b>\n{description}\n<a href='{link}'>🔗 Подробнее</a>\n\n"

    return message.strip()


@router.callback_query(F.data == 'news')
async def show_news(callback: CallbackQuery):
    url = "https://restoranoff.ru/news/newsfeed/"
    news_list = await pars.parse_restoranoff_news_async(url)
    message_text = format_news_message(news_list)

    await callback.message.answer(message_text, parse_mode="HTML")


@router.callback_query(F.data == 'promotions')
async def show_restoclub_promotions(callback: CallbackQuery):
    try:
        phot = FSInputFile('D:\\PycharmProjects\\gurman\\sale.jpg')
        await callback.message.answer_photo(phot)
        promotions = await fetch_restoclub_promotions()

        if not promotions:
            await callback.message.answer("Сейчас нет доступных акций.")
            return

        response = "🎁 Актуальные акции ресторанов Москвы:\n\n"
        for promo in promotions:
            response += (
                f"📍 {promo['restaurant']}\n"
                f"📰 {promo['title']}\n"
                f"💬 {promo['description']}\n\n"
            )

        await callback.message.answer(response)
    except Exception as e:
        await callback.message.answer("Ошибка при получении акций. Попробуйте позже.")
        print(f"Ошибка: {e}")


CATEGORIES = {
    "category_0": {
        "name": "Куда пойти с детьми",
        "url": "https://www.restoclub.ru/msk/search/restorany-moskvy-s-detskoj-komnatoj"
    },
    "category_1": {
        "name": "Новые рестораны",
        "url": "https://www.restoclub.ru/msk/search/novye-restorany-kafe-i-bary-v-moskve"
    },
    "category_2": {
        "name": "Рестораны в центре Москвы",
        "url": "https://www.restoclub.ru/msk/ratings/reiting-380-restoranov"
    },
    "category_3": {
        "name": "Рестораны и кафе с верандой",
        "url": "https://www.restoclub.ru/msk/search/restorany-moskvy-s-letnej-terrasoj"  # повторяется, возможно ошибка, проверь
    },
    "category_4": {
        "name": "Рестораны с ланчами",
        "url": "https://www.restoclub.ru/msk/search/restorany-moskvy-s-letnej-terrasoj"
    },
    "category_5": {
        "name": "Кофейни Москвы",
        "url": "https://www.restoclub.ru/msk/search/kofejnja-moskvy"
    },
}

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Вы нажали на кнопку помощи. Выберите интересующий вас раздел из меню.")

#------------------------------------Часто ищут 🔎 КАТЕГОРИИ

@router.message(F.text == "Часто ищут 🔎")
async def show_categories(message: Message):
    keyboard = kb.get_categories_keyboard()
    await message.answer("Выберите категорию:", reply_markup=keyboard)

@router.callback_query(F.data == "show_categories")
async def handle_back_to_categories(callback: CallbackQuery):
    keyboard = kb.get_categories_keyboard()
    await callback.message.answer("Выберите категорию:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("category_"))
async def process_category_callback(callback: CallbackQuery):
    key = callback.data
    category = CATEGORIES.get(key)

    if not category:
        await callback.message.answer("❌ Категория не найдена.")
        return

    await callback.message.edit_text(f"🔄 Загружаю: {category['name']}...")

    results = await pars.parse_category_page_async(category["url"])

    if not results:
        await callback.message.answer("Ничего не найдено в категориях кухни.")
        return

    text = f"📍 <b>{category['name']}</b>:\n\n"

    for r in results[:5]:
        # Ссылка делаем кликабельной в markdown/html:
        link_text = r['link'] if r['link'] == "Ссылка недоступна" else f'<a href="{r["link"]}">Ссылка</a>'

        text += (
            f"🍽 <b>{r['name']}</b>\n"
            f"📰 {r['title']}\n"
            f"💬 {r['description']}\n"
            f"🔗 {link_text}\n\n"
        )

    await callback.message.answer(text, parse_mode="HTML",reply_markup=kb.back_to_categories_keyboard())

#-------------------Популярные блюда и кухни
# Добавим словарь популярных кухонь
POPULAR_KITCHENS = {
    "kitchen_грузинские_рестораны": {"name": "Грузинские рестораны", "url": "https://www.restoclub.ru/msk/search/restorany-gruzinskoj-kuhni-v-moskve"},
    "kitchen_итальянские_рестораны": {"name": "Итальянские рестораны", "url": "https://www.restoclub.ru/msk/search/restorany-italjanskoj-kuhni-v-moskve"},
    "kitchen_японские_рестораны": {"name": "Японские рестораны", "url": "https://www.restoclub.ru/msk/search/japonskie-restorany-v-moskve"},
    "kitchen_стейки": {"name": "Стейки", "url": "https://www.restoclub.ru/msk/search/stejk-haus-moskvy"},
    "kitchen_рыба_и_морепродукты": {"name": "Рыба и морепродукты", "url": "https://www.restoclub.ru/msk/search/rybnie-restorany-v-moskve"},
    "kitchen_лучшие_бургеры": {"name": "Лучшие бургеры", "url": "https://www.restoclub.ru/msk/search/luchshie-burgery-v-moskve"}
}

# Обработчик сообщения для кнопки "Популярные кухни"
@router.message(F.text == "Популярные кухни и блюда 🍜")
async def show_popular_kitchens(message: Message):
    keyboard = kb.get_popular_kitchen_keyboard()
    await message.answer("Выберите категорию:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("kitchen_"))
async def process_kitchen_callback(callback: CallbackQuery):
    key = callback.data
    category_kitchen = POPULAR_KITCHENS.get(key)

    if not category_kitchen:
        await callback.message.answer("❌ Категория кухни не найдена.")
        return

    await callback.message.edit_text(f"🔄 Загружаю: {category_kitchen['name']}...")

    results = await pars.parse_popular_kitchen_page_async(category_kitchen["url"])

    if not results:
        await callback.message.answer("Ничего не найдено.")
        return

    text = f"📍 <b>{category_kitchen['name']}</b>:\n\n"

    for r in results[:5]:
        link_text = f'<a href="{r["link"]}">Ссылка</a>'
        cuisines = ", ".join(r["cuisines"])
        text += (
            f"🍽 <b>{r['name']}</b>\n"
            f"📍 {r['location']}\n"
            f"💰 {r['price']}\n"
            f"🍴 {r['description']}\n"
            f"🔗 {link_text}\n\n"
        )

    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb.back_to_popular_kitchens_keyboard())

@router.callback_query(F.data == "back_to_popular_kitchens")
async def handle_back_to_popular_kitchens(callback: CallbackQuery):
    keyboard = kb.get_popular_kitchen_keyboard()
    await callback.message.answer("Выберите категорию:", reply_markup=keyboard)
    await callback.answer()
#-------------
@router.message(F.text == "Контакты")
async def process_contacts(message: Message):
    contact_info = (
        "📞 Телефон: +1234567890\n"
        "✉️ Email: example@example.com\n"
        "🌐 Вебсайт: www.example.com\n"
        "🏠 Адрес: ул. Примерная, дом 1"
    )
    await message.answer(contact_info)


async def generate_pdf(promotions):
    """Асинхронная генерация PDF в памяти."""
    return await asyncio.to_thread(_generate_pdf_sync, promotions)


def _generate_pdf_sync(promotions):
    """Синхронная генерация PDF в памяти с акциями и скидками."""

    # Создание буфера для хранения PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    elements = []

    # Регистрация шрифта с поддержкой кириллицы
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

    # Определение стилей
    title_style = ParagraphStyle(
        name='Title',
        fontName='DejaVuSans',
        fontSize=20,
        alignment=1,
        spaceAfter=16,
        textColor='#2C3E50',
        fontWeight='bold'
    )

    header_style = ParagraphStyle(
        name='Header',
        fontName='DejaVuSans',
        fontSize=14,
        alignment=1,
        spaceAfter=12,
        textColor='#2980B9',
        fontStyle='italic'
    )

    normal_style = ParagraphStyle(
        name='Normal',
        fontName='DejaVuSans',
        fontSize=12,
        alignment=0,
        spaceAfter=8,
        textColor='#34495E'
    )

    # Форматирование текущей даты
    from datetime import datetime
    current_date = datetime.now().strftime("%d. %m. %Y")

    # Заголовок документа
    elements.append(Paragraph(" Скидки и Акции", title_style))
    elements.append(Spacer(1, 0.05 * letter[1]))

    # Введение
    elements.append(Paragraph(
        f"В нашем ресторане на {current_date} действуют скидки и специальные предложения. "
        "Не упустите возможность воспользоваться ими!", header_style))
    elements.append(Spacer(1, 0.15 * letter[1]))

    # Добавление информации об акциях
    for promo in promotions:
        promo_text = (
            f"<b>Акция:</b> {promo.description}<br/>"
            f"<b>Скидка:</b> {promo.discount_percentage}%<br/>"
            f"<b>Период действия:</b> с {promo.start_date.strftime('%d. %m. %Y')} по {promo.end_date.strftime('%d. %m. %Y')}<br/>"
        )
        elements.append(Paragraph(promo_text, normal_style))
        elements.append(Spacer(1, 0.05 * letter[1]))  # Уменьшено расстояние между акциями

    # Завершение и создание PDF
    doc.build(elements)
    pdf_buffer.seek(0)  # Возвращаем курсор в начало
    return pdf_buffer



@router.message(lambda message: message.text == "Акции")
async def process_contacts(message: types.Message):
    try:
        # Логирование начала работы
        logger.info(f"Получен запрос на акции от пользователя: {message.from_user.id}")

        # Получаем список активных акций
        promotions = await rq_b.find_promotion()

        if promotions:
            # Логирование перед генерацией PDF
            logger.info(f"Генерация PDF для {len(promotions)} акций...")

            # Генерация PDF в памяти
            pdf_buffer = await generate_pdf(promotions)

            # Логирование после генерации PDF
            logger.info("PDF файл с акциями сгенерирован в памяти.")

            # Отправка PDF-файла напрямую из памяти
            await message.answer("🎉 Вот ваш файл с актуальными акциями!")
            await message.answer_document(
                BufferedInputFile(pdf_buffer.read(), filename="promotions.pdf"),
                caption="Акции и скидки!"
            )

            # Логирование успешной отправки
            logger.info(f"PDF файл отправлен пользователю {message.from_user.id}.")

        else:
            # Логирование случая, если акций нет
            logger.warning(f"Пользователь {message.from_user.id} запросил акции, но их нет.")
            await message.answer("❌ *На данный момент нет действующих акций.*")

    except Exception as e:
        # Логирование ошибки
        logger.error(f"Ошибка при обработке запроса на акции от пользователя {message.from_user.id}: {e}")
        await message.answer("🚨 Произошла ошибка при обработке вашего запроса.")


@router.message(F.text == "О нас")
async def process_about(message: Message):
    about_info = (
        "Мы — ресторан Mari с многолетней историей, где традиции встречаются с современными вкусами. "
        "Всегда рады приветствовать вас и ваших близких в уютной атмосфере наших заведений!\n\n"
        "Мы являемся сетью из 4 ресторанов, каждый из которых готов предложить вам высококлассное обслуживание и изысканные блюда:\n\n"
        "1. Mari — ул. Лобненская, 4А, ☎ 8 (495) 526-33-03\n"
        "2. Mari — ул. Костромская, 17, ☎ 8 (495) 616-33-03\n"
        "3. Mari — ул. Дежнева, 13, ☎ 8 (496) 616-66-03\n"
        "4. Mari — пр-т Мира, 97, ☎ 8 (495) 616-66-03\n\n"
        "📧 Для связи и бронирования вы можете написать нам на почту: info@mari-rest.ru\n\n"
        "Мы всегда стараемся сделать ваш визит незабываемым и наполнить его теплом и заботой. "
        "Приходите в Mari, чтобы насладиться вкусом и уютом! ❤️"
    )

    await message.answer(about_info)

#----------------------------------------------- Бронирование

@router.message(F.text == "Бронь")
async def register_start(message: Message, state: FSMContext):
    await message.answer("Приступим к бронированию 😊", reply_markup=kb.main_without_bron)
    await state.set_state(Register.rest_id)

    restaurants = await rq_b.all_rest_view()
    if not restaurants:
        await message.answer("Рестораны не найдены.")
        return

    markup = kb.generate_restaurant_buttons(restaurants)
    await message.answer("Выберите ресторан:", reply_markup=markup)

@router.callback_query(Register.rest_id)
async def register_restaurant(callback: CallbackQuery, state: FSMContext):
    try:
        data = callback.data.split(":")
        restaurant_id = int(data[1])
        restaurant_name = data[2]

        await state.update_data(restaurant_id=restaurant_id, restaurant_name=restaurant_name)
        await state.set_state(Register.date)
        await callback.message.answer("Выберите дату бронирования:", reply_markup=kb.generate_date_buttons())
    except Exception:
        await callback.message.answer("Ошибка в выборе ресторана, попробуйте снова.")

@router.callback_query(Register.date)
async def register_date(callback: CallbackQuery, state: FSMContext):
    try:
        day = int(callback.data.split(":")[1])
        date = (datetime.now().date() + timedelta(days=day)).strftime("%d-%m-%Y")

        await state.update_data(date=date)
        await state.set_state(Register.time)
        time_buttons = kb.generate_time_buttons(date)
        await callback.message.answer("Выберите время:", reply_markup=time_buttons)
    except Exception:
        await callback.message.answer("Ошибка в выборе даты, попробуйте снова.")


@router.callback_query(Register.time)
async def register_time(callback: CallbackQuery, state: FSMContext):
    try:
        hour = int(callback.data.split(":")[1])  # Извлекаем выбранное время
        time = f"{hour:02d}:00"  # Форматируем время (например, 18:00)

        await state.update_data(time=time)  # Сохраняем выбранное время в состоянии
        await state.set_state(Register.hours)

        # Генерируем кнопки для выбора количества часов
        hours_buttons = kb.generate_hours_buttons(selected_time=hour)
        await callback.message.answer(
            "Выберите количество часов бронирования:",
            reply_markup=hours_buttons
        )
    except Exception:
        await callback.message.answer("Ошибка в выборе времени, попробуйте снова.")

@router.callback_query(Register.hours)
async def register_hours(callback: CallbackQuery, state: FSMContext):
    try:
        hours = int(callback.data.split(":")[1])
        await state.update_data(hours=hours)

        await state.set_state(Register.number_of_guests)
        await callback.message.answer("Введите количество гостей:")
    except Exception:
        await callback.message.answer("Ошибка в выборе количества часов, попробуйте снова.")

@router.message(Register.number_of_guests)
async def register_guests(message: Message, state: FSMContext):
    if message.text.isdigit():
        number_of_guests = int(message.text)
        if number_of_guests <= 10:  # Ограничение на количество гостей
            data = await state.get_data()
            reservation_time = datetime.strptime(f"{data['date']} {data['time']}", "%d-%m-%Y %H:%M")
            restaurant_id = data['restaurant_id']
            reservation_hours = data['hours']


            suitable_tables = await rq_b.find_suitable_table(restaurant_id, number_of_guests, reservation_time, reservation_hours)

            if suitable_tables:
                markup = kb.generate_table_buttons(suitable_tables)
                await state.update_data(number_of_guests=number_of_guests)
                await state.set_state(Register.table_choice)
                phot = FSInputFile('D:\\PycharmProjects\\bron_kur\\столы2.jpg')
                await message.answer_photo(phot)
                await message.answer("Выберите столик:", reply_markup=markup)
            else:
                await message.answer("Подходящие столы не найдены. Попробуйте другое время.")
                await state.clear()
        else:
            await message.answer("Максимальное количество гостей — 6.\n Пожалуйста, укажите другое количество или обратитесь к администратору.")
    else:
        await message.answer("Пожалуйста, укажите количество гостей числом.")



@router.callback_query(lambda c: c.data and c.data.startswith("select_table:"))
async def register_table_choice(callback: CallbackQuery, state: FSMContext):
    try:
        _, table_id, table_number = callback.data.split(":")
        table_id = int(table_id)
        table_number = int(table_number)

        await state.update_data(table_id=table_id, table_number=table_number)
        await state.set_state(Register.name)
        await callback.message.answer("Введите имя, на которое будет сделано бронирование:")
    except Exception as e:
        print(f"Error in register_table_choice: {e}")
        await callback.message.answer("Ошибка в выборе столика, попробуйте снова.")


@router.message(Register.name)
async def register_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)

    await state.set_state(Register.confirm)
    await confirm_reservation(message, state)

async def confirm_reservation(message: Message, state: FSMContext):
    data = await state.get_data()
    confirmation = (
        f"Подтвердите бронирование:\n"
        f"🏠 Ресторан: {data['restaurant_name']}\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Время: {data['time']}\n"
        f"⌛ Длительность: {data['hours']} ч.\n"
        f"👥 Гостей: {data['number_of_guests']}\n"
        f"🪑 Столик: {data['table_number']}\n"
        f"🙍 Имя: {data['name']}\n"
    )
    await message.answer(confirmation, reply_markup=kb.confirmation_buttons())


# Обработчик подтверждения бронирования
@router.callback_query(lambda c: c.data and c.data.startswith("confirm:"))
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    if callback.data == "confirm:yes":
        data = await state.get_data()
        reservation_time = datetime.strptime(f"{data['date']} {data['time']}", "%d-%m-%Y %H:%M")
        reservation_id = await rq_b.create_reservation(reservation_time,callback.from_user.id, data["name"], data["number_of_guests"],data["hours"],data['table_id'])
        await callback.message.answer("Бронирование успешно создано!")
        await state.update_data(reservation_id=reservation_id)
        await callback.message.answer("Вы хотите сделать предзаказ ?", reply_markup=kb.preorders_buttons())
        # await state.clear()
    elif callback.data == "confirm:no":
        await callback.message.answer("Что вы хотите исправить?", reply_markup=kb.correction_buttons())


#------------------------------PREORDER
@router.callback_query(lambda c: c.data and c.data.startswith("preorder:"))
async def register_preorder(callback: CallbackQuery, state: FSMContext):
    if callback.data == "preorder:yes":
        # Генерация клавиатуры категорий
        markup = await kb.generate_category_keyboard()
        await callback.message.answer("Выберите категорию блюд:", reply_markup=markup)
    elif callback.data == "preorder:no":
        await callback.message.answer("До скорой встречи ", reply_markup=kb.main)
        # await state.set_state(Register.confirm)
        # await confirm_reservation(callback.message, state)




@router.callback_query(lambda c: c.data and c.data.startswith("category:"))
async def select_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]  # Получаем название категории
    menu_items = await rq_b.get_menu_by_category(category)

    if not menu_items:
        await callback.message.answer("В этой категории пока нет блюд.")
        return

    # Генерация клавиатуры блюд
    markup = kb.generate_dish_keyboard(menu_items)
    await callback.message.answer(f"Вы выбрали категорию: {category.capitalize()}.\nВот список доступных блюд:", reply_markup=markup)


@router.callback_query(lambda c: c.data and c.data.startswith("dish:"))
async def select_dish(callback: CallbackQuery, state: FSMContext):
    dish_id = int(callback.data.split(":")[1])  # Получаем ID блюда

    # Генерация клавиатуры для выбора количества
    markup = kb.generate_quantity_keyboard(dish_id)
    await callback.message.answer("Выберите количество порций:", reply_markup=markup)


@router.callback_query(lambda c: c.data and c.data.startswith("quantity:"))
async def select_quantity(callback: CallbackQuery, state: FSMContext):
    _, dish_id, quantity = callback.data.split(":")
    dish_id = int(dish_id)
    quantity = int(quantity)

    # Загружаем информацию о блюде
    async with async_session() as session:
        dish = await session.get(Menu, dish_id)

    if not dish:
        await callback.message.answer("Ошибка: блюдо не найдено.")
        return

    # Сохраняем выбор в FSMContext
    data = await state.get_data()
    cart = data.get("cart", {})  # Корзина пользователя
    if dish_id in cart:
        cart[dish_id]["quantity"] += quantity
    else:
        cart[dish_id] = {
            "name": dish.name_dish,
            "quantity": quantity,
            "price": dish.price,
        }
    await state.update_data(cart=cart)

    # Подтверждаем добавление в корзину
    await callback.message.answer(
        f"{quantity} x {dish.name_dish} добавлено в корзину. Выберите следующее блюдо или завершите заказ.",reply_markup=kb.end_preorder
    )

    # Вернуться к выбору категорий
    markup = await kb.generate_category_keyboard()
    await callback.message.answer("Выберите следующую категорию блюд:", reply_markup=markup)

@router.callback_query(lambda c: c.data == "finish_preorder")
async def finish_preorder(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", {})  # Получаем корзину
    reservation_id = data.get("reservation_id")  # Получаем ID брони

    if not reservation_id:
        await callback.message.answer("Ошибка: не найдено бронирование.")
        return

    if not cart:
        await callback.message.answer("Вы не выбрали ни одного блюда.")
        return

    # Формируем текст с итоговым заказом
    order_summary = "Ваш предзаказ:\n\n"
    total_price = 0

    for dish_id, dish in cart.items():  # Проходим по корзине как по словарю
        order_summary += (
            f"🍽 {dish['name']} - {dish['quantity']} шт. "
            f"({dish['price']} руб. за шт.)\n"
        )
        total_price += dish['quantity'] * dish['price']

    order_summary += f"\n💵 Итого: {total_price} руб."

    # Выводим итоговый заказ
    await callback.message.answer(order_summary)

    try:
        # Создаем предзаказ
        await rq_b.create_preorder(reservation_id, cart)

        # Подтверждение успешного предзаказа
        await callback.message.answer("Предзаказ успешно создан! До скорой встречи!",reply_markup=kb.main)
        await state.clear()  # Это завершит состояние
    except Exception as e:
        await callback.message.answer(f"Ошибка при создании предзаказа: {str(e)}")



@router.callback_query(lambda c: c.data == "back_to_categories")
async def back_to_categories_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Вернуться к категориям".
    """
    # Генерируем клавиатуру с категориями
    category_keyboard = await kb.generate_category_keyboard()

    # Редактируем сообщение, заменяя клавиатуру
    await callback.message.edit_text(
        "Выберите категорию:",
        reply_markup=category_keyboard
    )


#-------------------ОРГАНИЗАЦИЯ МЕРОПРИЯТИЙ
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext




@router.message(F.text == 'Организовать мероприятие')
async def start_event_process(message: Message, state: FSMContext):
    await message.answer("Какое мероприятие вы хотите организовать?", reply_markup=kb.event_types_keyboard)
    await state.set_state(EventApplicationStates.event_type)


@router.message(EventApplicationStates.event_type)
async def process_event_type(message: Message, state: FSMContext):
    event_type = message.text.strip()
    await state.update_data(event_type=event_type)

    # Получаем рекомендации ресторанов по типу события
    restaurants = await rq_b.get_recommended_restaurants(event_type)

    if not restaurants:
        await message.answer("Пока нет рекомендаций для этого типа мероприятия.")
        return

    restaurant_list = "\n".join([
        f"{r['restaurant_name']} - {r['address']}\n({r['recommendation_description']})"
        for r in restaurants
    ])

    await message.answer(f"Рекомендуемые заведения:\n\n{restaurant_list}")
    await message.answer("Хотите выбрать конкретное заведение или оставить пустым?")
    await state.set_state(EventApplicationStates.restaurant_choice)


@router.message(EventApplicationStates.restaurant_choice)
async def process_restaurant_choice(message: Message, state: FSMContext):
    restaurant_choice = message.text.strip()
    await state.update_data(restaurant_choice=restaurant_choice)

    await message.answer("Укажите желаемую дату проведения мероприятия (например, 2025-06-15 18:00):")
    await state.set_state(EventApplicationStates.requested_date)


@router.message(EventApplicationStates.requested_date)
async def process_requested_date(message: Message, state: FSMContext):
    date_time = message.text.strip()
    await state.update_data(requested_date=date_time)

    await message.answer("Сколько человек будет на мероприятии?")
    await state.set_state(EventApplicationStates.guest_count)


@router.message(EventApplicationStates.guest_count)
async def process_guest_count(message: Message, state: FSMContext):
    guest_count = int(message.text.strip())
    await state.update_data(guest_count=guest_count)

    await message.answer("Если хотите, можете добавить дополнительное сообщение для менеджера:")
    await state.set_state(EventApplicationStates.message_to_manager)


@router.message(EventApplicationStates.message_to_manager)
async def process_message_to_manager(message: Message, state: FSMContext):
    message_text = message.text.strip()
    await state.update_data(message=message_text)

    data = await state.get_data()

    await message.answer(
        f"Вы хотите оформить заявку на мероприятие:\n"
        f"Тип: {data['event_type']}\n"
        f"Заведение: {data['restaurant_choice']}\n"
        f"Дата: {data['requested_date']}\n"
        f"Гостей: {data['guest_count']}\n"
        f"Сообщение: {data['message']}\n\n"
        "Подтвердите отправку заявки?",
        reply_markup=kb.confirm_keyboard()
    )

    await state.set_state(EventApplicationStates.confirm_application)

@router.callback_query(EventApplicationStates.confirm_application, F.data == "confirm_application")
async def confirm_application(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    async with async_session() as session:
        result = await session.execute(
            select(Clients.client_id).where(Clients.tg_id == callback.from_user.id)
        )
        client_id_db = result.scalar()
        if not client_id_db:
            await callback.message.edit_text("Ошибка: не найден ваш профиль в системе.")
            await state.clear()
            return

        result = await session.execute(
            select(EventTypes.event_type_id).where(EventTypes.name == data['event_type'])
        )
        event_type_id = result.scalar()
        if not event_type_id:
            await callback.message.edit_text("Ошибка: неизвестный тип мероприятия.")
            await state.clear()
            return

        restaurant_id = None
        if data['restaurant_choice'] and data['restaurant_choice'] != 'Нет':
            result = await session.execute(
                select(Restaurants.restaurant_id).where(Restaurants.restaurant_name.ilike(f"%{data['restaurant_choice']}%"))
            )
            restaurant_id = result.scalar()

        try:
            requested_date = datetime.strptime(data['requested_date'], "%Y-%m-%d %H:%M")
        except ValueError:
            await callback.message.edit_text("Ошибка: неверный формат даты.")
            await state.clear()
            return

        application = EventApplications(
            client_id=client_id_db,
            event_type_id=event_type_id,
            restaurant_id=restaurant_id,
            requested_date=requested_date,
            guest_count=int(data['guest_count']),
            message=data.get('message', ''),
        )

        session.add(application)
        await session.commit()

    await callback.message.answer("✅ Ваша заявка принята! Менеджер свяжется с вами в ближайшее время.",reply_markup=kb.main)
    await state.clear()


@router.message(EventApplicationStates.confirm_application, F.text == "Отменить")
async def cancel_application(message: Message, state: FSMContext):
    await message.answer("Оформление заявки отменено.")
    await state.clear()

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State


class AIState(StatesGroup):
    active = State()

@router.message(Command("aihelp"))
async def ai_help(message: Message, state: FSMContext):
    await message.answer(
        "Вы вошли в режим AI-гидa.\nВыберите действие:",
        reply_markup=kb.ai_reply_keyboard()
    )

# Обработка reply-кнопок
@router.message(F.text == "🔮 Включить AI-режим")
async def ai_on(message: Message, state: FSMContext):
    await state.set_state(AIState.active)
    await state.update_data(ai_mode=True)
    await message.answer("AI-режим включен! Задавайте свой вопрос, например: «Посоветуй итальянский ресторан для компании».")

@router.message(F.text == "🚫 Выключить AI-режим")
async def ai_off(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("AI-режим выключен. Возвращаюсь в главное меню:", reply_markup=kb.main)

@router.message(F.text == "↩️ Выйти в главное меню")
async def exit_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=kb.main)

@router.message()
async def handle_any_message(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("ai_mode"):
        await message.answer("Думаю... 🤖")
        response = ask_llm_ollama(message.text)
        await message.answer(response)
    else:
        await message.answer("Выберите команду из меню или введите /aihelp для активации AI-гида.")

