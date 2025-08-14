import math

from shapely import unary_union
from shapely.affinity import scale
from shapely.geometry import MultiPolygon, Polygon
from matplotlib import cm
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon


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


def generate_gcode_from_paths(
    inset_levels,
    base_speed=1000,
    speed_increment=200,
    base_power=1000,
    power_decrement=100,
    round_um=2,
    outer_speed_boost=0.5
):
    """
    Генерирует G-code для лазерной заливки с:
      - повышением скорости в плотных зонах (глубокие offset'ы)
      - внешние контуры тоже быстрее, чем базовая скорость
      - сортировка контуров внутри уровня по принципу ближайшего соседа
        и автоматическим разворотом для минимизации холостого хода.

    :param inset_levels: [[[ (x_nm, y_nm), ...], ...], ...] — пути по уровням (нм)
    :param base_speed: базовая (минимальная) скорость, мм/мин
    :param speed_increment: прибавка при переходе к более плотному уровню
    :param base_power: мощность лазера на первом уровне
    :param power_decrement: насколько уменьшать мощность на каждый уровень
    :param round_um: округление координат, мкм (1 мкм = 0.001 мм)
    :param outer_speed_boost: множитель прироста скорости для внешнего контура
    """
    nm_to_mm = 1e-6
    scale = 1e-3 * round_um

    # --- внутренняя функция сортировки ---
    def sort_paths_nearest(contours):
        if not contours:
            return []
        remaining = contours[:]
        sorted_contours = []
        current = remaining.pop(0)
        sorted_contours.append(current)
        current_end = current[-1]

        while remaining:
            min_dist = float("inf")
            min_idx = 0
            reverse_needed = False

            for i, contour in enumerate(remaining):
                start_pt = contour[0]
                end_pt = contour[-1]
                dist_start = math.hypot(start_pt[0] - current_end[0],
                                        start_pt[1] - current_end[1])
                dist_end = math.hypot(end_pt[0] - current_end[0],
                                      end_pt[1] - current_end[1])
                if dist_start < min_dist:
                    min_dist = dist_start
                    min_idx = i
                    reverse_needed = False
                if dist_end < min_dist:
                    min_dist = dist_end
                    min_idx = i
                    reverse_needed = True

            next_contour = remaining.pop(min_idx)
            if reverse_needed:
                next_contour.reverse()
            sorted_contours.append(next_contour)
            current_end = sorted_contours[-1][-1]

        return sorted_contours

    # --- начало формирования G-кода ---
    gcode = [
        "G21 ; set units to mm",
        "G90 ; absolute positioning",
        "M5 ; laser off"
    ]

    for level_idx, contours in enumerate(inset_levels):
        # сортируем в оптимальном порядке
        sorted_contours = sort_paths_nearest(contours)

        # вычисляем скорость
        if level_idx == 0:
            speed = base_speed + speed_increment * outer_speed_boost
        else:
            speed = base_speed + speed_increment * level_idx

        power = max(base_power - power_decrement * level_idx, 0)
        gcode.append(f"(Level {level_idx}, Speed {speed} mm/min, Power {power})")

        for contour in sorted_contours:
            if len(contour) < 2:
                continue

            # стартовая точка (округление и перевод)
            start_x = round(contour[0][0] * nm_to_mm / scale) * scale
            start_y = round(contour[0][1] * nm_to_mm / scale) * scale

            gcode.append("M5 ; laser off")
            gcode.append(f"G0 X{start_x:.3f} Y{start_y:.3f} F{speed}")
            gcode.append(f"M3 S{power}")

            # основной путь
            for x_nm, y_nm in contour[1:]:
                x_mm = round(x_nm * nm_to_mm / scale) * scale
                y_mm = round(y_nm * nm_to_mm / scale) * scale
                gcode.append(f"G1 X{x_mm:.3f} Y{y_mm:.3f} F{speed}")

            # замыкание
            gcode.append(f"G1 X{start_x:.3f} Y{start_y:.3f} F{speed}")
            gcode.append("M5 ; laser off")

    gcode.append("M5 ; laser off")
    gcode.append("G0 X0 Y0 ; home")

    return gcode
def save_gcode_to_file(gcode_lines, filename):
    """
    Сохраняет список строк G-code в указанный файл.
    """
    with open(filename, "w", encoding="utf-8") as f:
        for line in gcode_lines:
            f.write(line + "\n")
