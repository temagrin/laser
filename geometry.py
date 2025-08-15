import math
import pcbnew
from pcbnew import ERROR_INSIDE

MAX_ERROR = 10000


class PCB:
    def __init__(self, layout, config):
        self.copper_layer = layout
        self.config = config

    @staticmethod
    def get_board_origin_from_edges(board):
        """
        Определяет пользовательскую "нулевую" точку по границам платы (Edge.Cuts)
        как нижний левый угол ограничивающего прямоугольника.

        :param board: объект платы pcbnew.GetBoard()
        :return: (origin_x, origin_y) в внутренних единицах KiCad (нм)
        """
        points = PCB.get_edge_cuts_points(board)
        if not points:
            raise ValueError("Не найдены точки на Edge.Cuts")

        # Минимальные координаты — нижний левый угол
        min_x = min(p[0] for p in points)
        min_y = min(p[1] for p in points)
        return min_x, min_y

    @staticmethod
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

    @staticmethod
    def clear_user_layer(board):
        to_delete = [item for item in board.GetDrawings() if item.GetLayer() in [pcbnew.User_1, pcbnew.User_2]]
        for item in to_delete:
            board.Remove(item)
        pcbnew.Refresh()

    @staticmethod
    def track_to_poly_set(track, lay):
        poly_set = pcbnew.SHAPE_POLY_SET()
        clearance = 0
        track.TransformShapeToPolygon(poly_set, lay, clearance, MAX_ERROR, ERROR_INSIDE)
        return poly_set

    @staticmethod
    def pad_to_poly_set(pad, lay):
        poly_set = pcbnew.SHAPE_POLY_SET()
        clearance = 0
        pad.TransformShapeToPolygon(poly_set, lay, clearance, MAX_ERROR, ERROR_INSIDE)
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

    def get_cu_geometry(self, board):
        poly_sets = []
        hole_sets = []
        clearance = 0

        # Сбор медных объектов
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetLayer() == self.copper_layer:
                    poly_set = self.pad_to_poly_set(pad, self.copper_layer)
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
                    poly_set = self.track_to_poly_set(track, self.copper_layer)
                    if poly_set and not poly_set.IsEmpty():
                        poly_sets.append(poly_set)

        for zone in board.Zones():
            if zone.GetLayer() == self.copper_layer:
                poly_set = self.zone_to_poly_set(zone)
                if poly_set and not poly_set.IsEmpty():
                    poly_sets.append(poly_set)

        return poly_sets, hole_sets
