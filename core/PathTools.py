from shapely import unary_union, MultiPolygon, Polygon
from core.tools import get_path_length


class ShapelyPathGenerator:
    @staticmethod
    def generate_inset_paths(current_geom, step: float, min_length=400000):
        inset_levels = []
        i = 1
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
                contour_points = list(poly.exterior.coords)
                if get_path_length(contour_points) > min_length:
                    inset_levels.append(contour_points)
                for interior in poly.interiors:
                    hole_contour_points = list(interior.coords)
                    if get_path_length(hole_contour_points) > min_length:
                        inset_levels.append(hole_contour_points)
            i += 1
        return inset_levels
