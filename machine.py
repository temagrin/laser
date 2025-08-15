import math


class Machine:
    @staticmethod
    def sort_paths_nearest(contours):
        if not contours:
            return []
        remaining = contours[:]
        sorted_contours = []
        current = remaining.pop(0)
        sorted_contours.append(current)
        current_end = current[-1]

        while remaining:
            min_dist = float("inf")
            min_idx = 0
            reverse_needed = False

            for i, contour in enumerate(remaining):
                start_pt = contour[0]
                end_pt = contour[-1]
                dist_start = math.hypot(start_pt[0] - current_end[0],
                                        start_pt[1] - current_end[1])
                dist_end = math.hypot(end_pt[0] - current_end[0],
                                      end_pt[1] - current_end[1])
                if dist_start < min_dist:
                    min_dist = dist_start
                    min_idx = i
                    reverse_needed = False
                if dist_end < min_dist:
                    min_dist = dist_end
                    min_idx = i
                    reverse_needed = True

            next_contour = remaining.pop(min_idx)
            if reverse_needed:
                next_contour.reverse()
            sorted_contours.append(next_contour)
            current_end = sorted_contours[-1][-1]

        return sorted_contours

    @classmethod
    def generate_gcode_from_paths(
            cls,
            inset_levels,
            base_speed=1000,
            speed_increment=200,
            base_power=1000,
            power_decrement=100,
            round_um=2,
            outer_speed_boost=0.5
    ):
        """
        Генерирует G-code для лазерной заливки с:
          - повышением скорости в плотных зонах (глубокие offset'ы)
          - внешние контуры тоже быстрее, чем базовая скорость
          - сортировка контуров внутри уровня по принципу ближайшего соседа
            и автоматическим разворотом для минимизации холостого хода.

        :param inset_levels: [[[ (x_nm, y_nm), ...], ...], ...] — пути по уровням (нм)
        :param base_speed: базовая (минимальная) скорость, мм/мин
        :param speed_increment: прибавка при переходе к более плотному уровню
        :param base_power: мощность лазера на первом уровне
        :param power_decrement: насколько уменьшать мощность на каждый уровень
        :param round_um: округление координат, мкм (1 мкм = 0.001 мм)
        :param outer_speed_boost: множитель прироста скорости для внешнего контура
        """
        nm_to_mm = 1e-6
        scale = 1e-3 * round_um

        # --- начало формирования G-кода ---
        gcode = [
            "G21 ; set units to mm",
            "G90 ; absolute positioning",
            "M5 ; laser off"
        ]

        for level_idx, contours in enumerate(inset_levels):
            # сортируем в оптимальном порядке
            sorted_contours = cls.sort_paths_nearest(contours)

            # вычисляем скорость
            if level_idx == 0:
                speed = base_speed + speed_increment * outer_speed_boost
            else:
                speed = base_speed + speed_increment * level_idx

            power = max(base_power - power_decrement * level_idx, 0)
            gcode.append(f"(Level {level_idx}, Speed {speed} mm/min, Power {power})")

            for contour in sorted_contours:
                if len(contour) < 2:
                    continue

                # стартовая точка (округление и перевод)
                start_x = round(contour[0][0] * nm_to_mm / scale) * scale
                start_y = round(contour[0][1] * nm_to_mm / scale) * scale

                gcode.append("M5 ; laser off")
                gcode.append(f"G0 X{start_x:.3f} Y{start_y:.3f} F{speed}")
                gcode.append(f"M3 S{power}")

                # основной путь
                for x_nm, y_nm in contour[1:]:
                    x_mm = round(x_nm * nm_to_mm / scale) * scale
                    y_mm = round(y_nm * nm_to_mm / scale) * scale
                    gcode.append(f"G1 X{x_mm:.3f} Y{y_mm:.3f} F{speed}")

                # замыкание
                gcode.append(f"G1 X{start_x:.3f} Y{start_y:.3f} F{speed}")
                gcode.append("M5 ; laser off")

        gcode.append("M5 ; laser off")
        gcode.append("G0 X0 Y0 ; home")

        return gcode

    @staticmethod
    def save_gcode_to_file(gcode_lines, filename):
        """
        Сохраняет список строк G-code в указанный файл.
        """
        with open(filename, "w", encoding="utf-8") as f:
            for line in gcode_lines:
                f.write(line + "\n")

