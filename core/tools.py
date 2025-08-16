from math import sqrt

import pyclipper
from shapely import LinearRing
from shapely.affinity import scale, translate
from shapely.geometry import MultiPolygon, Polygon
from matplotlib import cm
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon


def offset_geometry(poly_set, origin_x, origin_y):
    return translate(poly_set, xoff=-origin_x, yoff=-origin_y)


def mirror_geometry(geom, axis='x', around_center=True):
    """
    Зеркально отражает Polygon или MultiPolygon по указанной оси без смещения.

    :param geom: объект Polygon или MultiPolygon
    :param axis: 'x' — зеркалить по горизонтальной оси, 'y' — по вертикальной
    :param around_center: если True — отражение относительно центра bounds объекта
    :return: отражённый объект
    """
    if around_center:
        minx, miny, maxx, maxy = geom.bounds
        cx = (minx + maxx) / 2
        cy = (miny + maxy) / 2
        origin = (cx, cy)
    else:
        origin = (0, 0)

    if axis == 'x':
        return scale(geom, xfact=1, yfact=-1, origin=origin)
    elif axis == 'y':
        return scale(geom, xfact=-1, yfact=1, origin=origin)
    else:
        raise ValueError("axis должен быть 'x' или 'y'")


def polygon_to_coords(polygon):
    if isinstance(polygon, Polygon):
        return list(polygon.exterior.coords)
    elif isinstance(polygon, MultiPolygon):
        return [list(p.exterior.coords) for p in polygon.geoms]
    else:
        return None


def render_preview(multipolygon):
    if multipolygon.is_empty:
        print("Пустая геометрия для отрисовки")
        return

    minx, miny, maxx, maxy = multipolygon.bounds
    fig, ax = plt.subplots()

    if isinstance(multipolygon, Polygon):
        polygons = [multipolygon]
    elif isinstance(multipolygon, MultiPolygon):
        polygons = list(multipolygon.geoms)
    else:
        print("Неподдерживаемый тип геометрии:", type(multipolygon))
        return

    for poly in polygons:
        # ===== внешний контур =====
        exterior_coords = list(poly.exterior.coords)
        ax.add_patch(MplPolygon(exterior_coords, closed=True,
                                facecolor='lightgray', edgecolor='black'))

        # ===== отверстия =====
        for interior in poly.interiors:
            interior_coords = list(interior.coords)
            ax.add_patch(MplPolygon(interior_coords, closed=True,
                                    facecolor='white', edgecolor='black'))

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect('equal', adjustable='box')

    plt.title("MultiPolygon preview")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(True)
    plt.show()


def shapely_to_pyclipper_paths(geom):
    """
    Преобразовать Shapely Polygon/MultiPolygon в список путей pyclipper.
    Каждый путь — список кортежей (x, y) с координатами int.
    """
    paths = []

    if isinstance(geom, Polygon):
        exterior = [(int(x), int(y)) for x, y in geom.exterior.coords]
        paths.append(exterior)
        for interior in geom.interiors:
            hole = [(int(x), int(y)) for x, y in interior.coords]
            paths.append(hole)
    elif isinstance(geom, MultiPolygon):
        for poly in geom.geoms:
            exterior = [(int(x), int(y)) for x, y in poly.exterior.coords]
            paths.append(exterior)
            for interior in poly.interiors:
                hole = [(int(x), int(y)) for x, y in interior.coords]
                paths.append(hole)
    return paths


def filter_short_paths_near_holes(paths, holes, length_thresh=30, dist_thresh=5):
    hole_polygons = [Polygon(hole) for hole in holes]
    filtered = []
    for path in paths:
        poly = Polygon(path)
        if not poly.is_valid or poly.is_empty:
            continue
        # Вычисляем длину контура (периметр)
        length = poly.length
        # Находим минимальное расстояние до отверстий
        distances = [poly.distance(hole) for hole in hole_polygons]
        min_dist = min(distances) if distances else float('inf')
        # Отбрасываем короткие и близкие к отверстиям
        if length < length_thresh and min_dist < dist_thresh:
            continue
        filtered.append(path)
    return filtered


def advanced_filter_paths(paths, holes, intersection_ratio_thresh=0.3):
    hole_polygons = [Polygon(hole) for hole in holes]  # оригинальные отверстия без буфера
    filtered = []

    for path in paths:
        poly = Polygon(path)
        if not poly.is_valid or poly.is_empty:
            continue

        # Проверяем для каждого отверстия
        remove_path = False
        for hole in hole_polygons:
            if poly.within(hole):
                # Полностью внутри отверстия — удаляем
                remove_path = True
                break
            elif poly.intersects(hole):
                inter_area = poly.intersection(hole).area
                ratio = inter_area / poly.area if poly.area > 0 else 0
                if ratio > intersection_ratio_thresh:
                    # Большая часть пути внутри отверстия — удаляем
                    remove_path = True
                    break

        if not remove_path:
            filtered.append(path)

    return filtered


def length_of_path(path):
    length = 0
    for i in range(1, len(path)):
        dx = path[i][0] - path[i-1][0]
        dy = path[i][1] - path[i-1][1]
        length += (dx*dx + dy*dy)**0.5
    return length


def filter_short_intersecting_paths(paths, length_thresh=None):
    """
    Фильтрует пересекающиеся контуры, удаляя из каждой пары пересекающихся самый короткий,
    если он короче порога length_thresh (если он задан).
    paths - список контуров (списки точек)
    length_thresh - порог длины для удаления коротких контуров в пересечении (None - без ограничения)
    """
    polygons = [Polygon(p) for p in paths if len(p) >= 3]
    lengths = [poly.length for poly in polygons]
    to_remove = set()

    for i in range(len(polygons)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(polygons)):
            if j in to_remove:
                continue

            # Используем Clipper для вычисления пересечения
            pc = pyclipper.Pyclipper()
            pc.AddPath(paths[i], pyclipper.PT_SUBJECT, True)
            pc.AddPath(paths[j], pyclipper.PT_CLIP, True)
            inter = pc.Execute(pyclipper.CT_INTERSECTION)

            if inter:  # Есть пересечение
                len_i = lengths[i]
                len_j = lengths[j]

                # Удаляем самый короткий из пары, если ниже threshold
                if len_i < len_j:
                    if length_thresh is None or len_i < length_thresh:
                        to_remove.add(i)
                else:
                    if length_thresh is None or len_j < length_thresh:
                        to_remove.add(j)

    filtered = [paths[i] for i in range(len(paths)) if i not in to_remove]
    return filtered


def generate_inset_paths_for_polygon(polygon: Polygon, step: float):
    def to_int_coords(coords):
        return [(int(x), int(y)) for x, y in coords]

    def ensure_path_validity(paths, outer=True):
        valid_paths = []
        for path in paths:
            if len(path) < 3:
                continue
            ring = LinearRing(path)
            if not ring.is_valid:
                continue
            is_ccw = ring.is_ccw
            if outer and not is_ccw:
                path = path[::-1]
            elif not outer and is_ccw:
                path = path[::-1]
            valid_paths.append(path)
        return valid_paths

    outer_path = to_int_coords(polygon.exterior.coords)
    inner_paths = [to_int_coords(hole.coords) for hole in polygon.interiors]

    outer_paths_valid = ensure_path_validity([outer_path], outer=True)
    if not outer_paths_valid:
        return []
    outer_path = outer_paths_valid[0]
    inner_paths = ensure_path_validity(inner_paths, outer=False)

    pco_outer = pyclipper.PyclipperOffset()
    pco_outer.AddPath(outer_path, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

    inset_paths = []
    i = 1

    while True:
        offset_distance = -step * i
        outer_offset = pco_outer.Execute(offset_distance)
        if not outer_offset:
            break

        outer_offset = [path for path in outer_offset if len(path) >= 3]
        if not outer_offset:
            break

        pc = pyclipper.Pyclipper()
        pc.AddPaths(outer_offset, pyclipper.PT_SUBJECT, True)

        if inner_paths:
            pc.AddPaths(inner_paths, pyclipper.PT_CLIP, True)
            clipped = pc.Execute(pyclipper.CT_DIFFERENCE)
        else:
            clipped = outer_offset

        if not clipped:
            break

        if not clipped:
            break

        inset_paths.extend(clipped)
        i += 1

    inset_paths = filter_short_paths_near_holes(inset_paths, inner_paths, length_thresh=700000, dist_thresh=700000)
    return filter_short_intersecting_paths(inset_paths, length_thresh=800000)


def generate_inset_paths_separated_with_centroid(multipolygon: MultiPolygon, step: float):
    result = []

    if isinstance(multipolygon, Polygon):
        centroid = multipolygon.centroid.coords[0]
        inset_levels = generate_inset_paths_for_polygon(multipolygon, step)
        result.append((centroid, inset_levels))

    elif isinstance(multipolygon, MultiPolygon):
        for poly in multipolygon.geoms:
            if poly.is_empty:
                continue
            centroid = poly.centroid.coords[0]
            inset_levels = generate_inset_paths_for_polygon(poly, step)
            result.append((centroid, inset_levels))

    else:
        raise ValueError(f"Unsupported geometry type: {type(multipolygon)}")

    return result


def sort_by_centroid_distance(data_input):
    if not data_input:
        return []

    def distance(p1, p2):
        return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    data = data_input[:]  # копия
    sorted_data = [data.pop(0)]
    last_centroid = sorted_data[0][0]

    while data:
        nearest_index = None
        nearest_dist = float('inf')

        for i, (centroid, _) in enumerate(data):
            dist = distance(last_centroid, centroid)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_index = i

        sorted_data.append(data.pop(nearest_index))
        last_centroid = sorted_data[-1][0]

    return sorted_data

def unpack_sorted_data(sorted_data):
    unpacked = []
    for _, inset_levels in sorted_data:
        unpacked.append(inset_levels)
    return unpacked


def plot_inset_paths(paths):
    fig, ax = plt.subplots()
    ax.set_aspect('equal', adjustable='box')
    all_x, all_y = [], []

    for figure in paths:
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


def get_polygon_coordinates(shape):
    polygons = []
    if not shape or shape.IsEmpty():
        return polygons

    for i in range(shape.OutlineCount()):
        outline = shape.Outline(i)
        points = []
        for v in range(outline.GetPointCount()):
            vertex = outline.GetPoint(v)
            points.append((vertex.x, vertex.y))
        polygons.append(points)
    return polygons


def convert_shape_to_shapely(shape):
    coords = get_polygon_coordinates(shape)
    if coords:
        if len(coords) == 1:
            return MultiPolygon([Polygon(coords[0])])
        else:
            return MultiPolygon([Polygon(poly) for poly in coords])
    else:
        return None
