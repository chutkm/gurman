import asyncio
from app.database.models import async_session, Reservations
from sqlalchemy import select, func
import matplotlib.pyplot as plt


async def plot_reservations_by_hour():
    async with async_session() as session:
        query = (
            select(
                func.extract('hour', Reservations.reservation_date_time).label('hour'),
                func.count(Reservations.reservation_id).label('count')
            )
            .group_by('hour')
            .order_by('hour')
        )
        result = await session.execute(query)
        data = result.fetchall()

        if not data:
            print("Нет данных для построения графика.")
            return

        hours, counts = zip(*data)

        plt.figure(figsize=(10, 6))
        plt.bar(hours, counts, color='lightblue', edgecolor='black')
        plt.xticks(range(8, 24))
        plt.xlabel('Часы дня', fontsize=12)
        plt.ylabel('Количество бронирований', fontsize=12)
        plt.title('Зависимость бронирований от времени', fontsize=14)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    asyncio.run(plot_reservations_by_hour())

# python plot_graph.py
