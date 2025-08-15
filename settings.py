import os

import pcbnew


class Config:
    def __init__(self, plugin_path):
        self.show_preview = False
        self.copper_layer = pcbnew.B_Cu
        self.laser_beam_wide = 100000.0
        self.base_speed = 1000
        self.speed_increment = 200
        self.base_power = 1000
        self.power_decrement = 100
        self.round_um = 2,
        self.outer_speed_boost = 0.5
        self.icon_file_name = os.path.join(plugin_path, "config.json")
        self.user_dir = "/home/user"
        self.expose_holes = True

    def get_laser_gcode_filename(self):
        if self.copper_layer == pcbnew.B_Cu:
            filename = "laser_bottom.gcode"
        else:
            filename = "laser_front.gcode"
        return os.path.join(self.user_dir, filename)

    def load(self):
        pass

    def save(self):
        pass
