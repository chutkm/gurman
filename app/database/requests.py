from quart import logging
from sqlalchemy.future import select
from app.database.models import Reservations, async_session, Administrators, Restaurants, Tables, Preorder, Menu
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from app.database.models import Reservations, Restaurants, async_session

from sqlalchemy.sql import select, func
from sqlalchemy.exc import SQLAlchemyError


# Функция для удаления бронирования по ID
async def delete_reservation_by_id(reservation_id):
    try:
        async with async_session() as session:
            reservation = await session.get(Reservations, reservation_id)
            if reservation:
                await session.delete(reservation)
                await session.commit()
                print(f"Reservation {reservation_id} deleted successfully.")
            else:
                print(f"Reservation with ID {reservation_id} not found.")
    except SQLAlchemyError as e:
        print(f"Error deleting reservation {reservation_id}: {e}")
        await session.rollback()  # Откатить транзакцию при ошибке
        print("Transaction rolled back due to error.")

# Получить все бронирования
async def get_all_reservations():
    """Получить список всех бронирований."""
    try:
        async with async_session() as session:
            query = select(Reservations)
            result = await session.execute(query)
            reservations = result.scalars().all()
            print(f"Retrieved {len(reservations)} reservations.")
            return reservations
    except SQLAlchemyError as e:
        print(f"Error retrieving reservations: {e}")
        await session.rollback()  # Откатить транзакцию при ошибке
        print("Transaction rolled back due to error.")

# Получить бронирования для определенного ресторана с номерами столиков
# async def get_reservations_by_restaurant(restaurant_id):
#     """Получить бронирования для определенного ресторана с номерами столиков."""
#     try:
#         async with async_session() as session:
#             # Запрос с объединением таблиц Reservations и Tables
#             query = (
#                 select(Reservations, Tables)
#                 .join(Tables, Reservations.table_id == Tables.table_id)
#                 .where(Tables.restaurant_id == restaurant_id)
#             )
#
#             # Выполнение запроса
#             result = await session.execute(query)
#
#             # Преобразуем строки результата в объекты моделей и выводим для отладки
#             reservations = []
#             for reservation, table in result.fetchall():
#                 print(f"Reservation ID: {reservation.reservation_id}, Table Number: {table.table_number}")
#                 reservations.append({
#                     "reservation_id": reservation.reservation_id,
#                     "reservation_date_time": reservation.reservation_date_time,
#                     "reservation_name": reservation.reservation_name,
#                     "guest_count": reservation.guest_count,
#                     "reservation_hours": reservation.reservation_hours,
#                     "reservation_status": reservation.reservation_status,
#                     "table_number": table.table_number  # Номер столика
#                 })
#
#             print(f"Retrieved {len(reservations)} reservations for restaurant {restaurant_id}.")
#             return reservations
#     except SQLAlchemyError as e:
#         print(f"Error retrieving reservations for restaurant {restaurant_id}: {e}")
#         await session.rollback()  # Откатить транзакцию при ошибке
#         print("Transaction rolled back due to error.")


# async def get_reservations_by_restaurant(restaurant_id):
#     """Получить бронирования для определенного ресторана с номерами столиков и предзаказами."""
#     try:
#         async with async_session() as session:
#             # Запрос с объединением таблиц Reservations, Tables и PreOrders
#             query = (
#                 select(Reservations, Tables, Preorder)
#                 .join(Tables, Reservations.table_id == Tables.table_id)
#                 .join(Preorder, Reservations.reservation_id == Preorder.reservation_id)
#                 .where(Tables.restaurant_id == restaurant_id)
#             )
#
#             # Выполнение запроса
#             result = await session.execute(query)
#
#             # Преобразуем строки результата в объекты моделей и выводим для отладки
#             reservations = []
#             for reservation, table, preorder in result.fetchall():
#                 print(f"Reservation ID: {reservation.reservation_id}, Table Number: {table.table_number}, PreOrder: {preorder}")
#                 reservations.append({
#                     "reservation_id": reservation.reservation_id,
#                     "reservation_date_time": reservation.reservation_date_time,
#                     "reservation_name": reservation.reservation_name,
#                     "guest_count": reservation.guest_count,
#                     "reservation_hours": reservation.reservation_hours,
#                     "reservation_status": reservation.reservation_status,
#                     "table_number": table.table_number,  # Номер столика
#                     "preorder_menu_id": preorder.menu_id if preorder else None,
#                     "preorder_quantity": preorder.quantity if preorder else None
#                 })
#
#             print(f"Retrieved {len(reservations)} reservations for restaurant {restaurant_id}.")
#             return reservations
#     except SQLAlchemyError as e:
#         print(f"Error retrieving reservations for restaurant {restaurant_id}: {e}")
#         await session.rollback()  # Откатить транзакцию при ошибке
#         print("Transaction rolled back due to error.")
from sqlalchemy.future import select

from sqlalchemy import func

async def get_reservations_by_restaurant(restaurant_id):
    """Получить бронирования для определенного ресторана с предзаказами в виде списка."""
    try:
        async with async_session() as session:
            query = (
                select(
                    Reservations.reservation_id,
                    Reservations.reservation_date_time,
                    Reservations.reservation_name,
                    Reservations.guest_count,
                    Reservations.reservation_status,
                    Reservations.reservation_hours,
                    Tables.table_number,
                    func.group_concat(
                        func.concat(Menu.name_dish, ' (x', Preorder.quantity, ')'), ';\n '
                    ).label("preorder_details")
                )
                .join(Preorder, Reservations.reservation_id == Preorder.reservation_id, isouter=True)
                .join(Menu, Preorder.menu_id == Menu.menu_id, isouter=True)
                .join(Tables, Reservations.table_id == Tables.table_id)
                .where(Tables.restaurant_id == restaurant_id)
                .group_by(
                    Reservations.reservation_id,
                    Reservations.reservation_date_time,
                    Reservations.reservation_name,
                    Reservations.guest_count,
                    Reservations.reservation_status,
                    Reservations.reservation_hours,
                    Tables.table_number
                )
            )
            result = await session.execute(query)
            reservations = [
                {
                    "reservation_id": r.reservation_id,
                    "reservation_date_time": r.reservation_date_time,
                    "reservation_name": r.reservation_name,
                    "guest_count": r.guest_count,
                    "reservation_status": r.reservation_status,
                    "reservation_hours": r.reservation_hours,
                    "table_number": r.table_number,
                    "preorder_details": r.preorder_details or "Нет предзаказов",
                }
                for r in result
            ]
            return reservations
    except Exception as e:
        logging.error(f"Ошибка получения бронирований с предзаказами: {e}")
        return []



# Получить все рестораны
async def get_all_restaurants():
    """Получить список всех ресторанов."""
    try:
        async with async_session() as session:
            query = select(Restaurants)
            result = await session.execute(query)
            restaurants = result.scalars().all()
            print(f"Retrieved {len(restaurants)} restaurants.")
            return restaurants
    except SQLAlchemyError as e:
        print(f"Error retrieving restaurants: {e}")
        await session.rollback()  # Откатить транзакцию при ошибке
        print("Transaction rolled back due to error.")

# Функция для проверки учетных данных администратора
async def verify_admin_credentials(email, password):
    """Проверка учетных данных администратора."""
    try:
        async with async_session() as session:
            query = select(Administrators).where(Administrators.email == email)
            result = await session.execute(query)
            admin = result.scalar_one_or_none()

            if admin and admin.password_hash == password:
                print(f"Admin {email} verified successfully.")
                return admin
            else:
                print(f"Admin {email} not found or password mismatch.")
    except SQLAlchemyError as e:
        print(f"Error verifying admin credentials for {email}: {e}")
        await session.rollback()  # Откатить транзакцию при ошибке
        print("Transaction rolled back due to error.")

    return None




# async def get_reservations_by_period(restaurant_id, period):
#     """Получить бронирования для определенного ресторана с номерами столиков."""
#     try:
#         print(f"Получение бронирований для ресторана {restaurant_id} за период {period}.")
#
#         async with async_session() as session:
#             if period == 'today':
#                 print("Запрос на бронирования за сегодня.")
#                 query = (
#                     select(Reservations, Tables)
#                     .join(Tables, Reservations.table_id == Tables.table_id)
#                     .where(
#                         Tables.restaurant_id == restaurant_id,
#                         func.date(Reservations.reservation_date_time) == func.current_date()
#                     )
#                 )
#             elif period == 'week':
#                 print("Запрос на бронирования за неделю.")
#                 query = (
#                     select(Reservations, Tables)
#                     .join(Tables, Reservations.table_id == Tables.table_id)
#                     .where(
#                         Tables.restaurant_id == restaurant_id,
#                         func.week( Reservations.reservation_date_time) == func.week(func.current_date())
#                     )
#                 )
#             elif period == 'month':
#                 print("Запрос на бронирования за месяц.")
#                 query = (
#                     select(Reservations, Tables)
#                     .join(Tables, Reservations.table_id == Tables.table_id)
#                     .where(
#                         Tables.restaurant_id == restaurant_id,
#                         func.year(Reservations.reservation_date_time) == func.year(func.current_date()),
#                         func.month(Reservations.reservation_date_time) == func.month(func.current_date())
#                     )
#                 )
#             else:
#                 raise ValueError(f"Неизвестный период: {period}")
#
#             # Выполнение запроса
#             print(f"Выполнение запроса для ресторана {restaurant_id} за период {period}.")
#             result = await session.execute(query)
#
#             # Преобразование строк результата в список словарей
#             reservations = []
#             for reservation, table in result.fetchall():
#                 reservations.append({
#                     "reservation_id": reservation.reservation_id,
#                     "reservation_date_time": reservation.reservation_date_time,
#                     "reservation_name": reservation.reservation_name,
#                     "guest_count": reservation.guest_count,
#                     "reservation_hours": reservation.reservation_hours,
#                     "reservation_status": reservation.reservation_status,
#                     "table_number": table.table_number  # Номер столика
#                 })
#
#             print(f"Получено {len(reservations)} бронирований для ресторана {restaurant_id}.")
#             return reservations
#
#     except SQLAlchemyError as e:
#         print(f"Ошибка при получении бронирований для ресторана {restaurant_id}: {e}")
#         await session.rollback()  # Откатить транзакцию при ошибке
#         print("Транзакция откатана из-за ошибки.")
#         return []
#     except ValueError as e:
#         print(f"Ошибка: {e}")
#         return []


from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError


async def get_reservations_by_period(restaurant_id, period):
    """Получить бронирования для определенного ресторана с номерами столиков и предзаказами, включая информацию о меню."""
    try:
        print(f"Получение бронирований для ресторана {restaurant_id} за период {period}.")

        # Подключение к сессии
        async with async_session() as session:
            if period == 'today':
                print("Запрос на бронирования за сегодня.")
                query = (
                    select(
                        Reservations.reservation_id,
                        Reservations.reservation_date_time,
                        Reservations.reservation_name,
                        Reservations.guest_count,
                        Reservations.reservation_status,
                        Reservations.reservation_hours,
                        Tables.table_number,
                        func.group_concat(
                            func.concat(Menu.name_dish, ' (x', Preorder.quantity, ')'), ';\n '
                        ).label("preorder_details")
                    )
                    .join(Preorder, Reservations.reservation_id == Preorder.reservation_id, isouter=True)
                    .join(Menu, Preorder.menu_id == Menu.menu_id, isouter=True)
                    .join(Tables, Reservations.table_id == Tables.table_id)
                    .where(
                        Tables.restaurant_id == restaurant_id,
                        func.date(Reservations.reservation_date_time) == func.current_date()
                    )
                    .group_by(
                        Reservations.reservation_id,
                        Reservations.reservation_date_time,
                        Reservations.reservation_name,
                        Reservations.guest_count,
                        Reservations.reservation_status,
                        Reservations.reservation_hours,
                        Tables.table_number
                    )
                )
            elif period == 'week':
                print("Запрос на бронирования за неделю.")
                query = (
                    select(
                        Reservations.reservation_id,
                        Reservations.reservation_date_time,
                        Reservations.reservation_name,
                        Reservations.guest_count,
                        Reservations.reservation_status,
                        Reservations.reservation_hours,
                        Tables.table_number,
                        func.group_concat(
                            func.concat(Menu.name_dish, ' (x', Preorder.quantity, ')'), ';\n '
                        ).label("preorder_details")
                    )
                    .join(Preorder, Reservations.reservation_id == Preorder.reservation_id, isouter=True)
                    .join(Menu, Preorder.menu_id == Menu.menu_id, isouter=True)
                    .join(Tables, Reservations.table_id == Tables.table_id)
                    .where(
                        Tables.restaurant_id == restaurant_id,
                        func.week(Reservations.reservation_date_time) == func.week(func.current_date())
                    )
                    .group_by(
                        Reservations.reservation_id,
                        Reservations.reservation_date_time,
                        Reservations.reservation_name,
                        Reservations.guest_count,
                        Reservations.reservation_status,
                        Reservations.reservation_hours,
                        Tables.table_number
                    )
                )
            elif period == 'month':
                print("Запрос на бронирования за месяц.")
                query = (
                    select(
                        Reservations.reservation_id,
                        Reservations.reservation_date_time,
                        Reservations.reservation_name,
                        Reservations.guest_count,
                        Reservations.reservation_status,
                        Reservations.reservation_hours,
                        Tables.table_number,
                        func.group_concat(
                            func.concat(Menu.name_dish, ' (x', Preorder.quantity, ')'), '; \n'
                        ).label("preorder_details")
                    )
                    .join(Preorder, Reservations.reservation_id == Preorder.reservation_id, isouter=True)
                    .join(Menu, Preorder.menu_id == Menu.menu_id, isouter=True)
                    .join(Tables, Reservations.table_id == Tables.table_id)
                    .where(
                        Tables.restaurant_id == restaurant_id,
                        func.year(Reservations.reservation_date_time) == func.year(func.current_date()),
                        func.month(Reservations.reservation_date_time) == func.month(func.current_date())
                    )
                    .group_by(
                        Reservations.reservation_id,
                        Reservations.reservation_date_time,
                        Reservations.reservation_name,
                        Reservations.guest_count,
                        Reservations.reservation_status,
                        Reservations.reservation_hours,
                        Tables.table_number
                    )
                )
            else:
                raise ValueError(f"Неизвестный период: {period}")

            # Выполнение запроса
            print(f"Выполнение запроса для ресторана {restaurant_id} за период {period}.")
            result = await session.execute(query)

            # Преобразование строк результата в список словарей
            reservations = [
                {
                    "reservation_id": r.reservation_id,
                    "reservation_date_time": r.reservation_date_time,
                    "reservation_name": r.reservation_name,
                    "guest_count": r.guest_count,
                    "reservation_status": r.reservation_status,
                    "reservation_hours": r.reservation_hours,
                    "table_number": r.table_number,
                    "preorder_details": r.preorder_details or "-",
                }
                for r in result
            ]

            print(f"Получено {len(reservations)} бронирований для ресторана {restaurant_id} за период {period}.")
            return reservations

    except Exception as e:
        print(f"Ошибка при получении бронирований для ресторана {restaurant_id}: {e}")
        return []




# Функция для получения бронирования по ID
async def get_reservation_by_id(reservation_id):
    async with async_session() as session:
        result = await session.execute(
            select(Reservations).filter(Reservations.id == reservation_id)
        )
        return result.scalars().first()

# Функция для обновления бронирования
async def update_reservation_by_id(reservation):
    async with async_session() as session:
        session.add(reservation)
        await session.commit()