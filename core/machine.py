import math


class Machine:
    @classmethod
    def generate_gcode_from_paths(
            cls,
            inset_levels,
            base_speed=900,  # минимальная скорость (для самых длинных контуров)
            max_speed=1500,  # максимальная скорость (для самых коротких контуров)
            laser_power=255,
            round_um=2,
            skip_min_length=0.05,  # отбрасываем слишком короткие контуры (мм)
            min_contour_length=1.5,  # длина ниже которой уже макс. скорость (мм)
            max_contour_length=15.0,  # длина выше которой уже миним. скорость (мм)
    ):
        nm_to_mm = 1e-6
        scale = 1e-3 * round_um
        gcode = []

        for contour_points in inset_levels:
            last_command = ""
            if len(contour_points) < 2:
                continue

            # --- вычисляем длину контура ---
            length = 0.0
            prev_x, prev_y = contour_points[0]
            first_x, first_y = contour_points[0]

            for x_nm, y_nm in contour_points[1:]:
                x = x_nm
                y = y_nm
                length += math.hypot(x - prev_x, y - prev_y)
                prev_x, prev_y = x, y
            # замыкаем контур

            length += math.hypot(prev_x - first_x, prev_y - first_y)
            length *= nm_to_mm

            # --- фильтрация слишком коротких ---
            if length < skip_min_length:
                continue

            # --- расчет скорости (инвертированная логика) ---
            if length <= min_contour_length:
                speed = max_speed
            elif length >= max_contour_length:
                speed = base_speed
            else:
                # линейная интерполяция от max_speed к base_speed
                ratio = (length - min_contour_length) / (max_contour_length - min_contour_length)
                speed = max_speed - ratio * (max_speed - base_speed)

            # --- генерация G-кода ---
            start_x = round(contour_points[0][0] * nm_to_mm / scale) * scale
            start_y = round(contour_points[0][1] * nm_to_mm / scale) * scale
            gcode.append(f"G0X{start_x:.3f}Y{start_y:.3f}S0")

            first = True
            for x_nm, y_nm in contour_points[1:]:
                x_mm = round(x_nm * nm_to_mm / scale) * scale
                y_mm = round(y_nm * nm_to_mm / scale) * scale
                if first:
                    gcode.append(
                        f"G1X{x_mm:.3f}Y{y_mm:.3f}F{speed:.1f}S{laser_power}"
                    )
                    first = False
                else:
                    new_command = f"X{x_mm:.3f}Y{y_mm:.3f}"
                    if new_command != last_command:
                        gcode.append(f"{new_command}")
                        last_command = f"{new_command}"
            # замыкание контура
            gcode.append(f"X{start_x:.3f}Y{start_y:.3f}")

        return gcode

    @staticmethod
    def save_gcode_to_file(gcode_lines, filename):
        """
        Сохраняет список строк G-code в указанный файл.
        """
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"G21 G17 G90\nG0Z0\nM4\n")
            for line in gcode_lines:
                f.write(line + "\n")
            f.write(f"M5\nG0X0Y0\nM30\n")
