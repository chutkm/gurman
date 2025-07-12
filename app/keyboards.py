from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
# import locale
# locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
# Создаем функцию для генерации callback данных
import app.database.requests_bot as rq_b
def make_callback_data(action, value):
    return f"{action}:{value}"

def booking_keyboard(booking_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру для управления бронированием.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Предзаказ", callback_data=f"preorder_history:{booking_id}")],
            [InlineKeyboardButton(text="Отменить", callback_data=f"cancel_history:{booking_id}")],
            [InlineKeyboardButton(text="Оставить отзыв", callback_data=f"review_history:{booking_id}")]
        ]
    )
#----------------------
async def generate_category_keyboard():
    """
    Генерирует клавиатуру с категориями блюд по одной кнопке в строке.
    """
    categories = await rq_b.get_categories()  # Получаем список категорий
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки для каждой категории
    for category in categories:
        builder.row(
            InlineKeyboardButton(text=category.capitalize(), callback_data=f"category:{category}")
        )



    return builder.as_markup()

def generate_dish_keyboard(menu_items):
    """
    Генерирует клавиатуру с блюдами из выбранной категории и кнопкой завершения предзаказа.
    """
    markup = InlineKeyboardBuilder()

    # Добавляем кнопки с блюдами
    buttons_row = []
    for i, item in enumerate(menu_items):
        callback_data = f"dish:{item.menu_id}"  # Уникальное callback_data для каждого блюда
        buttons_row.append(InlineKeyboardButton(
            text=f"{item.name_dish} - {item.price} р.",
            callback_data=callback_data
        ))

        # Когда в строке 2 кнопки, добавляем строку
        if len(buttons_row) == 1:
            markup.row(*buttons_row)  # Добавляем 2 кнопки в одну строку
            buttons_row = []  # Очищаем список кнопок для следующей строки

    # Если осталась одна кнопка в последней строке, добавляем её
    if buttons_row:
        markup.row(*buttons_row)

    # Добавляем кнопку "Вернуться к категориям"
    back_to_categories_button = InlineKeyboardButton(
        text="⬅️ Вернуться к категориям",
        callback_data="back_to_categories"
    )
    markup.row(back_to_categories_button)

    return markup.as_markup()

# Клавиатура для выбора количества
def generate_quantity_keyboard(dish_id):
    """
    Генерирует клавиатуру для выбора количества блюда.
    """
    markup = InlineKeyboardBuilder()
    for i in range(1, 6):  # Количество от 1 до 10
        callback_data = f"quantity:{dish_id}:{i}"
        markup.add(InlineKeyboardButton(text=str(i), callback_data=callback_data))



    return markup.as_markup()



# Создаём клавиатуру с кнопкой "Завершить предзаказ"
end_preorder = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(
        text="Завершить предзаказ",
        callback_data="finish_preorder"
    )]
])
main = ReplyKeyboardMarkup(
    keyboard=[
        # [KeyboardButton(text='Найти Ресторан 🍽')],
        # [KeyboardButton(text='Мероприятие 🎉')],
        [KeyboardButton(text='Бронь'),KeyboardButton(text='Мои бронирования')],
        [KeyboardButton(text='Организовать мероприятие'),],
        [KeyboardButton(text='Популярные кухни и блюда 🍜')],
        [KeyboardButton(text='Часто ищут 🔎'), KeyboardButton(text='Акции и новинки')]#Скидки и Акции
    ],
    resize_keyboard=True,
    input_field_placeholder='Выберите пункт который вас интересует'
)
#--------------LLMs
# def ai_mode_buttons():
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="🔮 Включить AI-режим", callback_data="ai_on")],
#         [InlineKeyboardButton(text="🚫 Выключить AI-режим", callback_data="ai_off")]
#     ])
def ai_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔮 Включить AI-режим")],
            [KeyboardButton(text="🚫 Выключить AI-режим")],
            [KeyboardButton(text="↩️ Выйти в главное меню")]
        ],
        resize_keyboard=True
    )


def salas_new_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Скидки и Акции', callback_data='promotions')],
            [InlineKeyboardButton(text='Новинки в меню', callback_data='new_dishes')],
            [InlineKeyboardButton(text='Новости ресторанной индустрии', callback_data='news')],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")]
        ]
    )

def get_popular_kitchen_keyboard() -> InlineKeyboardMarkup:
    category_kitchens = [
        "Грузинские рестораны",
        "Итальянские рестораны",
        "Японские рестораны",
        "Стейки",
        "Рыба и морепродукты",
        "Лучшие бургеры"
    ]

    inline_keyboard = []
    for i in range(0, len(category_kitchens), 2):
        row = []
        # Формируем callback_data по имени категории
        row.append(
            InlineKeyboardButton(
                text=category_kitchens[i],
                callback_data=f"kitchen_{category_kitchens[i].replace(' ', '_').lower()}"
            )
        )
        if i + 1 < len(category_kitchens):
            row.append(
                InlineKeyboardButton(
                    text=category_kitchens[i + 1],
                    callback_data=f"kitchen_{category_kitchens[i + 1].replace(' ', '_').lower()}"
                )
            )
        inline_keyboard.append(row)

    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def back_to_popular_kitchens_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к популярным кухням", callback_data="back_to_popular_kitchens")]
        ]
    )

def get_categories_keyboard() -> InlineKeyboardMarkup:
    categories = [
        "Куда пойти с детьми 👨‍👩‍👧‍👦 ",
        "Новые рестораны 🆕",
        "Рестораны в центре Москвы 🏙",
        "Рестораны и кафе с верандой 🌿",
        "Рестораны с ланчами 🍽",
        "Кофейни Москвы ☕️"
    ]

    # Формируем список списков кнопок, по 2 в ряд
    inline_keyboard = []
    for i in range(0, len(categories), 2):
        row = []
        row.append(
            InlineKeyboardButton(text=categories[i], callback_data=f"category_{i}")
        )
        if i + 1 < len(categories):
            row.append(
                InlineKeyboardButton(text=categories[i + 1], callback_data=f"category_{i + 1}")
            )
        inline_keyboard.append(row)

    # Кнопка "Назад в меню" в отдельной строке
    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

main_without_bron = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Контакты'), KeyboardButton(text='О нас')]
    ],
    resize_keyboard=True,
    input_field_placeholder='Введите информацию'
)

# back_menu = InlineKeyboardMarkup(inline_keyboard=[
#     [InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back')]
# ])


get_number = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Отправить номер', request_contact=True)],
        [KeyboardButton(text='Ввести номер вручную')]
    ],
    resize_keyboard=True
)


def generate_restaurant_buttons(restaurants):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for restaurant in restaurants:
        # Преобразуем название ресторана в безопасный формат
        restaurant_name = restaurant.restaurant_name[:64]  # Ограничиваем длину названия

        # Формируем callback_data
        callback_data = f"restaurant:{restaurant.restaurant_id}:{restaurant_name}"

        # Проверка длины callback_data
        if len(callback_data) > 64:
            callback_data = callback_data[:64]  # Обрезаем если длина превышает

        # Добавляем кнопку для ресторана
        keyboard.inline_keyboard.append([  # Добавляем строку кнопок
            InlineKeyboardButton(
                text=restaurant.restaurant_name,  # Текст на кнопке
                callback_data=callback_data  # Данные, передаваемые при нажатии
            )
        ])

    # Добавляем кнопку "Назад в меню" в отдельной строке после цикла
    back_button = InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")
    keyboard.inline_keyboard.append([back_button])

    return keyboard



def generate_date_buttons():
    today = datetime.now().date()
    buttons = []

    # Добавляем кнопки для выбора дат
    for i in range(7):  # Предлагаем выбор из 7 дней
        date = today + timedelta(days=i)
        buttons.append(
            InlineKeyboardButton(
                text=date.strftime('%a, %d.%m'),
                callback_data=make_callback_data("date", i)
            )
        )

    # Добавляем кнопку "Назад" в отдельной строке
    back_button = InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")

    # Формируем клавиатуру
    inline_keyboard = [
        buttons[:4],  # Первая строка: 4 дня
        buttons[4:7], # Вторая строка: 3 дня
        [back_button] # Третья строка: кнопка "Назад"
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def generate_hours_buttons(selected_time: int):
    """
    Генерирует кнопки для выбора количества часов бронирования в зависимости от выбранного времени.

    :param selected_time: Выбранное время (в часах, например, 18 для 18:00)
    """
    builder = InlineKeyboardBuilder()
    closing_hour = 22  # Ресторан закрывается в 22:00

    # Ограничение на максимальное количество часов
    max_hours = min(closing_hour - selected_time, 5)

    for hour_ in range(1, max_hours + 1):  # Генерируем только доступные часы
        builder.add(
            InlineKeyboardButton(
                text=f"{hour_} час" if hour_ == 1 else f"{hour_} часа",
                callback_data=make_callback_data("hours", hour_)
            )
        )

    # Кнопка "Назад в меню"
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back"))
    return builder.as_markup()



def generate_time_buttons(selected_date: str) -> InlineKeyboardMarkup:
    now = datetime.now()
    builder = InlineKeyboardBuilder()
    time_slots = range(10, 22)  # Например, с 10:00 до 22:00

    # Если выбранная дата - сегодня, исключаем прошедшее время
    if selected_date == now.strftime("%d-%m-%Y"):
        time_slots = [hour for hour in time_slots if hour > now.hour]

    # Создаём кнопки для каждого доступного временного интервала
    for hour in time_slots:
        builder.button(
            text=f"{hour:02d}:00",
            callback_data=f"time:{hour}"
        )

    # Кнопка "Назад"
    builder.button(
        text="⬅️ Назад",
        callback_data="back"
    )

    # Финализируем клавиатуру
    return builder.as_markup()


# Генерация разметки для выбора столика
from aiogram.utils.keyboard import InlineKeyboardBuilder

def generate_table_buttons(suitable_tables):
    builder = InlineKeyboardBuilder()

    buttons_row = []

    for i, table in enumerate(suitable_tables):
        buttons_row.append(
            InlineKeyboardButton(
                text=f"Стол №{table.table_number} ({table.place_type})",
                callback_data=f"select_table:{table.table_id}:{table.table_number}"
            )
        )

        if len(buttons_row) == 2:
            builder.row(*buttons_row)
            buttons_row = []

    if buttons_row:
        builder.row(*buttons_row)

    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back"))

    return builder.as_markup()


def preorders_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="preorder:yes")],
        [InlineKeyboardButton(text="Нет", callback_data="preorder:no")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")]
    ])


#клава при утверждении инфы о брони - верная ли она или нет
def confirmation_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="confirm:yes")],
        [InlineKeyboardButton(text="Нет", callback_data="confirm:no")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")]
    ])

def correction_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дата", callback_data="correct:date")],
        [InlineKeyboardButton(text="Время", callback_data="correct:time")],
        [InlineKeyboardButton(text="Количество гостей", callback_data="correct:guests")],
        [InlineKeyboardButton(text="Имя", callback_data="correct:name")],
        [InlineKeyboardButton(text="Номер телефона", callback_data="correct:number")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

#отмена брони
def cancel_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="cancel:yes")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel:no")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")]
    ])


def find_restaurant_button():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Найти ресторан 🍽"))
    return kb


#назад к категориям
def back_to_categories_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="show_categories")]
        ]
    )



#---------мероприятие

# Клавиатура выбора типа мероприятия
event_types_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Свадьба")],
        [KeyboardButton(text="Банкет")],
        [KeyboardButton(text="Детский праздник")],
        [KeyboardButton(text="Юбилей")],
        [KeyboardButton(text="Вендинг")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_application")],
            [InlineKeyboardButton(text="Отменить", callback_data="cancel_application")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")]
        ]
    )