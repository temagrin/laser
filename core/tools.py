import math
import numpy as np
from matplotlib import cm
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon


def get_path_length(contour_points):
    length = 0.0
    prev_x, prev_y = contour_points[0]
    first_x, first_y = contour_points[0]
    for x_nm, y_nm in contour_points[1:]:
        x = x_nm
        y = y_nm
        length += math.hypot(x - prev_x, y - prev_y)
        prev_x, prev_y = x, y

    length += math.hypot(prev_x - first_x, prev_y - first_y)
    return length


def euclidean(a, b):
    """Вычисляет евклидово расстояние между точками a и b"""
    a = np.array(a)
    b = np.array(b)
    return np.linalg.norm(a - b)


def rotate_path_to_start_at(path, point_index):
    """
    Поворачивает путь так, чтобы точка с индексом point_index стала первой.
    Предполагается, что путь замкнут (первая точка = последняя).
    После поворота путь остается замкнутым.
    """
    n = len(path) - 1
    rotated = path[point_index:point_index + n] + path[:point_index] + [path[point_index]]
    return rotated


def sort_paths_minimize_transitions(paths):
    """
    Сортирует пути так, чтобы минимизировать перемещения между концом одного контура и любой точкой следующего,
    поворачивая выбранный путь так, чтобы выбранная ближайшая точка стала началом.

    paths — список путей, каждый путь — список (x,y), замкнут (первая точка = последняя)
    Возвращает — список отсортированных и ориентированных путей.
    """
    n = len(paths)
    used = [False] * n
    sorted_paths = []

    # Начинаем с первого пути без изменений
    curr_idx = 0
    used[curr_idx] = True
    sorted_paths.append(paths[curr_idx])

    for _ in range(n - 1):
        curr_path = sorted_paths[-1]
        curr_end = curr_path[-1]  # конец текущего пути (у замкнутого он равен началу)

        min_dist = None
        next_idx = None
        next_rotated_path = None

        for j in range(n):
            if not used[j]:
                candidate_path = paths[j]
                # Ищем точку в candidate_path, которая ближе всего к curr_end
                distances = [euclidean(curr_end, pt) for pt in candidate_path[:-1]]  # не учитываем последний дубль
                closest_point_idx = np.argmin(distances)
                dist = distances[closest_point_idx]

                if (min_dist is None) or (dist < min_dist):
                    min_dist = dist
                    next_idx = j
                    # Поворачиваем путь, чтобы ближайшая точка стала началом
                    next_rotated_path = rotate_path_to_start_at(candidate_path, closest_point_idx)

        used[next_idx] = True
        sorted_paths.append(next_rotated_path)

    return sorted_paths


def sort_paths(paths):
    """Простая сортировка по концам-началам"""
    n = len(paths)
    used = [False] * n
    sorted_indices = []

    curr_idx = 0
    sorted_indices.append(curr_idx)
    used[curr_idx] = True

    for _ in range(n - 1):
        last_pt = paths[curr_idx][0]
        min_dist = None
        next_idx = None
        for j in range(n):
            if not used[j]:
                dist = euclidean(last_pt, paths[j])
                if (min_dist is None) or (dist < min_dist):
                    min_dist = dist
                    next_idx = j
        sorted_indices.append(next_idx)
        used[next_idx] = True
        curr_idx = next_idx

    sorted_paths = [paths[i] for i in sorted_indices]
    return sorted_paths


def plot_inset_paths(paths):
    fig, ax = plt.subplots()
    ax.set_aspect('equal', adjustable='box')
    all_x, all_y = [], []
    for figure_idx, figure in enumerate(paths):
        colors = cm.get_cmap('viridis', len(figure))
        for level_idx, contour in enumerate(figure):
            color = colors(level_idx)  # Цвет для этого уровня
            if len(contour) < 3:
                continue  # пропускаем вырожденные
            poly_patch = MplPolygon(contour, closed=True,
                                    facecolor='none',
                                    edgecolor=color,
                                    linewidth=1)
            ax.add_patch(poly_patch)

            xs, ys = zip(*contour)
            all_x.extend(xs)
            all_y.extend(ys)

    if all_x and all_y:
        padding_x = (max(all_x) - min(all_x)) * 0.05 or 1
        padding_y = (max(all_y) - min(all_y)) * 0.05 or 1
        ax.set_xlim(min(all_x) - padding_x, max(all_x) + padding_x)
        ax.set_ylim(min(all_y) - padding_y, max(all_y) + padding_y)

    ax.grid(True, linestyle='--', alpha=0.5)
    plt.title("Paths Preview")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.show()

