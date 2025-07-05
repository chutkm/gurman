import aiohttp
from bs4 import BeautifulSoup
import requests
async def fetch_restoclub_promotions():
    url = "https://www.restoclub.ru/msk/news/actions"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }


    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return []

            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    promotions = []

    for block in soup.select(".news-item")[:5]:
        title_tag = block.select_one(".news-item__title")
        text_tag = block.select_one(".news-item__text")
        rest_tag = block.select_one(".news-item__header")

        title = title_tag.get_text(strip=True) if title_tag else "Без названия"
        description = text_tag.get_text(strip=True) if text_tag else "Без описания"
        import re
        # Название ресторана из title-атрибута
        if rest_tag and rest_tag.has_attr("title"):
            restaurant_full = rest_tag["title"]  # Например: "Ресторан «One Love»"
            match = re.search(r'Ресторан\s+«(.+?)»', restaurant_full)
            restaurant = match.group(1) if match else restaurant_full.replace("Ресторан ", "").strip()
        else:
            restaurant = "Не указано"

        promotions.append({
            "restaurant": restaurant,
            "title": title,
            "description": description
        })

    return promotions


import aiohttp
from bs4 import BeautifulSoup, NavigableString

#
# def extract_restaurant_name(a_tag):
#     inner_div = a_tag.find('div')
#     if not inner_div:
#         return a_tag.get_text(strip=True)
#
#     # Удаляем все элементы с классом .tooltip-verification
#     for tooltip in inner_div.select('.tooltip-verification'):
#         tooltip.decompose()
#
#     # Рекурсивно собираем текст из всех дочерних узлов, кроме тегов
#     def recursive_text(node):
#         result = []
#         for child in node.children:
#             if child.name is None and isinstance(child, NavigableString):
#                 text = child.strip()
#                 if text:
#                     result.append(text)
#             elif child.name == 'span':
#                 result.extend(recursive_text(child))
#             elif child.name:
#                 result.extend(recursive_text(child))
#         return result
#
#     text_parts = recursive_text(inner_div)
#     name = ' '.join(text_parts).strip()
#     return name

from bs4 import NavigableString

def extract_restaurant_name(a_tag):
    name_parts = []
    for child in a_tag.descendants:
        # Берём только текстовые узлы
        if isinstance(child, NavigableString):
            # Проверяем, не находится ли текст внутри нежелательного тега
            parent = child.parent
            if parent and parent.name not in ['div', 'svg', 'script', 'style']:
                if not any(cls in (parent.get('class') or []) for cls in ['tooltip-verification', 'tooltiptext']):
                    text = child.strip()
                    if text:
                        name_parts.append(text)
    return ' '.join(name_parts)




async def parse_category_page_async(url: str) -> list:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return []

            html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')

    # 1) Получаем названия и ссылки из блока .search-place-title__name
    name_blocks = soup.select('.search-place-title__name a.search-place-title__link-name')
    names_map = {}
    for block in name_blocks:
        href = block.get('data-href') or block.get('href')
        if not href:
            continue
        full_link = f"https://www.restoclub.ru{href}"
        name = extract_restaurant_name(block)
        names_map[full_link] = name

    # 2) Получаем дополнительные данные из a.search-place-rubric__item
    results = []
    rubric_links = soup.select('a.search-place-rubric__item')

    for link in rubric_links:
        href = link.get('href')
        full_link = f"https://www.restoclub.ru{href}" if href else None

        rubric = link.select_one('span.search-place-rubric__mark')
        description = link.select_one('span.search-place-rubric__t')

        title = rubric.get_text(strip=True) if rubric else "Без рубрики"
        desc = description.get_text(strip=True) if description else ""

        # Найдём название по ссылке, если есть
        name = names_map.get(full_link, "Без названия")

        results.append({
            "name": name,
            "title": title,
            "description": desc,
            "link": full_link or "Ссылка недоступна"
        })

    return results




import aiohttp
from bs4 import BeautifulSoup

async def parse_popular_kitchen_page_async(url: str) -> list:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    print(f"Ошибка HTTP {response.status} при загрузке {url}")
                    return []
                html = await response.text()
        except Exception as e:
            print(f"Ошибка соединения: {e}")
            return []

    soup = BeautifulSoup(html, 'html.parser')
    restaurant_cards = soup.select('div.search-place-card')

    results = []
    for card in restaurant_cards:
        # Название ресторана (обновлённый селектор)
        name_tag = card.select_one('div.search-place-title__name a.search-place-title__link-name')
        if name_tag:
            # Извлекаем только текст внутри <a>, без вложенных <span>
            name = ''.join(name_tag.find_all(string=True, recursive=False)).strip()
        else:
            name = "Без названия"

        # Ссылка
        relative_link = name_tag.get('data-href') or name_tag.get('href') if name_tag else None
        full_link = f"https://www.restoclub.ru{relative_link}" if relative_link else "Ссылка недоступна"

        # Местоположение (первое слово)
        location_tag = card.select_one('li.search-place-card__info-item span')
        location_full = location_tag.get_text(strip=True) if location_tag else "Не указано"
        location = location_full.split(',')[0].split()[0]  # берём первое слово до запятой или пробела

        # Средний чек
        price_tag = card.select_one('li.search-place-card__info-item._bill')
        price = price_tag.get_text(strip=True) if price_tag else "Не указана"

        # Кухни
        cuisine_tags = card.select('li.search-place-card__info-item._cuisine span.cuisine')
        cuisines = [tag.get_text(strip=True) for tag in cuisine_tags] if cuisine_tags else ["Не указано"]

        # Описание
        description_tag = card.select_one('span.search-place-rubric__t._long')
        description = description_tag.get_text(strip=True) if description_tag else "Описание не найдено"

        results.append({
            "name": name,
            "location": location,
            "price": price,
            "cuisines": cuisines,
            "link": full_link,
            "description": description
        })

    return results

import aiohttp
from bs4 import BeautifulSoup



async def parse_restoranoff_news_async(url: str) -> list:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    print(f"[Ошибка] HTTP {response.status} при загрузке {url}")
                    return []
                html = await response.text()
        except Exception as e:
            print(f"[Ошибка соединения] {e}")
            return []

    soup = BeautifulSoup(html, 'html.parser')
    print(soup.prettify())
    news_items = soup.select('div.news_item')  # Общий селектор для всех новостей

    results = []
    for item in news_items:
        # Заголовок новости
        title_tag = item.select_one('.text_block a h2')
        title = title_tag.get_text(strip=True) if title_tag else "Без названия"

        # Описание новости
        description_tag = item.select_one('.description a')
        description = description_tag.get_text(strip=True) if description_tag else "Описание отсутствует"

        # Ссылка на новость
        link_tag = item.select_one('.text_block a')
        relative_link = link_tag.get('href') if link_tag else None
        full_link = f"https://restoranoff.ru {relative_link}" if relative_link else "Ссылка недоступна"

        results.append({
            "title": title,
            "description": description,
            "link": full_link
        })

    print(f"[Информация] Найдено {len(results)} новостей")
    return results