import matplotlib.pyplot as plt
import networkx as nx

# Сущности
entities = [
    "clients", "reservations", "reviews", "preorder",
    "menu", "tables", "restaurants", "promotions", "administrators"
]

# Связи с текстовыми подписями и отношениями
edge_labels = {
    ("clients", "reviews"): "оставляет отзыв (1:M)",
    ("clients", "reservations"): "делает бронирование (1:M)",
    ("reservations", "preorder"): "имеет предзаказ (1:1)",
    ("preorder", "menu"): "заказывает блюдо (M:M)",
    ("reservations", "tables"): "резервирует стол (1:1)",
    ("tables", "restaurants"): "находится в (M:1)"
}

# Создание графа
G = nx.DiGraph()
G.add_nodes_from(entities)
G.add_edges_from(edge_labels.keys())

# Расположение узлов с увеличением расстояния между ними
pos = nx.spring_layout(G, seed=42, k=1)  # Параметр k отвечает за расстояние между узлами

# Настройка фигуры
plt.figure(figsize=(16, 12))

# Отрисовка графа
nx.draw(
    G, pos, with_labels=True, node_size=3000,
    node_color="white", font_size=12, font_weight="bold",
    edge_color="black", arrows=True, arrowsize=20
)

# Подписи узлов в прямоугольниках
nx.draw_networkx_labels(
    G, pos, font_color='black',
    bbox=dict(boxstyle="round,pad=0.3", edgecolor='black', facecolor='white')
)

# Подписи рёбер с указанием типов связей
nx.draw_networkx_edge_labels(
    G, pos, edge_labels=edge_labels, font_color='black', label_pos=0.5
)

plt.title("ER-диаграмма ", fontsize=16)
plt.axis('off')
plt.show()
