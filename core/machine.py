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

        def to_mm(value):
            return round(value * nm_to_mm / scale) * scale

        def write_command(f_handle, command, last_cmd):
            if command != last_cmd:
                f_handle.write(command + "\n")
                return command
            return last_cmd

        def cmd_iterator():
            for inset_levels in paths:
                for contour_points in inset_levels:
                    if len(contour_points) < 2:
                        continue

                    length = get_path_length(contour_points) * nm_to_mm
                    speed = cls.get_speed(length, base_speed, short_speed, min_contour_length, max_contour_length)

                    start_x = to_mm(contour_points[0][0])
                    start_y = to_mm(contour_points[0][1])
                    yield f"G0X{start_x:.3f}Y{start_y:.3f}S0"
                    first_point = True
                    for x_nm, y_nm in contour_points[1:]:
                        x_mm = to_mm(x_nm)
                        y_mm = to_mm(y_nm)
                        if first_point:
                            first_point = False
                            yield f"G1X{x_mm:.3f}Y{y_mm:.3f}F{speed}S{laser_power}"
                        else:
                            yield f"X{x_mm:.3f}Y{y_mm:.3f}"
                    if not first_point:
                        yield f"G1X{start_x:.3f}Y{start_y:.3f}"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("G21 G17 G90\nG0Z0\nM4\n")
            last_command = ""
            for cmd in cmd_iterator():
                last_command = write_command(f, cmd, last_command)
            f.write("M5\nG0X0Y0\nM30\n")
