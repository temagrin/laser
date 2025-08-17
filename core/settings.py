import os
import json
import pcbnew


class PluginConfig:
    def __init__(self, plugin_path):
        self.show_preview = True
        self.show_preview_path = False
        self.copper_layer = pcbnew.B_Cu
        self.laser_beam_wide = 15000
        self.base_speed = 900
        self.short_speed = 750
        self.laser_power = 255
        self.round_um = 2
        self.config_file_name = os.path.join(plugin_path, "config.json")
        self.user_dir = "/home/user"
        self.expose_holes = True

    def get_laser_gcode_filename(self):
        if self.copper_layer == pcbnew.B_Cu:
            filename = "laser_bottom.gcode"
        else:
            filename = "laser_front.gcode"
        return os.path.join(self.user_dir, filename)

    def load_config(self):
        if not os.path.isfile(self.config_file_name):
            return  # Файл не найден — остаются значения по умолчанию
        try:
            with open(self.config_file_name, "r") as f:
                data = json.load(f)
            self.show_preview = data.get("show_preview", self.show_preview)
            self.show_preview_path = data.get("show_preview_path", self.show_preview_path)
            layer = data.get("copper_layer", None)
            if layer is not None:
                if isinstance(layer, int):
                    self.copper_layer = layer
                else:
                    if layer == "B_Cu":
                        self.copper_layer = pcbnew.B_Cu
                    elif layer == "F_Cu":
                        self.copper_layer = pcbnew.F_Cu

            self.laser_beam_wide = int(data.get("laser_beam_wide", self.laser_beam_wide))
            self.base_speed = int(data.get("base_speed", self.base_speed))
            self.short_speed = int(data.get("short_speed", self.short_speed))
            self.laser_power = int(data.get("laser_power", self.laser_power))
            self.round_um = int(data.get("round_um", self.round_um))
            self.user_dir = data.get("user_dir", self.user_dir)
            self.expose_holes = bool(data.get("expose_holes", self.expose_holes))
        except Exception as e:
            print(f"Ошибка при загрузке конфига: {e}")

    def save_config(self):
        data = {
            "show_preview": self.show_preview,
            "show_preview_path": self.show_preview_path,
            "copper_layer": self.copper_layer,
            "laser_beam_wide": self.laser_beam_wide,
            "base_speed": self.base_speed,
            "short_speed": self.short_speed,
            "laser_power": self.laser_power,
            "round_um": self.round_um,
            "user_dir": self.user_dir,
            "expose_holes": self.expose_holes,
        }
        try:
            with open(self.config_file_name, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Ошибка при сохранении конфига: {e}")
