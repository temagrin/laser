from math import sqrt

from shapely import MultiPolygon, Polygon
from shapely.affinity import translate, scale


class GeometryTool:
    @staticmethod
    def convert_shape_to_shapely(coords) -> MultiPolygon:
        if coords:
            if len(coords) == 1:
                return MultiPolygon([Polygon(coords[0])])
            else:
                return MultiPolygon([Polygon(poly) for poly in coords])
        else:
            return MultiPolygon([])

    @staticmethod
    def get_shapely_complete_multy_poly(poly_coords, hole_coords) -> MultiPolygon:
        poly_multy_poly = GeometryTool.convert_shape_to_shapely(poly_coords)
        if hole_coords:
            hole_multy_poly = GeometryTool.convert_shape_to_shapely(hole_coords)
            poly_multy_poly = poly_multy_poly.difference(hole_multy_poly)
        return poly_multy_poly

    @staticmethod
    def offset_geometry(poly_set, origin_x, origin_y):
        return translate(poly_set, xoff=-origin_x, yoff=-origin_y)

    @staticmethod
    def mirror_geometry(geom, axis='x', around_center=True):
        """
        Зеркально отражает Polygon или MultiPolygon по указанной оси без смещения.

        :param geom: Объект Polygon или MultiPolygon
        :param axis: 'x' — зеркалит по горизонтальной оси, 'y' — по вертикальной
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

    @staticmethod
    def sort_by_centroid_distance(data_input):
        if not data_input:
            return []

        def distance(p1, p2):
            return sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

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

        return [polygone for _, polygone in sorted_data]

    @classmethod
    def extract_sorted_polygons(cls, multipolygon):
        result = []

        if isinstance(multipolygon, Polygon):
            centroid = multipolygon.centroid.coords[0]
            result.append((centroid, multipolygon))

        elif isinstance(multipolygon, MultiPolygon):
            for poly in multipolygon.geoms:
                if poly.is_empty:
                    continue
                centroid = poly.centroid.coords[0]
                result.append((centroid, poly))
        else:
            raise ValueError(f"Unsupported geometry type: {type(multipolygon)}")

        return cls.sort_by_centroid_distance(result)

    @staticmethod
    def shapely_to_paths(geom):
        """
        Преобразовать Shapely Polygon/MultiPolygon в список путей.
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
