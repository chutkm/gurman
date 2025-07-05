import asyncio
from aiogram import Bot, Dispatcher
from quart import Quart, render_template, redirect, url_for
import locale
# from app.handlers import router
from app.database.models import async_main
from app.database.requests import get_all_reservations, delete_reservation_by_id
import logging
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

app = Quart(__name__, template_folder='templates')
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

@app.route('/')
async def index():
    try:
        reservations = await get_all_reservations()
        return await render_template('index.html', reservations=reservations)
    except Exception as e:
        return str(e)


@app.route('/delete/<int:reservation_id>')
async def delete_reservation(reservation_id):
    await delete_reservation_by_id(reservation_id)
    return redirect(url_for('index'))

from quart import request, session

# Фиктивные учетные данные администратора
ADMIN_CREDENTIALS = {"email": "admin@example.com", "password": "admin123"}

@app.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        form_data = await request.form
        email = form_data.get('email')
        password = form_data.get('password')

        # Проверка учетных данных
        if email == ADMIN_CREDENTIALS['email'] and password == ADMIN_CREDENTIALS['password']:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        return "Неверный email или пароль", 401

    return await render_template('base.html')


#
# @app.route('/admin')
# async def admin_panel():
#     if not session.get('logged_in'):
#         return redirect(url_for('login'))
#     reservations = await get_all_reservations()
#     return await render_template('index.html', reservations=reservations)


# @app.route('/add', methods=['GET', 'POST'])
# async def add_reservation():
#     if request.method == 'POST':
#         name = request.form['name']
#         date = request.form['date']
#         time = request.form['time']
#         guests = request.form['guests']
#         # Здесь добавьте код для сохранения новой записи в базе данных
#         await add_reservation_to_db(name, date, time, guests)
#         return redirect(url_for('index'))
#
#     return await render_template('add_reservation.html')