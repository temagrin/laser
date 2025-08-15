import os
import json
import pcbnew


class PluginConfig:
    def __init__(self, plugin_path):
        self.show_preview = False
        self.copper_layer = pcbnew.B_Cu
        self.laser_beam_wide = 100000.0
        self.base_speed = 1000
        self.speed_increment = 200
        self.base_power = 1000
        self.power_decrement = 100
        self.round_um = 2
        self.outer_speed_boost = 0.5
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
            # Загрузка параметров, если они есть в файле
            self.show_preview = data.get("show_preview", self.show_preview)
            # Для copper_layer нужно конвертировать из int (или строки)
            layer = data.get("copper_layer", None)
            if layer is not None:
                if isinstance(layer, int):
                    self.copper_layer = layer
                else:
                    # Если в файле строка, можно конвертировать по имени
                    if layer == "B_Cu":
                        self.copper_layer = pcbnew.B_Cu
                    elif layer == "F_Cu":
                        self.copper_layer = pcbnew.F_Cu

            self.laser_beam_wide = float(data.get("laser_beam_wide", self.laser_beam_wide))
            self.base_speed = int(data.get("base_speed", self.base_speed))
            self.speed_increment = int(data.get("speed_increment", self.speed_increment))
            self.base_power = int(data.get("base_power", self.base_power))
            self.power_decrement = int(data.get("power_decrement", self.power_decrement))
            # round_um был кортежем из одного элемента — исправим на int
            val = data.get("round_um", self.round_um)
            if isinstance(val, list):
                self.round_um = int(val[0])
            else:
                self.round_um = int(val)
            self.outer_speed_boost = float(data.get("outer_speed_boost", self.outer_speed_boost))
            self.user_dir = data.get("user_dir", self.user_dir)
            self.expose_holes = bool(data.get("expose_holes", self.expose_holes))
        except Exception as e:
            print(f"Ошибка при загрузке конфига: {e}")

    def save_config(self):
        data = {
            "show_preview": self.show_preview,
            "copper_layer": self.copper_layer,
            "laser_beam_wide": self.laser_beam_wide,
            "base_speed": self.base_speed,
            "speed_increment": self.speed_increment,
            "base_power": self.base_power,
            "power_decrement": self.power_decrement,
            "round_um": self.round_um,
            "outer_speed_boost": self.outer_speed_boost,
            "user_dir": self.user_dir,
            "expose_holes": self.expose_holes,
        }
        try:
            with open(self.config_file_name, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Ошибка при сохранении конфига: {e}")
