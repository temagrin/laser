import os
import json


class PluginConfig:
    COPPER_LAYERS = {0: "F.Cu", 2: "B.Cu"}
    FIELDS = {
        "user_dir":             {"default": "/home/user", "type": str, "label": "Рабочая директория"},
        "laser_beam_wide":      {"default": 25000, "type": int, "label": "Диаметр лазерного луча (нм)"},
        "laser_power":          {"default": 255, "type": int, "label": "Мощность лазера"},
        "copper_layer":         {"default": 2, "type": int, "label": "Слой меди", "choices": COPPER_LAYERS},
        "base_speed":           {"default": 900, "type": int, "label": "Базовая скорость (F)"},
        "short_speed":          {"default": 750, "type": int, "label": "Скорость коротких участков (F)"},
        "arc_segments":         {"default": 32, "type": int, "label": "Сегментация окружностей"},
        "round_um":             {"default": 2, "type": int, "label": "Округление координат (мкм)"},
        "max_contour_length":   {"default": 15, "type": int, "label": "Макс. длина контура (мм)"},
        "min_contour_length":   {"default": 1, "type": int, "label": "Мин. длина контура (мм)"},
        "show_preview":         {"default": False, "type": bool, "label": "Предпросмотр платы"},
        "show_paths":           {"default": False, "type": bool, "label": "Показать пути"},
        "tent_th":              {"default": False, "type": bool, "label": "Тентовать TH"},
        "tent_via":             {"default": False, "type": bool, "label": "Тентовать VIA"},
    }

    def __init__(self):
        self.max_contour_length = 15.0
        self.min_contour_length = 1.2
        self.skip_min_length = 0.05
        self.arc_segments = 32
        self.tent_th = False
        self.tent_via = False
        self.show_preview = False
        self.show_paths = False
        self.copper_layer = 0
        self.laser_beam_wide = 25000
        self.base_speed = 900
        self.short_speed = 750
        self.laser_power = 255
        self.round_um = 2
        self.user_dir = "/home/user"
        self._config_file_name = os.path.join(os.path.dirname(__file__), "config.json")

        for key, meta in self.FIELDS.items():
            setattr(self, key, meta["default"])

    def load_config(self):
        if not os.path.isfile(self._config_file_name):
            return
        try:
            with open(self._config_file_name, "r") as f:
                data = json.load(f)

            for key, meta in self.FIELDS.items():
                if key in data:
                    setattr(self, key, meta["type"](data[key]))

        except Exception as e:
            print(f"Ошибка при загрузке конфига: {e}")

    def save_config(self):
        data = {key: getattr(self, key) for key in self.FIELDS.keys()}
        try:
            with open(self._config_file_name, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Ошибка при сохранении конфига: {e}")

    def get_laser_gcode_filename(self):
        filename = "laser_bottom.gcode" if self.copper_layer == 2 else "laser_front.gcode"
        return os.path.join(self.user_dir, filename)
