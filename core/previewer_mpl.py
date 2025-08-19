from matplotlib import cm
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon


class Plotter:
    def __init__(self, title):
        self.title = title
        self.frame_polygons = None
        self.frame_path = None

    def plot_inset_paths(self, paths):
        fig, ax = plt.subplots()
        ax.set_aspect('equal', adjustable='box')
        all_x, all_y = [], []
        for figure_idx, figure in enumerate(paths):
            colors = cm.get_cmap('viridis', len(figure))
            for level_idx, contour in enumerate(figure):
                color = colors(level_idx)
                if len(contour) < 3:
                    continue  # пропускаем вырожденные
                poly_patch = MplPolygon(contour, closed=True,
                                        facecolor='none',
                                        edgecolor=color,
                                        linewidth=1)
                ax.add_patch(poly_patch)

                xs, ys = zip(*contour)
                all_x.extend(xs)
                all_y.extend(ys)

        if all_x and all_y:
            padding_x = (max(all_x) - min(all_x)) * 0.05 or 1
            padding_y = (max(all_y) - min(all_y)) * 0.05 or 1
            ax.set_xlim(min(all_x) - padding_x, max(all_x) + padding_x)
            ax.set_ylim(min(all_y) - padding_y, max(all_y) + padding_y)

        ax.grid(True, linestyle='--', alpha=0.5)
        plt.title(self.title)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.show()
        self.frame_path = plt


    def render_preview(self, polygons):
        if not polygons:
            print("Пустая геометрия для отрисовки")
            return

        all_x, all_y = [], []
        for p in polygons:
            minx, miny, maxx, maxy = p.bounds
            all_x.extend([minx, maxx])
            all_y.extend([miny, maxy])

        fig, ax = plt.subplots()
        colors = cm.get_cmap('viridis', len(polygons))

        for index, poly in enumerate(polygons):
            # ===== внешний контур =====
            exterior_coords = list(poly.exterior.coords)
            ax.add_patch(MplPolygon(exterior_coords, closed=True,
                                    facecolor=colors(index), edgecolor='black'))

            # ===== отверстия =====
            for interior in poly.interiors:
                interior_coords = list(interior.coords)
                ax.add_patch(MplPolygon(interior_coords, closed=True,
                                        facecolor='white', edgecolor='black'))

        ax.set_xlim(min(all_x), max(all_x))
        ax.set_ylim(min(all_y), max(all_y))
        ax.set_aspect('equal', adjustable='box')

        plt.title("MultiPolygon preview")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.grid(True)
        plt.show()

        self.frame_polygons = plt

    def destroy_all(self):
        pass

