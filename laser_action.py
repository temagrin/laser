import os
import pcbnew
import wx

from core.path_tools import ShapelyPathGenerator
from core.geometry import PCB
from core.machine import Machine
from core.polygons import GeometryTool
from core.previewer import Plotter
from core.settings import PluginConfig


class LaserSettingsDialog(wx.Dialog):
    def __init__(self, config, title):
        super().__init__(None, title=title)

        panel = wx.Panel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox_dir = wx.BoxSizer(wx.HORIZONTAL)
        self.dir_ctrl = wx.TextCtrl(panel)
        dir_btn = wx.Button(panel, label="...")
        dir_btn.Bind(wx.EVT_BUTTON, self.on_choose_dir)
        hbox_dir.Add(wx.StaticText(panel, label="Рабочая директория:"), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                     border=8)
        hbox_dir.Add(self.dir_ctrl, proportion=1, flag=wx.EXPAND)
        hbox_dir.Add(dir_btn, flag=wx.LEFT, border=8)
        vbox.Add(hbox_dir, flag=wx.EXPAND | wx.ALL, border=10)

        hbox_num = wx.BoxSizer(wx.HORIZONTAL)
        self.step_ctrl = wx.TextCtrl(panel)
        hbox_num.Add(wx.StaticText(panel, label="Диаметр лазерного луча:"), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                     border=8)
        hbox_num.Add(self.step_ctrl, proportion=1, flag=wx.EXPAND)
        vbox.Add(hbox_num, flag=wx.EXPAND | wx.ALL, border=10)

        hbox_num2 = wx.BoxSizer(wx.HORIZONTAL)
        self.power_ctrl = wx.TextCtrl(panel)
        hbox_num2.Add(wx.StaticText(panel, label="Мощность лазера:"), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                      border=8)
        hbox_num2.Add(self.power_ctrl, proportion=1, flag=wx.EXPAND)
        vbox.Add(hbox_num2, flag=wx.EXPAND | wx.ALL, border=10)

        hbox_layer = wx.BoxSizer(wx.HORIZONTAL)
        self.layer_choice = wx.Choice(panel, choices=["F.Cu", "B.Cu"])
        self.layer_choice.SetMaxSize(wx.Size(250, -1))
        hbox_layer.Add(wx.StaticText(panel, label="Слой меди:"), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)
        hbox_layer.Add(self.layer_choice, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(hbox_layer, flag=wx.EXPAND | wx.ALL, border=10)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK, label="Сгенерировать")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="Отмена")
        hbox_btns.Add(ok_btn, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        hbox_btns.Add(cancel_btn, flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        vbox.Add(hbox_btns, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=20)

        panel.SetSizer(vbox)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(main_sizer)
        self.SetMinSize((500, 280))
        self.Layout()
        self.Fit()

        # Установка значений из конфига
        self.dir_ctrl.SetValue(config.user_dir)
        self.step_ctrl.SetValue(str(config.laser_beam_wide))
        self.power_ctrl.SetValue(str(config.laser_power))
        if config.copper_layer == pcbnew.F_Cu:
            self.layer_choice.SetStringSelection("F.Cu")
        else:
            self.layer_choice.SetStringSelection("B.Cu")

    def on_choose_dir(self, event):
        dialog = wx.DirDialog(self, "Выберите рабочую директорию")
        if dialog.ShowModal() == wx.ID_OK:
            self.dir_ctrl.SetValue(dialog.GetPath())
        dialog.Destroy()

    def get_parameters(self):
        return {
            "work_dir": self.dir_ctrl.GetValue(),
            "step": self.step_ctrl.GetValue(),
            "power": self.power_ctrl.GetValue(),
            "layer": self.layer_choice.GetStringSelection(),
        }


def show_msq(title, message):
    dlg = wx.MessageDialog(None, message, title, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()


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

    def get_gui_config(self):
        config = PluginConfig()
        config.load_config()

        dlg = LaserSettingsDialog(config, self.title)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        params = dlg.get_parameters()
        dlg.Destroy()

        config.user_dir = params.get("work_dir", config.user_dir)
        config.laser_beam_wide = int(params.get("step", config.laser_beam_wide))
        config.laser_power = int(params.get("power", config.laser_power))

        layer = params.get("layer", config.copper_layer)
        if layer == "F.Cu":
            config.copper_layer = pcbnew.F_Cu
        elif layer == "B.Cu":
            config.copper_layer = pcbnew.B_Cu

        config.save_config()
        return config

    def Run(self):
        config = self.get_gui_config()
        if not config:
            return

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

        if config.show_preview_path:
            Plotter.plot_inset_paths(paths)

        Machine.generate_gcode_to_file(
            paths=paths,
            filename=config.get_laser_gcode_filename(),
            base_speed=config.base_speed,
            short_speed=config.short_speed,
            laser_power=config.laser_power,
            round_um=config.round_um,
            skip_min_length=config.skip_min_length,
            min_contour_length=config.min_contour_length,
            max_contour_length=config.max_contour_length)

        show_msq(self.title, f"Сохранен файл {config.get_laser_gcode_filename()}")
        return


Laser().register()
