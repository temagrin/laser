class Machine:
    @classmethod
    def generate_gcode_from_paths(
            cls,
            inset_levels,
            base_speed=900,
            max_speed=1500,
            speed_increment=200,
            laser_power=255,
            round_um=2,
    ):
        nm_to_mm = 1e-6
        scale = 1e-3 * round_um
        gcode = []

        for level_idx, contours in enumerate(inset_levels):
            speed = base_speed + (speed_increment * level_idx)
            if speed > max_speed:
                speed = max_speed
            for contour in contours:
                if len(contour) < 2:
                    continue
                start_x = round(contour[0][0] * nm_to_mm / scale) * scale
                start_y = round(contour[0][1] * nm_to_mm / scale) * scale
                gcode.append(f"G0X{start_x:.3f}Y{start_y:.3f}S0")
                first = True
                for x_nm, y_nm in contour[1:]:
                    x_mm = round(x_nm * nm_to_mm / scale) * scale
                    y_mm = round(y_nm * nm_to_mm / scale) * scale
                    if first:
                        gcode.append(f"G1X{x_mm:.3f}Y{y_mm:.3f}F{speed}S{laser_power}")
                    else:
                        gcode.append(f"X{x_mm:.3f}Y{y_mm:.3f}")
                    first = False
                # замыкание
                gcode.append(f"X{start_x:.3f}Y{start_y:.3f}")
        return gcode

    @staticmethod
    def save_gcode_to_file(gcode_lines, filename, laser_power):
        """
        Сохраняет список строк G-code в указанный файл.
        """
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"G21 G17 G90\nG0Z0\nM4\n")
            for line in gcode_lines:
                f.write(line + "\n")
            f.write(f"M5\nG0X0Y0\nM30\n")
