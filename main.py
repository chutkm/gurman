import datetime
from aiogram import Bot, Dispatcher
from aiogram.dispatcher import router
from quart import request, session, send_file, jsonify
import asyncio
from app.handlers import router
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher
from quart import Quart, render_template, redirect, url_for
from sqlalchemy import func
from sqlalchemy import select, and_
from app.database.models import async_main, Reservations, async_session, Tables, Preorder
from app.database.requests import get_all_reservations, verify_admin_credentials, \
    get_reservations_by_restaurant, get_all_reservations, get_all_restaurants, delete_reservation_by_id, \
    get_reservations_by_period, update_reservation_by_id, get_reservation_by_id
from dotenv import load_dotenv
import os

# Создание экземпляра веб-приложения
app = Quart(__name__, template_folder='templates')
import logging

logging.basicConfig(level=logging.DEBUG)

# --- Маршруты для веб-приложения ---
@app.route('/')
async def login():
    """Страница авторизации администратора."""
    return await render_template('base.html')


@app.route('/login', methods=['GET', 'POST'])
async def handle_login():
    try:
        form_data = await request.form
        email = form_data.get('email')
        password = form_data.get('password')

        admin = await verify_admin_credentials(email, password)
        if admin:
            session['logged_in'] = True
            session['admin_id'] = admin.admin_id  # Сохраняем ID администратора в сессии
            return redirect(url_for('admin_panel'))
        return "Неверный email или пароль", 401
    except Exception as e:
        print(f"Ошибка при авторизации: {e}")
        return "Внутренняя ошибка сервера", 500



# Обработчик обновления резервации
@app.route('/update_reservation', methods=['POST'])
async def update_reservation():
    try:
        # Получаем данные из тела запроса
        data = await request.get_json()

        reservation_id = data.get('reservation_id')
        reservation_name = data.get('reservation_name')
        reservation_date_time = data.get('reservation_date_time')
        guest_count = data.get('guest_count')
        reservation_hours = data.get('reservation_hours')  # Это число, которое передается
        table_number = data.get('table_number')
        restaurant_id = data.get('restaurant_id')

        # Проверка наличия всех данных
        if not all([reservation_id, reservation_name, reservation_date_time, guest_count, reservation_hours, table_number, restaurant_id]):
            return jsonify({'error': 'Не все данные переданы'}), 400

        # Преобразуем данные в нужные типы
        guest_count = int(guest_count)
        reservation_hours = int(reservation_hours)
        from datetime import datetime, timedelta

        # Конвертируем время бронирования в datetime
        reservation_start = datetime.fromisoformat(reservation_date_time)
        reservation_end = reservation_start + timedelta(hours=reservation_hours)

        # Подключаемся к базе данных
        async with async_session() as session:
            # Получаем текущее бронирование для проверки изменений
            result = await session.execute(select(Reservations).filter(Reservations.reservation_id == reservation_id))
            reservation = result.scalar_one_or_none()

            if not reservation:
                return jsonify({'error': 'Резервация не найдена'}), 404

            # Получаем новый столик
            table = await session.execute(
                select(Tables).filter(Tables.restaurant_id == restaurant_id, Tables.table_number == table_number)
            )
            new_table = table.scalar_one_or_none()

            if not new_table:
                return jsonify({'error': 'Столик не найден для выбранного ресторана'}), 400

            # Проверка изменений времени или столика
            if reservation.reservation_date_time != reservation_start or reservation.table_id != new_table.table_id:
                # Получаем все бронирования для указанного столика
                result = await session.execute(
                    select(Reservations.reservation_date_time)
                    .join(Tables, Reservations.table_id == Tables.table_id)
                    .filter(
                        Tables.restaurant_id == restaurant_id,
                        Tables.table_number == table_number,
                        Reservations.reservation_id != reservation_id  # Исключаем текущее бронирование
                    ).where(func.date(Reservations.reservation_date_time) == reservation_start.date())  # Исправлено

                )
                reservations = result.scalars().all()

                # Проверка на пересечение временных интервалов
                for existing_reservation_start in reservations:
                    existing_reservation_end = existing_reservation_start + timedelta(hours=reservation_hours)

                    # Логирование текущего бронирования
                    logger.info(f"Проверяем бронирование: {existing_reservation_start} - {existing_reservation_end}")
                    logger.info(f"Новое бронирование: {reservation_start} - {reservation_end}")

                    # Проверка пересечения дат и времени
                    if (reservation_start.date() == existing_reservation_start.date() and
                            not (
                                    reservation_end <= existing_reservation_start or reservation_start >= existing_reservation_end)):
                        # Логирование пересечения
                        logger.info(f"Пересечение найдено: {existing_reservation_start} - {existing_reservation_end} "
                                    f"с {reservation_start} - {reservation_end}")
                        return jsonify({'error': 'Выбранное время занято. Выберите другое время или столик.'}), 400

            # Обновляем данные бронирования
            reservation.reservation_name = reservation_name
            reservation.reservation_date_time = reservation_start
            reservation.reservation_hours = reservation_hours
            reservation.guest_count = guest_count
            reservation.table_id = new_table.table_id

            # Сохраняем изменения
            await session.commit()

        # Возвращаем успешный ответ
        return jsonify({'status': 'success', 'message': 'Резервация обновлена успешно'}), 200

    except Exception as e:
        # Логируем ошибку
        logger.error(f"Ошибка при обновлении бронирования: {str(e)}")
        return jsonify({'error': str(e)}), 500




@app.route('/admin', methods=['GET'])
async def admin_panel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    restaurant_id = request.args.get('restaurant_id', type=int)
    restaurants = await get_all_restaurants()

    if restaurant_id:
        reservations = await get_reservations_by_restaurant(restaurant_id)
    else:
        reservations = await get_all_reservations()

    return await render_template(
        'index.html',
        reservations=reservations,
        restaurants=restaurants,
        selected_restaurant_id=restaurant_id
    )


@app.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
async def delete_reservation(reservation_id):
    """Удаление бронирования."""
    await delete_reservation_by_id(reservation_id)
    return redirect(url_for('admin_panel'))

@app.route('/edit_reservation/')
async def edit_reservation():
    pass





#-------------------------ОТЧЕТ
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
# Подготовка PDF с использованием Paragraph
import logging
from datetime import datetime

# Подключаем шрифт, который поддерживает кириллицу
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))  # Убедитесь, что путь к файлу корректен


# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

async def generate_pdf(reservations, pdf_path, period, report_date):
    # Генерация PDF в фоновом потоке, чтобы не блокировать выполнение других задач
    await asyncio.to_thread(_generate_pdf_sync, reservations, pdf_path, period, report_date)

def _generate_pdf_sync(reservations, pdf_path, period, report_date):
    logger.info("Начинаем генерацию PDF отчета.")

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []

    # Подключаем шрифт с поддержкой кириллицы
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    # Стили
    title_style = ParagraphStyle(
        name='Title',
        fontName='DejaVuSans',
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10
    )

    normal_style = ParagraphStyle(
        name='Normal',
        fontName='DejaVuSans',
        fontSize=10,
        alignment=TA_CENTER
    )

    # Заголовки отчета
    elements.append(Paragraph("ОТЧЕТ", title_style))
    elements.append(Paragraph("о бронировании столиков в ресторане «Mari»", normal_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Текстовые данные для отчета
    period_text = {
        'week': 'неделя',
        'month': 'месяц'
    }.get(period, 'день')


    address = "Адрес ресторана не указан"  # Если нужно, замените на реальный адрес

    elements.append(Paragraph(f"За период: {period_text} с {report_date.strftime('%d.%m.%Y')  }", normal_style))
    elements.append(Paragraph(f"Дата создания отчета: {report_date.strftime('%d.%m.%Y %H:%M')}", normal_style))
    elements.append(Paragraph(f"Количество бронирований: {len(reservations)}", normal_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Стили текста для других частей
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontName = 'DejaVuSans'

    # Заголовки таблицы
    data = [
        ["Дата и время", "Имя", "Гости", "Часы", "Столик", "Предзаказ", "Статус"]
    ]

    logger.debug("Добавляем данные бронирований.")

    # Данные бронирований
    for reservation in reservations:
        try:
            reservation_data = [
                reservation.get('reservation_date_time', 'Не указано').strftime('%d.%m.%Y %H:%M') if reservation.get(
                    'reservation_date_time') else 'Не указано',
                reservation['reservation_name'],
                str(reservation['guest_count']),
                str(reservation['reservation_hours']),
                str(reservation['table_number']),
                reservation['preorder_details'],
                reservation['reservation_status']
            ]
            data.append(reservation_data)
        except Exception as e:
            logger.error(f"Ошибка при обработке бронирования: {e}")
            continue

    logger.debug(f"Сформировано {len(reservations)} бронирований.")

    if len(data) == 1:
        elements.append(Paragraph("Нет данных о бронированиях.", normal_style))
    else:
        # Создание таблицы
        # table = Table(data)
        # Установим общую ширину таблицы в зависимости от ширины страницы
        page_width, _ = letter
        table_width = page_width - 0.1 * inch  # Отступы по дюйму с каждой стороны

        # Распределение ширины колонок (относительное)
        col_widths = [0.15 * table_width,  # Дата и время
                      0.17 * table_width,  # Имя
                      0.08 * table_width,  # Гости
                      0.1 * table_width,  # Часы
                      0.1 * table_width,  # Столик
                      0.25 * table_width,  # Предзаказ
                      0.15 * table_width]  # Статус

        # Создание таблицы с динамическими ширинами колонок
        table = Table(data, colWidths=col_widths)


        # Применение стиля таблицы
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10)
        ])
        table.setStyle(style)


    logger.debug("Добавляем таблицу в отчет.")

    # Добавление дополнительного отступа перед таблицей
    elements.append(Spacer(1,  10))  # Отступ между текстом и таблицей

    # Добавление таблицы в PDF
    elements.append(table)


    # Раздел подписи
    elements.extend([
        Spacer(1, 0.9 * inch),
        Paragraph("Получил отчет о бронировании:", normal_style),
        Paragraph("__________ (подпись)   ________________________(ФИО)", normal_style)
    ])


    try:
        # Генерация PDF
        doc.build(elements)
        logger.info(f"PDF отчет успешно сгенерирован: {pdf_path}")
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}")


# Измененный роутер
@app.route('/generate_report', methods=['POST'])
async def generate_report():
    form = await request.form
    period = form.get('period')
    restaurant_id = form.get('restaurant_id')  # Получаем restaurant_id из формы

    if not restaurant_id:
        # Обработка ошибки, если restaurant_id не был передан
        return "Ресторан не выбран.", 400

    # Получаем данные о  бронированиях
    reservations = await get_reservations_by_period(restaurant_id, period)

    if not reservations:
        return "Нет данных для отчета.", 404

    # Подключение шрифта с поддержкой кириллицы
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

    # Генерация PDF в отдельном потоке
    pdf_path = "report.pdf"
    report_date = datetime.now()
    await generate_pdf(reservations, pdf_path, period, report_date)

    # Отправка PDF-файла внутри правильного контекста запроса
    return await send_file(pdf_path, as_attachment=True)

# Загружаем переменные из .env
load_dotenv()

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Функция для запуска бота
async def start_bot():
    bot = Bot(token=BOT_TOKEN)
    await async_main()  # Инициализация базы данных
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
# Секретный ключ для сессий

app.secret_key = "your_secret_key"


async def start_web():
    await app.run_task(debug=True)



async def main():

    bot_task = asyncio.create_task(start_bot())
    web_task = asyncio.create_task(start_web())
    # Построение графика

    try:

        await asyncio.gather(bot_task,web_task)
    except KeyboardInterrupt:
        print("Приложение остановлено")
    finally:
        plt.show()





if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
            print("Бот выключен")