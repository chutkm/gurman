from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    DECIMAL,
    Text,
    Enum,
    Boolean,
    BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import aiomysql
from sqlalchemy import Boolean
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

# Получаем URL базы данных
DATABASE_URL = os.getenv('DATABASE_URL')
# from config import DATABASE_URL
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

import asyncio

# Определение базового класса для асинхронных операций
class Base(DeclarativeBase):
    pass

#--------------------
# Таблица клиентов
class Clients(Base):
    __tablename__ = 'clients'

    client_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id:Mapped[int] = mapped_column(Integer,nullable= True)
    tg_user_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(15), nullable= True)
    registration_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    reviews: Mapped[list['Reviews']] = relationship('Reviews', back_populates='client')
    reservations: Mapped[list['Reservations']] = relationship('Reservations', back_populates='client')



class Reviews(Base):
    __tablename__ = 'reviews'

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    review_date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.reservation_id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey('clients.client_id'), nullable=False)
    # Убрали client_id и relationship с Clients
    # Оставили только связь с reservations
    reservation: Mapped["Reservations"] = relationship("Reservations", back_populates="reviews")

    client: Mapped["Clients"] = relationship("Clients", back_populates="reviews")

# Таблица меню
class Menu(Base):
    __tablename__ = 'menu'

    menu_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_dish: Mapped[str] = mapped_column(String(255), nullable=False)
    type_dish: Mapped[str] = mapped_column(String(100), nullable=False)
    portion_size: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    unit_of_measurement: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    preorders: Mapped[list['Preorder']] = relationship('Preorder', back_populates='menu')


# Таблица предзаказов
class Preorder(Base):
    __tablename__ = 'preorder'

    preorder_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reservation_id: Mapped[int] = mapped_column(ForeignKey('reservations.reservation_id'), nullable=False)
    menu_id: Mapped[int] = mapped_column(ForeignKey('menu.menu_id'), nullable=False)

    reservation: Mapped['Reservations'] = relationship('Reservations', back_populates='preorders')
    menu: Mapped['Menu'] = relationship('Menu', back_populates='preorders')


# Таблица ресторанов
class Restaurants(Base):
    __tablename__ = 'restaurants'

    restaurant_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(15), nullable=False)

    tables: Mapped[list['Tables']] = relationship('Tables', back_populates='restaurant')


# Таблица столиков
class Tables(Base):
    __tablename__ = 'tables'

    table_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    place_type: Mapped[str] = mapped_column(Enum('зал', 'веранда', name='place_type_enum'), nullable=False)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.restaurant_id'), nullable=False)

    restaurant: Mapped['Restaurants'] = relationship('Restaurants', back_populates='tables')
    reservations: Mapped[list['Reservations']] = relationship('Reservations', back_populates='table')


# Таблица бронирований

# Таблица акций
class Promotions(Base):
    __tablename__ = 'promotions'

    promotion_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promotion_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    discount_percentage: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usage_conditions: Mapped[str] = mapped_column(Text, nullable=False)


# Таблица администраторов
class Administrators(Base):
    __tablename__ = 'administrators'

    admin_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

class Reservations(Base):
    __tablename__ = 'reservations'

    reservation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reservation_date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reservation_name: Mapped[str] = mapped_column(String(100), nullable=False)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reservation_status: Mapped[str] = mapped_column(Enum('подтверждено','отменено', name='status_enum'), nullable=False)
    reservation_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey('clients.client_id'), nullable=False)
    table_id: Mapped[int] = mapped_column(ForeignKey('tables.table_id'), nullable=False)

    client: Mapped['Clients'] = relationship('Clients', back_populates='reservations')
    table: Mapped['Tables'] = relationship('Tables', back_populates='reservations')
    preorders: Mapped[list['Preorder']] = relationship('Preorder', back_populates='reservation')
    reviews: Mapped[list["Reviews"]] = relationship("Reviews", back_populates="reservation")

# Таблица типов мероприятий
class EventTypes(Base):
    __tablename__ = 'event_types'

    event_type_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)


# Таблица рекомендаций заведений под мероприятия
class EventVenueRecommendations(Base):
    __tablename__ = 'event_venue_recommendations'

    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.restaurant_id'), nullable=False)
    event_type_id: Mapped[int] = mapped_column(ForeignKey('event_types.event_type_id'), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Связи
    restaurant: Mapped['Restaurants'] = relationship('Restaurants')
    event_type: Mapped['EventTypes'] = relationship('EventTypes')


# Таблица заявок на мероприятия
class EventApplications(Base):
    __tablename__ = 'event_applications'

    application_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('clients.client_id'), nullable=False)
    event_type_id: Mapped[int] = mapped_column(ForeignKey('event_types.event_type_id'), nullable=False)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.restaurant_id'), nullable=True)
    requested_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связи
    client: Mapped['Clients'] = relationship('Clients')
    event_type: Mapped['EventTypes'] = relationship('EventTypes')
    restaurant: Mapped['Restaurants'] = relationship('Restaurants')

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
