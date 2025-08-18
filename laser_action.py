import os
import pcbnew

from core.gui import GUI
from core.extractor import PCB
from core.machine import Machine
from core.geometry import GeometryTool
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
        gui = GUI(self.title)

        config = gui.get_gui_config()
        if not config:
            return

        gui.show_spinner()

        board = pcbnew.GetBoard()
        if not board:
            gui.show_msq("Ошибка: нет открытой платы")
            return

        origin_x, origin_y = PCB.get_board_origin_from_edges(board)
        if origin_x == 0 or origin_y == 0:
            gui.show_msq("Не задана область обрезки платы. Расположите на слое Edge.cut прямоугольник - "
                         "границы платы")
            return

        poly_coords, hole_coords = PCB.get_cu_geometry(
            board=board,
            copper_layer=config.copper_layer,
            tent_via=config.tent_via,
            tent_th=config.tent_th,
            arc_segments=config.arc_segments)

        if not poly_coords:
            gui.show_msq("На выбранном слое нет медных объектов")
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
            figure_paths = GeometryTool.generate_inset_paths(
                current_geom=figure,
                step=config.laser_beam_wide,
                min_length_um=config.min_length_um,
                sort_type=config.sort_type)
            if figure_paths:
                paths.append(figure_paths)

        if config.show_paths:
            Plotter.plot_inset_paths(paths)

        filename = f"laser_{config.COPPER_LAYERS[config.copper_layer]}.gcode"
        output_filename = os.path.join(config.user_dir, filename)

        Machine.generate_gcode_to_file(
            paths=paths,
            filename=output_filename,
            base_speed=config.base_speed,
            short_speed=config.short_speed,
            laser_power=config.laser_power,
            round_um=config.round_um,
            min_contour_length=config.min_contour_length,
            max_contour_length=config.max_contour_length)

        gui.destroy_spinner()
        gui.show_msq(f"Сохранен файл {output_filename}")


Laser().register()
