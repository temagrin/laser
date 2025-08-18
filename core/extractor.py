import math
import pcbnew
from pcbnew import ERROR_INSIDE

MAX_ERROR = 10000


class PCB:
    @classmethod
    def get_board_origin_from_edges(cls, board):
        """
        Определяет пользовательскую "нулевую" точку по границам платы (Edge.Cuts)
        как нижний левый угол ограничивающего прямоугольника.

        :param board: объект платы pcbnew.GetBoard()
        :return: (origin_x, origin_y) в внутренних единицах KiCad (нм)
        """
        points = cls.get_edge_cuts_points(board)
        if not points:
            return 0, 0

        # TODO надо пройти момент
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
    def create_thick_rectangle_poly_set(draw):
        if draw.GetShape() != pcbnew.S_RECT:
            raise ValueError("Объект не является S_RECT")

        start = draw.GetStart()
        end = draw.GetEnd()
        line_width = draw.GetWidth()
        x0, y0 = start.x, start.y
        x1, y1 = end.x, end.y
        thickness = line_width // 2

        poly_set = pcbnew.SHAPE_POLY_SET()
        outline = pcbnew.SHAPE_LINE_CHAIN()

        points = [
            pcbnew.VECTOR2I(x0-thickness, y0-thickness),
            pcbnew.VECTOR2I(x1+thickness, y0-thickness),
            pcbnew.VECTOR2I(x1+thickness, y1+thickness),
            pcbnew.VECTOR2I(x0-thickness, y1+thickness),
            pcbnew.VECTOR2I(x0-thickness, y1-thickness),
            pcbnew.VECTOR2I(x1-thickness, y1-thickness),
            pcbnew.VECTOR2I(x1-thickness, y0+thickness),
            pcbnew.VECTOR2I(x0+thickness, y0+thickness),
            pcbnew.VECTOR2I(x0+thickness, y1-thickness-1),
            pcbnew.VECTOR2I(x0-thickness, y1-thickness-1),
            pcbnew.VECTOR2I(x0-thickness, y0-thickness),
        ]

        for pt in points:
            outline.Append(pt)

        outline.SetClosed(True)
        poly_set.AddOutline(outline)
        return poly_set

    @staticmethod
    def draw_to_poly_set(draw, lay):
        if draw.GetShape() == pcbnew.S_RECT:
            return PCB.create_thick_rectangle_poly_set(draw)
        else:
            poly_set = pcbnew.SHAPE_POLY_SET()
            clearance = 0
            draw.TransformShapeToPolygon(poly_set, lay, clearance, MAX_ERROR, ERROR_INSIDE)
            return poly_set

    @staticmethod
    def create_slot_from_object(center, drill_x, drill_y, orientation_degrees, segments):
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

        for i in range(segments + 1):
            ang = math.pi / 2 + math.pi * i / segments  # от 90° до 270°
            x = -half_length + radius * math.cos(ang)
            y = radius * math.sin(ang)
            points.append((x, y))

        for i in range(segments + 1):
            ang = 3 * math.pi / 2 + math.pi * i / segments  # от 270° до 450°
            x = half_length + radius * math.cos(ang)
            y = radius * math.sin(ang)
            points.append((x, y))

        for x, y in points:
            xr = int(center.x + (x * math.cos(angle_rad) - y * math.sin(angle_rad)))
            yr = int(center.y + (x * math.sin(angle_rad) + y * math.cos(angle_rad)))
            outline.Append(pcbnew.VECTOR2I(xr, yr))

        outline.SetClosed(True)
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

    @classmethod
    def get_cu_geometry(cls, board, copper_layer, tent_via=False, tent_th=False, arc_segments=32):
        poly_sets = []
        hole_sets = []
        clearance = 0
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                attrs = pad.GetAttribute()
                # THROUGH-HOLE
                if attrs in [pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH]:
                    if pad.GetLayer() in [copper_layer, 0]:
                        poly_set = cls.pad_to_poly_set(pad, pad.GetLayer())
                        if poly_set and not poly_set.IsEmpty():
                            poly_sets.append(poly_set)
                # SMD
                else:
                    if fp.IsFlipped() == (copper_layer == pcbnew.B_Cu):
                        poly_set = cls.pad_to_poly_set(pad, copper_layer)
                        if poly_set and not poly_set.IsEmpty():
                            poly_sets.append(poly_set)

                if pad.HasDrilledHole():
                    drill_x = pad.GetDrillSizeX()
                    drill_y = pad.GetDrillSizeY()
                    pos = pad.GetPosition()
                    orientation = pad.GetOrientation().AsDegrees()
                    if drill_x > 0 and drill_y > 0 and not tent_th:
                        hole_poly = cls.create_slot_from_object(pos, drill_x, drill_y, orientation, arc_segments)
                        hole_sets.append(hole_poly)

        for track in board.GetTracks():
            cls_track = track.GetClass()
            if cls_track == "PCB_VIA":
                poly_set = pcbnew.SHAPE_POLY_SET()
                track.TransformShapeToPolygon(poly_set, copper_layer, clearance, MAX_ERROR, ERROR_INSIDE)
                if poly_set and not poly_set.IsEmpty():
                    poly_sets.append(poly_set)
                drill = track.GetDrill()
                orientation = 0
                pos = track.GetPosition()
                if drill > 0 and not tent_via:
                    hole_poly = cls.create_slot_from_object(pos, drill, drill, orientation, arc_segments)
                    hole_sets.append(hole_poly)

            elif cls_track == "PCB_TRACK":
                if track.GetLayer() == copper_layer:
                    poly_set = cls.track_to_poly_set(track, copper_layer)
                    if poly_set and not poly_set.IsEmpty():
                        poly_sets.append(poly_set)

        for drawing in board.Drawings():
            if drawing.GetLayer() == copper_layer:
                poly_set = cls.draw_to_poly_set(drawing, copper_layer)
                if poly_set and not poly_set.IsEmpty():
                    poly_sets.append(poly_set)

        for zone in board.Zones():
            if zone.GetLayer() == copper_layer:
                poly_set = cls.zone_to_poly_set(zone)
                if poly_set and not poly_set.IsEmpty():
                    poly_sets.append(poly_set)

        poly_sets_multy = cls.union_poly_sets(poly_sets)
        holy_sets_multy = cls.union_poly_sets(hole_sets)
        poly_sets_coords = cls.get_polygon_coordinates(poly_sets_multy)
        holy_sets_coords = cls.get_polygon_coordinates(holy_sets_multy)
        return poly_sets_coords, holy_sets_coords
