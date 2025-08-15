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
    print("MIN-MAX: ", minx, miny, maxx, maxy)

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

        # ===== отверстия (интерьеры) =====
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


def generate_inset_paths(multipolygon: MultiPolygon, step: float):
    """
    Генерирует внутренние эквидистантные контуры (inset offsets) для MultiPolygon с шагом step
    и строит их до полного исчезновения фигуры.

    :param multipolygon: исходный объект MultiPolygon или Polygon (Shapely)
    :param step: расстояние смещения внутрь (>0), в тех же единицах, что и координаты
    :return: список уровней offset'а — каждый уровень это список контуров,
             где каждый контур это список координат [(x, y), ...]
    """
    if isinstance(multipolygon, Polygon):
        current_geom = multipolygon
    elif isinstance(multipolygon, MultiPolygon):
        current_geom = unary_union([g for g in multipolygon.geoms if not g.is_empty])
    else:
        raise ValueError(f"Unsupported geometry type: {type(multipolygon)}")

    inset_levels = []
    i = 1

    while True:
        offset_distance = -step * i
        offset_geom = current_geom.buffer(offset_distance)

        if offset_geom.is_empty:
            break

        # Приводим к списку полигонов
        if isinstance(offset_geom, Polygon):
            polys = [offset_geom]
        elif isinstance(offset_geom, MultiPolygon):
            polys = list(offset_geom.geoms)
        else:
            polys = [g for g in offset_geom.geoms if isinstance(g, Polygon)]

        if not polys:
            break

        contours = []
        for poly in polys:
            # внешний контур
            contours.append(list(poly.exterior.coords))
            # внутренние отверстия
            for interior in poly.interiors:
                contours.append(list(interior.coords))

        inset_levels.append(contours)
        i += 1

    return inset_levels


def plot_inset_paths(inset_levels):
    """
    Отображает сгенерированные эквидистантные пути (выход generate_inset_paths)
    :param inset_levels: список уровней offset'а, каждый уровень — список контуров (список (x, y))
    """
    fig, ax = plt.subplots()
    ax.set_aspect('equal', adjustable='box')

    # Градиент цветов по числу уровней
    colors = cm.get_cmap('viridis', len(inset_levels))

    all_x, all_y = [], []

    for level_idx, contours in enumerate(inset_levels):
        color = colors(level_idx)  # Цвет для этого уровня
        for contour in contours:
            if len(contour) < 3:
                continue  # пропускаем вырожденные
            poly_patch = MplPolygon(contour, closed=True,
                                    facecolor='none',
                                    edgecolor=color,
                                    linewidth=1)
            ax.add_patch(poly_patch)

            # Сохраняем координаты для автолимитов
            xs, ys = zip(*contour)
            all_x.extend(xs)
            all_y.extend(ys)

    if all_x and all_y:
        padding_x = (max(all_x) - min(all_x)) * 0.05 or 1
        padding_y = (max(all_y) - min(all_y)) * 0.05 or 1
        ax.set_xlim(min(all_x) - padding_x, max(all_x) + padding_x)
        ax.set_ylim(min(all_y) - padding_y, max(all_y) + padding_y)

    ax.grid(True, linestyle='--', alpha=0.5)
    plt.title("Inset Paths Preview")
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

