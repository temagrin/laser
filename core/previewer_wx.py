import wx


class UniversalPathsPanel(wx.Panel):
    def __init__(self, parent, data, is_shapely=False):
        super().__init__(parent)
        self.data = data
        self.is_shapely = is_shapely

        self.SetBackgroundColour(wx.Colour(250, 250, 250))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.on_paint)

        # Собираем все точки для вычисления границ
        all_x, all_y = [], []

        if is_shapely:
            for geom in data:
                polygons = []
                if hasattr(geom, 'geoms'):
                    polygons.extend(geom.geoms)
                else:
                    polygons.append(geom)

                for poly in polygons:
                    minx, miny, maxx, maxy = poly.bounds
                    all_x.extend([minx, maxx])
                    all_y.extend([miny, maxy])
        else:
            for figure in data:
                for contour in figure:
                    if len(contour) < 3:
                        continue
                    xs, ys = zip(*contour)
                    all_x.extend(xs)
                    all_y.extend(ys)

        if all_x and all_y:
            self.min_x = min(all_x)
            self.max_x = max(all_x)
            self.min_y = min(all_y)
            self.max_y = max(all_y)
        else:
            self.min_x = self.min_y = 0
            self.max_x = self.max_y = 1

        padding_x = (self.max_x - self.min_x) * 0.05 or 1
        padding_y = (self.max_y - self.min_y) * 0.05 or 1
        self.min_x -= padding_x
        self.max_x += padding_x
        self.min_y -= padding_y
        self.max_y += padding_y

    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        gc = wx.GraphicsContext.Create(dc)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

        width, height = self.GetSize()
        data_width = self.max_x - self.min_x
        data_height = self.max_y - self.min_y
        scale_x = width / data_width
        scale_y = height / data_height
        scale = min(scale_x, scale_y)

        offset_x = (width - data_width * scale) / 2
        offset_y = (height - data_height * scale) / 2

        self.draw_grid(gc, width, height, scale, offset_x, offset_y)

        if self.is_shapely:
            for idx, geom in enumerate(self.data):
                polygons = []
                if hasattr(geom, 'geoms'):
                    polygons.extend(geom.geoms)
                else:
                    polygons.append(geom)
                color = self.colormap(idx, len(self.data))
                for poly in polygons:
                    exterior_coords = list(poly.exterior.coords)
                    interiors_coords = [list(interior.coords) for interior in poly.interiors]

                    self.draw_polygon(gc,
                                      exterior_coords,
                                      interiors_coords,
                                      edge_color=wx.BLACK,
                                      fill_color=color,
                                      scale=scale,
                                      offset_x=offset_x,
                                      offset_y=offset_y,
                                      bg_color=self.GetBackgroundColour())
        else:
            for figure_idx, figure in enumerate(self.data):
                for level_idx, contour in enumerate(figure):
                    if len(contour) < 3:
                        continue
                    color = self.colormap(level_idx, len(figure))
                    self.draw_polygon(gc, contour, [],
                                      edge_color=color,
                                      fill_color=None,
                                      scale=scale,
                                      offset_x=offset_x,
                                      offset_y=offset_y,
                                      bg_color=self.GetBackgroundColour())

        self.draw_labels(dc, width, height)

    def draw_polygon(self, gc, exterior_pts, interiors_pts_list, edge_color, fill_color, scale, offset_x, offset_y,
                     bg_color):
        # Внешний контур с заливкой
        gc.SetPen(wx.Pen(edge_color, 1))
        if fill_color:
            gc.SetBrush(wx.Brush(fill_color))
        else:
            gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 0)))  # прозрачная заливка

        exterior_screen = [self.to_screen(x, y, scale, offset_x, offset_y) for x, y in exterior_pts]
        path = gc.CreatePath()
        path.MoveToPoint(*exterior_screen[0])
        for pt in exterior_screen[1:]:
            path.AddLineToPoint(*pt)
        path.CloseSubpath()
        gc.DrawPath(path)

        # Отверстия (дыры) цветом фона
        gc.SetPen(wx.Pen(edge_color, 1))
        gc.SetBrush(wx.Brush(bg_color))

        for interior_pts in interiors_pts_list:
            interior_screen = [self.to_screen(x, y, scale, offset_x, offset_y) for x, y in interior_pts]
            path_int = gc.CreatePath()
            path_int.MoveToPoint(*interior_screen[0])
            for pt in interior_screen[1:]:
                path_int.AddLineToPoint(*pt)
            path_int.CloseSubpath()
            gc.DrawPath(path_int)

    def to_screen(self, x, y, scale, offset_x, offset_y):
        sx = offset_x + (x - self.min_x) * scale
        sy = offset_y + (self.max_y - y) * scale  # инверсия Y для wx
        return (sx, sy)

    def colormap(self, idx, n):
        viridis_colors = [
            (68, 1, 84), (72, 35, 116), (64, 67, 135), (52, 94, 141),
            (41, 120, 142), (32, 144, 140), (34, 167, 132), (68, 190, 112),
            (121, 209, 81), (189, 222, 38), (253, 231, 37)
        ]
        i = int(idx * (len(viridis_colors) - 1) / max(1, n - 1))
        r, g, b = viridis_colors[i]
        return wx.Colour(r, g, b)

    def draw_grid(self, gc, width, height, scale, offset_x, offset_y):
        gc.SetPen(wx.Pen(wx.Colour(100, 100, 100), 1, style=wx.PENSTYLE_SHORT_DASH))
        step = 50

        x = offset_x
        while x < width:
            gc.StrokeLine(x, 0, x, height)
            x += step

        y = offset_y
        while y < height:
            gc.StrokeLine(0, y, width, y)
            y += step

    def draw_labels(self, dc, width, height):
        dc.SetTextForeground(wx.BLACK)
        font = dc.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetPointSize(12)
        dc.SetFont(font)
        dc.DrawText("Paths Preview", 10, 10)

        font.SetWeight(wx.FONTWEIGHT_NORMAL)
        font.SetPointSize(10)
        dc.SetFont(font)
        dc.DrawText("X", width - 20, height - 20)
        dc.DrawText("Y", 10, 30)


class UniversalPathsFrame(wx.Frame):
    def __init__(self, data, title, is_shapely=False):
        super().__init__(None, title=title, size=(800, 600))
        UniversalPathsPanel(self, data, is_shapely)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Show()
        wx.Yield()

    def on_close(self, event):
        self.Destroy()


class Plotter:
    def __init__(self, title):
        self.title = title
        self.frame_polygons = None
        self.frame_path = None

    def plot_inset_paths(self, paths):
        self.frame_path = UniversalPathsFrame(paths, title=f"{self.title} paths", is_shapely=False)

    def render_preview(self, polygons):
        self.frame_polygons = UniversalPathsFrame(polygons, title=f"{self.title} polygons", is_shapely=True)

    def destroy_all(self):
        if self.frame_polygons:
            self.frame_polygons.Destroy()
        if self.frame_path:
            self.frame_path.Destroy()

