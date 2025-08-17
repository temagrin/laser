import os
import pcbnew
import wx

from core.gui import get_gui_config, show_msq, PenFrame
from core.path_tools import ShapelyPathGenerator
from core.geometry import PCB
from core.machine import Machine
from core.polygons import GeometryTool
from core.previewer import Plotter


class Laser(pcbnew.ActionPlugin):
    def __init__(self):
        super().__init__()
        self.title = "Laser processing"
        self.name = "Laser processing"
        self.category = "Hardware"
        self.description = "Генератор GCODE для лазерного векторного экспонирования"

    def defaults(self):
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "icons/icon.svg")

    def Run(self):
        config = get_gui_config(self.title)
        if not config:
            return

        pend_frame = PenFrame(self.title)

        board = pcbnew.GetBoard()
        if not board:
            show_msq(self.title, "Ошибка: нет открытой платы")
            return

        origin_x, origin_y = PCB.get_board_origin_from_edges(board)
        if origin_x == 0 or origin_y == 0:
            show_msq(self.title, "Не задана область обрезки платы")
            return

        poly_coords, hole_coords = PCB.get_cu_geometry(
            board=board,
            copper_layer=config.copper_layer,
            tent_via=config.tent_via,
            tent_th=config.tent_th,
            arc_segments=config.arc_segments)

        if not poly_coords:
            show_msq(self.title, "На выбранном слое нет медных объектов")
            return

        shapely_multy = GeometryTool.get_shapely_complete_multy_poly(poly_coords, hole_coords)
        shapely_multy = GeometryTool.offset_geometry(shapely_multy, origin_x, origin_y)
        shapely_multy = GeometryTool.mirror_geometry(shapely_multy)

        if config.copper_layer == pcbnew.B_Cu:
            shapely_multy = GeometryTool.mirror_geometry(shapely_multy, 'y')

        polygons = GeometryTool.extract_sorted_polygons(shapely_multy)
        if config.show_preview:
            Plotter.render_preview(polygons)

        paths = []
        for figure in polygons:
            paths.append(ShapelyPathGenerator.generate_inset_paths(figure, config.laser_beam_wide))

        if config.show_paths:
            Plotter.plot_inset_paths(paths)

        Machine.generate_gcode_to_file(
            paths=paths,
            filename=config.get_laser_gcode_filename(),
            base_speed=config.base_speed,
            short_speed=config.short_speed,
            laser_power=config.laser_power,
            round_um=config.round_um,
            min_contour_length=config.min_contour_length,
            max_contour_length=config.max_contour_length)
        pend_frame.Destroy()
        show_msq(self.title, f"Сохранен файл {config.get_laser_gcode_filename()}")
        return


Laser().register()
