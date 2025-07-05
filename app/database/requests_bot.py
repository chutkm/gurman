from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from .models import async_session, Clients, Reservations, Tables, Restaurants, Menu, Preorder, Promotions, Reviews
from sqlalchemy import select, update, delete, func, or_, and_, Integer, insert
from sqlalchemy import and_, or_, func

# Функция для добавления нового пользователя
async def check_number(tg_id: int) -> bool:
    """
    Проверяет, есть ли номер телефона у пользователя.
    Возвращает True, если номера нет, иначе False.
    """
    async with async_session() as session:
        result = await session.scalar(
            select(Clients.phone_number).where(Clients.tg_id == tg_id)
        )
        return result is None


async def all_rest_view():
    async with async_session() as session:
        result = await session.execute(select(Restaurants.restaurant_id, Restaurants.restaurant_name))

        # Проверяем тип результата
        if isinstance(result, list):  # Если результат — список
            restaurants = result
        else:
            restaurants = result.fetchall()  # Если результат — объект запроса

    return restaurants if restaurants else None

#-------------------------PREORDER
async def create_preorder(reservation_id: int, cart: dict):
    """
    Добавляет предзаказ в базу данных на основе `reservation_id` и списка блюд (cart).

    :param reservation_id: ID бронирования, к которому относится предзаказ.
    :param cart: Словарь с информацией о предзаказе, где ключ — ID блюда, а значение — количество.
    """
    async with async_session() as session:
        try:
            # Создаем записи для каждого блюда в предзаказе
            for menu_id, item in cart.items():
                new_preorder = Preorder(
                    preorder_id=None,  # ID создается автоматически, если используется автоинкремент
                    reservation_id=reservation_id,
                    menu_id=menu_id,
                    quantity=item["quantity"]
                )
                session.add(new_preorder)

            # Сохраняем изменения в базе данных
            await session.commit()

        except Exception as e:
            await session.rollback()
            raise e


async def all_menu_view():
    async with async_session() as session:
        menu = await session.execute(select(Menu))

        # Проверяем тип результата
        if isinstance(menu, list):  # Если результат — список
            restaurants = menu
        else:
            restaurants = menu.fetchall()  # Если результат — объект запроса

    return restaurants if restaurants else None

# Получение списка блюд из категории
async def get_menu_by_category(category):
    """
    Получает список блюд из базы данных на основе категории.
    """
    async with async_session() as session:
        result = await session.execute(
            select(Menu).where(Menu.type_dish == category)
        )
        menu_items = result.scalars().all()  # Преобразуем результат в список объектов Menu
    return menu_items if menu_items else None

# Получение списка уникальных категорий
async def get_categories():
    """
    Получает список уникальных категорий блюд из базы данных.
    """
    async with async_session() as session:
        result = await session.execute(select(Menu.type_dish).distinct())
        categories = result.scalars().all()
    return categories


#-----------------------------------------------PREORDER

async def set_user(tg_id: int, tg_user_name: str = None):
    """
    Добавляет пользователя в базу данных с увеличением client_id на 1,
    если его еще нет.
    """
    if not tg_user_name:  # Если username отсутствует
        tg_user_name = "anonymous"  # Значение по умолчанию

    async with async_session() as session:  # Используйте асинхронную сессию
        try:
            # Проверяем, существует ли пользователь
            user = await session.scalar(select(Clients).where(Clients.tg_id == tg_id))
            if not user:
                # Получаем максимальный client_id из таблицы
                max_client_id = await session.scalar(select(func.max(Clients.client_id)))
                if max_client_id is None:
                    max_client_id = 0  # Если таблица пустая

                # Если пользователя нет, создаем нового
                new_user = Clients(
                    client_id=max_client_id + 1,
                    tg_id=tg_id,
                    tg_user_name=tg_user_name,
                    registration_date=datetime.utcnow()
                )
                session.add(new_user)
                await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при добавлении пользователя в БД: {e}")
            raise


async def create_reservation(reservation_time,user_tg_id, reservation_name,number_of_guests, hours,table_choice):
    async with async_session() as session:
        try:
            # Проверка, существует ли пользователь
            user = await session.scalar(select(Clients).where(Clients.tg_id == user_tg_id))
            if not user:
                raise ValueError("User does not exist")

            client_id = await session.scalar(select(Clients.client_id).where(Clients.tg_id == user_tg_id))
            reservation_status  = "подтверждено"

            # Получаем максимальный client_id из таблицы
            # max_reservation_id = await session.scalar(select(func.max(Reservations.reservation_id)))
            # # Если таблица пуста, max_reservation_id будет None, поэтому используем 0 и добавляем 1
            # reservation_id = (max_reservation_id or 0) + 1


            # Создаем бронирование
            new_reservation = Reservations(
                reservation_id=None,
                reservation_date_time=reservation_time,
                reservation_name=reservation_name,
                guest_count=number_of_guests,
                reservation_status=reservation_status,
                reservation_hours = hours,
                client_id = client_id,
                table_id = table_choice
            )
            session.add(new_reservation)

            # Сохраняем изменения в базе данных
            await session.commit()

            # Получаем созданный reservation_id
            reservation_id = new_reservation.reservation_id

            # Возвращаем reservation_id
            return reservation_id

        except Exception as e:
            await session.rollback()
            raise e





async def find_suitable_table(restaurant_id, number_of_guests, reservation_time, reservation_hours):
    """
    Находит подходящие столики, доступные в указанное время.
    """
    async with async_session() as session:
        try:
            # Время окончания бронирования
            reservation_end_time = reservation_time + timedelta(hours=reservation_hours)

            # Запрос для поиска столиков, подходящих по количеству мест и ресторану
            available_table_query = (
                select(Tables)
                .where(
                    and_(
                        Tables.seats == number_of_guests,
                        Tables.restaurant_id == restaurant_id
                    )
                )
                .order_by(Tables.seats.asc())
            )
            result = await session.execute(available_table_query)
            tables = result.scalars().all()

            suitable_tables = []
            for table in tables:
                # Проверка на пересечения с существующими бронированиями
                reservation_query = (
                    select(Reservations)
                    .where(
                        Reservations.table_id == table.table_id,
                        Reservations.reservation_status == 'подтверждено',
                        or_(
                            and_(
                                Reservations.reservation_date_time <= reservation_time,
                                Reservations.reservation_date_time + func.cast(Reservations.reservation_hours, Integer) * func.interval(1, 'hour') > reservation_time
                            ),
                            and_(
                                Reservations.reservation_date_time < reservation_end_time,
                                Reservations.reservation_date_time + func.cast(Reservations.reservation_hours, Integer) * func.interval(1, 'hour') >= reservation_end_time
                            ),
                            and_(
                                Reservations.reservation_date_time >= reservation_time,
                                Reservations.reservation_date_time + func.cast(Reservations.reservation_hours, Integer) * func.interval(1, 'hour') <= reservation_end_time
                            )
                        )
                    )
                )
                reservation_result = await session.execute(reservation_query)
                existing_reservation = reservation_result.scalars().first()

                if not existing_reservation:
                    suitable_tables.append(table)

            return suitable_tables

        except Exception as e:
            raise Exception(f"Ошибка при поиске столика: {e}")

async def find_promotion():
    async with async_session() as session:
        # Формируем запрос для получения активных промо-акций
        promo = await session.execute(
            select(Promotions.description, Promotions.discount_percentage, Promotions.start_date, Promotions.end_date)
            .where(func.current_date().between(Promotions.start_date, Promotions.end_date))
        )
        # Извлекаем результат
        promotions = promo.fetchall()

        # Возвращаем акции
        return promotions

def get_promotions():
    """Функция для получения данных о промо-акциях."""
    promotions = [
        {'description': 'Скидка 20% на все товары', 'validity_period': '01.01.2024 - 31.01.2024', 'terms': 'Для всех пользователей.'},
        {'description': 'Подарок за покупку от 3000₽', 'validity_period': '01.12.2023 - 31.12.2023', 'terms': 'При заказе на сайте.'},
    ]
    return promotions










async def save_review_to_db(client_id: int, review_text: str, rating: int, reservation_id: int):
    """
    Сохраняет отзыв в базе данных.
    """
    try:
        async with async_session() as session:
            async with session.begin():
                await session.execute(
                    insert(Reviews).values(
                        client_id=client_id,
                        review_text=review_text,
                        rating=rating,
                        review_date_time=datetime.now(),
                        reservation_id=reservation_id
                    )
                )
            await session.commit()
        return True
    except Exception as e:
        print(f"Ошибка при сохранении отзыва: {e}")
        return False


from app.database.models import (
    EventVenueRecommendations,
    Restaurants,
    EventTypes,
    Base,
    async_session
)
from sqlalchemy import select, join, func

async def get_recommended_restaurants(event_type_name: str) -> list[dict]:
    async with async_session() as session:
        stmt = (
            select(
                Restaurants.restaurant_id,
                Restaurants.restaurant_name,
                Restaurants.address,
                EventTypes.name.label('event_type'),
                EventVenueRecommendations.description.label('recommendation_description')
            )
            .select_from(join(EventVenueRecommendations, Restaurants))
            .join(EventTypes)
            .where(EventTypes.name == event_type_name)
        )
        result = await session.execute(stmt)
        return [
            {
                'restaurant_id': row.restaurant_id,
                'restaurant_name': row.restaurant_name,
                'address': row.address,
                'event_type': row.event_type,
                'recommendation_description': row.recommendation_description
            }
            for row in result.all()
        ]
