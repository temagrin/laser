from core.tools import get_path_length


class Machine:
    @staticmethod
    def get_speed(length, base_speed, short_speed, min_contour_length, max_contour_length):
        if length <= min_contour_length:
            speed = short_speed
        elif length >= max_contour_length:
            speed = base_speed
        else:
            ratio = (length - min_contour_length) / (max_contour_length - min_contour_length)
            speed = base_speed - ratio * (base_speed - short_speed)
        return int(speed)

    @classmethod
    def generate_gcode_to_file(
            cls,
            paths,
            filename,
            base_speed=900,
            short_speed=750,
            laser_power=255,
            round_um=2,
            min_contour_length=1.5,
            max_contour_length=15.0,
    ):
        nm_to_mm = 1e-6
        scale = 1e-3 * round_um
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"G21 G17 G90\nG0Z0\nM4\n")
            for inset_levels in paths:
                for contour_points in inset_levels:
                    last_command = ""
                    if len(contour_points) < 2:
                        continue

                    length = get_path_length(contour_points)
                    length *= nm_to_mm

                    speed = cls.get_speed(length, base_speed, short_speed, min_contour_length, max_contour_length)

                    # --- генерация G-кода ---
                    start_x = round(contour_points[0][0] * nm_to_mm / scale) * scale
                    start_y = round(contour_points[0][1] * nm_to_mm / scale) * scale
                    f.write(f"G0X{start_x:.3f}Y{start_y:.3f}S0\n")
                    first = True
                    for x_nm, y_nm in contour_points[1:]:
                        x_mm = round(x_nm * nm_to_mm / scale) * scale
                        y_mm = round(y_nm * nm_to_mm / scale) * scale
                        if first:
                            f.write(f"G1X{x_mm:.3f}Y{y_mm:.3f}F{speed:.1f}S{laser_power}\n")
                            first = False
                        else:
                            new_command = f"X{x_mm:.3f}Y{y_mm:.3f}"
                            if new_command != last_command:
                                f.write(f"{new_command}\n")
                                last_command = f"{new_command}"
                    new_command = f"X{start_x:.3f}Y{start_y:.3f}"
                    if new_command != last_command:
                        f.write(f"{new_command}\n")
            f.write(f"M5\nG0X0Y0\nM30\n")
        return
