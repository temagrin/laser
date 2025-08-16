from math import sqrt

from shapely import unary_union
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

    # Приводим к списку полигонов (чтобы работало и с Polygon, и с MultiPolygon)
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


def generate_inset_paths_for_polygon(polygon: Polygon, step: float):
    external_paths = []
    internal_paths = []

    i = 1
    current_geom = polygon

    while True:
        offset_distance = -step * i
        offset_geom = current_geom.buffer(offset_distance)

        if offset_geom.is_empty:
            break

        if isinstance(offset_geom, MultiPolygon):
            offset_geom = unary_union(offset_geom)

        if isinstance(offset_geom, Polygon):
            polys = [offset_geom]
        elif isinstance(offset_geom, MultiPolygon):
            polys = list(offset_geom.geoms)
        else:
            polys = []

        for poly in polys:
            external_paths.append(list(poly.exterior.coords))

            for interior in poly.interiors:
                internal_paths.append(list(interior.coords))

        i += 1
    internal_paths.reverse()
    combined_paths = external_paths + internal_paths
    return combined_paths


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
