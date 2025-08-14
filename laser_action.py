import math
import os
import pcbnew
from pcbnew import ERROR_INSIDE

import wx
from shapely import Polygon, MultiPolygon
from shapely.affinity import translate

from tools import render_preview, generate_inset_paths, plot_inset_paths, generate_gcode_from_paths, save_gcode_to_file, \
    mirror_geometry

MAX_ERROR = 10000
SHOW_PREVIEW = False
LASER_BEAM_WIDE = 100000.0  # в нанометрах для kicad


def get_polygon_coordinates(shape: pcbnew.SHAPE_POLY_SET):
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


def show_msq(message, title):
    dlg = wx.MessageDialog(None, message, title, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()


def get_board_origin_from_edges(board):
    """
    Определяет пользовательскую "нулевую" точку по границам платы (Edge.Cuts)
    как нижний левый угол ограничивающего прямоугольника.

    :param board: объект платы pcbnew.GetBoard()
    :return: (origin_x, origin_y) в внутренних единицах KiCad (нм)
    """
    points = get_edge_cuts_points(board)
    if not points:
        raise ValueError("Не найдены точки на Edge.Cuts")

    # Минимальные координаты — нижний левый угол
    min_x = min(p[0] for p in points)
    min_y = min(p[1] for p in points)
    return min_x, min_y


def get_edge_cuts_points(board):
    layer = pcbnew.Edge_Cuts  # слой Edge.Cuts

    points = []

    # Получаем все рисованные объекты на слое Edge.Cuts
    drawings = board.GetDrawings()
    for d in drawings:
        if d.GetLayer() == layer:
            shape = d.GetShape()
            # В зависимости от типа объекта извлекаем точки
            if shape == pcbnew.S_SEGMENT:
                # Линия (Segment)
                start = d.GetStart()
                end = d.GetEnd()
                points.append((start.x, start.y))
                points.append((end.x, end.y))
            elif shape == pcbnew.S_ARC:
                # Дуга (Arc)
                start = d.GetStart()
                end = d.GetEnd()
                points.append((start.x, start.y))
                points.append((end.x, end.y))
            elif shape == pcbnew.S_CIRCLE:
                # Круг — центр и радиус (точки начала контура можно взять как центр окружности)
                center = d.GetCenter()
                points.append((center.x, center.y))
            elif shape == pcbnew.S_POLYGON:
                # Полилиния или многоугольник
                poly_set = d.GetPolyShape()
                for i in range(poly_set.OutlineCount()):
                    outline = poly_set.Outline(i)
                    for v in range(outline.GetPointCount()):
                        pt = outline.GetPoint(v)
                        points.append((pt.x, pt.y))
            elif shape == pcbnew.S_RECT:
                # Прямоугольник: берём противоположные углы и формируем остальные вершины
                start = d.GetStart()  # один угол
                end = d.GetEnd()  # противоположный угол

                # Четыре угла
                p1 = (start.x, start.y)
                p2 = (end.x, start.y)
                p3 = (end.x, end.y)
                p4 = (start.x, end.y)

                points.extend([p1, p2, p3, p4])
            else:
                print("Необработанная реализация области обрезки", shape)
                pass

    unique_points = list(set(points))
    unique_points.sort(key=lambda p: (p[0], p[1]))
    return unique_points


class Laser(pcbnew.ActionPlugin):
    def __init__(self):
        super().__init__()
        self.copper_layer = pcbnew.F_Cu
        self.description = "Объединение медных объектов слоя и отображение на User_1"
        self.category = "Hardware"
        self.name = "Laser processing"

    def defaults(self):
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "icons/icon.svg")

    @staticmethod
    def clear_user_layer(board):
        to_delete = [item for item in board.GetDrawings() if item.GetLayer() in [pcbnew.User_1, pcbnew.User_2]]
        for item in to_delete:
            board.Remove(item)
        pcbnew.Refresh()

    def track_to_poly_set(self, track):
        poly_set = pcbnew.SHAPE_POLY_SET()
        clearance = 0
        track.TransformShapeToPolygon(poly_set, self.copper_layer, clearance, MAX_ERROR, ERROR_INSIDE)
        return poly_set

    def pad_to_poly_set(self, pad):
        poly_set = pcbnew.SHAPE_POLY_SET()
        clearance = 0
        pad.TransformShapeToPolygon(poly_set, self.copper_layer, clearance, MAX_ERROR, ERROR_INSIDE)
        return poly_set

    @staticmethod
    def zone_to_poly_set(zone):
        poly_set = pcbnew.SHAPE_POLY_SET()
        for i in range(zone.OutlineCount()):
            outline = zone.Outline(i)
            poly_set.AddOutline(outline)
        return poly_set

    @staticmethod
    def union_poly_sets(poly_sets):
        if not poly_sets:
            return None
        filtered = [ps for ps in poly_sets if ps and not ps.IsEmpty()]
        if not filtered:
            return None
        result = pcbnew.SHAPE_POLY_SET(filtered[0])
        for ps in filtered[1:]:
            result.BooleanAdd(ps)
        return result

    @staticmethod
    def create_slot_from_object(center, drill_x, drill_y, orientation_degrees):
        angle_rad = math.radians(orientation_degrees)

        length = max(drill_x, drill_y)  # общая длина прорези (включая торцы)
        width = min(drill_x, drill_y)  # ширина прорези (диаметр фрезы)
        radius = width // 2  # радиус закругления торцов

        # Расстояние от центра прорези до центра полукруга с каждой стороны
        half_length = (length - width) // 2
        if half_length < 0:
            # Предотвращаем отрицательный размер (если ширина больше длины)
            half_length = 0

        poly_set = pcbnew.SHAPE_POLY_SET()
        outline = pcbnew.SHAPE_LINE_CHAIN()

        points = []

        segments = 32  # количество сегментов для аппроксимации дуг

        # Левая полуокружность (сверху вниз)
        for i in range(segments + 1):
            ang = math.pi / 2 + math.pi * i / segments  # от 90° до 270°
            x = -half_length + radius * math.cos(ang)
            y = radius * math.sin(ang)
            points.append((x, y))

        # Правая полуокружность (снизу вверх)
        for i in range(segments + 1):
            ang = 3 * math.pi / 2 + math.pi * i / segments  # от 270° до 450°
            x = half_length + radius * math.cos(ang)
            y = radius * math.sin(ang)
            points.append((x, y))

        # Поворот и перенос точек в центр + ориентация
        for x, y in points:
            xr = int(center.x + (x * math.cos(angle_rad) - y * math.sin(angle_rad)))
            yr = int(center.y + (x * math.sin(angle_rad) + y * math.cos(angle_rad)))
            outline.Append(pcbnew.VECTOR2I(xr, yr))

        outline.SetClosed(True)
        poly_set.AddOutline(outline)

        return poly_set

    @staticmethod
    def poly_set_to_draw_segments(board, poly_set, lay):
        poly_shape = pcbnew.PCB_SHAPE(board)
        poly_shape.SetShape(pcbnew.S_POLYGON)
        poly_shape.SetLayer(lay)
        poly_shape.SetPolyShape(poly_set)
        board.Add(poly_shape)

    def Run(self):
        board = pcbnew.GetBoard()
        if not board:
            show_msq("Ошибка: нет открытой платы", "Laser Fill")
            return

        poly_sets = []
        hole_sets = []
        clearance = 0
        origin_x, origin_y = get_board_origin_from_edges(board)
        if origin_x == 0 or origin_y == 0:
            show_msq("Не задана область обрезки платы", "Laser Fill")
            return

        # Сбор медных объектов
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetLayer() == self.copper_layer:
                    poly_set = self.pad_to_poly_set(pad)
                    if poly_set and not poly_set.IsEmpty():
                        poly_sets.append(poly_set)

                    drill_x = pad.GetDrillSizeX()
                    drill_y = pad.GetDrillSizeY()
                    orientation = pad.GetOrientation().AsDegrees()
                    if drill_x > 0 and drill_y > 0:
                        hole_poly = self.create_slot_from_object(pad.GetPosition(), drill_x, drill_y, orientation)
                        hole_sets.append(hole_poly)

        for track in board.GetTracks():
            cls = track.GetClass()
            if cls == "PCB_VIA":
                poly_set = pcbnew.SHAPE_POLY_SET()
                track.TransformShapeToPolygon(poly_set, self.copper_layer, clearance, MAX_ERROR, ERROR_INSIDE)
                if poly_set and not poly_set.IsEmpty():
                    poly_sets.append(poly_set)
                drill_x = track.GetDrill()
                drill_y = track.GetDrill()
                orientation = 0
                if drill_x > 0 and drill_y > 0:
                    hole_poly = self.create_slot_from_object(track.GetPosition(), drill_x, drill_y, orientation)
                    hole_sets.append(hole_poly)

            elif cls == "PCB_TRACK":
                if track.GetLayer() == self.copper_layer:
                    poly_set = self.track_to_poly_set(track)
                    if poly_set and not poly_set.IsEmpty():
                        poly_sets.append(poly_set)

        for zone in board.Zones():
            if zone.GetLayer() == self.copper_layer:
                poly_set = self.zone_to_poly_set(zone)
                if poly_set and not poly_set.IsEmpty():
                    poly_sets.append(poly_set)

        if not poly_sets:
            show_msq("На выбранном слое нет медных объектов", "Laser Fill")
            return

        union_poly_set = self.union_poly_sets(poly_sets)
        if union_poly_set is None or union_poly_set.IsEmpty():
            show_msq("Ошибка при объединении полигонов", "Laser Fill")
            return

        holes_poly_set = self.union_poly_sets(hole_sets)  # объединённые отверстия

        # self.poly_set_to_draw_segments(board, union_poly_set, pcbnew.User_1)
        # self.poly_set_to_draw_segments(board, holes_poly_set, pcbnew.User_2)

        cu_multy = convert_shape_to_shapely(union_poly_set)
        ho_multy = convert_shape_to_shapely(holes_poly_set)
        cu_with_holes_multy = cu_multy.difference(ho_multy)
        if SHOW_PREVIEW:
            render_preview(cu_with_holes_multy)
        cu_with_holes_multy = translate(cu_with_holes_multy, xoff=-origin_x, yoff=-origin_y)
        cu_with_holes_multy = mirror_geometry(cu_with_holes_multy)
        if self.copper_layer == pcbnew.B_Cu:
            cu_with_holes_multy = mirror_geometry(cu_with_holes_multy, 'y')
        paths = generate_inset_paths(cu_with_holes_multy, step=LASER_BEAM_WIDE)
        gcodes = generate_gcode_from_paths(paths, base_speed=1000, speed_increment=200, base_power=1000,
                                           power_decrement=100)
        save_gcode_to_file(gcodes, "/home/user/test.gcode")

        # Отображаем пути
        plot_inset_paths(paths)

        pcbnew.Refresh()


Laser().register()
