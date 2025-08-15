import os
import pcbnew
import wx

from geometry import PCB
from machine import Machine
from settings import Config
from tools import *


class Laser(pcbnew.ActionPlugin):
    def __init__(self):
        super().__init__()
        self.description = "Объединение медных объектов слоя и отображение на User_1"
        self.category = "Hardware"
        self.name = "Laser processing"
        self.title = "Laser processing"
        self.plugin_path = os.path.dirname(__file__)

    def defaults(self):
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(self.plugin_path, "icons/icon.svg")

    def show_msq(self, message):
        dlg = wx.MessageDialog(None, message, self.title, wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def Run(self):
        config = Config(plugin_path=self.plugin_path)
        config.load()

        board = pcbnew.GetBoard()
        if not board:
            self.show_msq("Ошибка: нет открытой платы")
            return

        pcb = PCB(layout=pcbnew.F_Cu, config=config)
        origin_x, origin_y = pcb.get_board_origin_from_edges(board)
        if origin_x == 0 or origin_y == 0:
            self.show_msq("Не задана область обрезки платы")
            return

        poly_sets, hole_sets = pcb.get_cu_geometry(board)

        if not poly_sets:
            self.show_msq("На выбранном слое нет медных объектов")
            return

        union_poly_set = pcb.union_poly_sets(poly_sets)
        if union_poly_set is None or union_poly_set.IsEmpty():
            self.show_msq("Ошибка при объединении полигонов")
            return
        cu_multy = convert_shape_to_shapely(union_poly_set)

        # Экспонировать с отверстиями
        if config.expose_holes and hole_sets:
            holes_poly_set = pcb.union_poly_sets(hole_sets)
            ho_multy = convert_shape_to_shapely(holes_poly_set)
            cu_with_holes_multy = cu_multy.difference(ho_multy)
        else:
            cu_with_holes_multy = cu_multy

        if config.show_preview:
            render_preview(cu_with_holes_multy)

        cu_with_holes_multy = offset_geometry(cu_with_holes_multy, origin_x, origin_y)
        cu_with_holes_multy = mirror_geometry(cu_with_holes_multy)
        if config.copper_layer == pcbnew.B_Cu:
            cu_with_holes_multy = mirror_geometry(cu_with_holes_multy, 'y')

        machine = Machine()

        paths = generate_inset_paths(cu_with_holes_multy, step=config.laser_beam_wide)
        gcode_lines = machine.generate_gcode_from_paths(paths,
                                                        base_speed=config.base_speed,
                                                        speed_increment=config.speed_increment,
                                                        base_power=config.base_power,
                                                        power_decrement=config.power_decrement,
                                                        round_um=config.round_um,
                                                        outer_speed_boost=config.outer_speed_boost
                                                        )
        machine.save_gcode_to_file(gcode_lines, config.get_laser_gcode_filename())

        if config.show_preview:
            plot_inset_paths(paths)


Laser().register()
