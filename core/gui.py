import wx
from wx import Size

from core.settings import PluginConfig

GRID_GAP = 8


class LaserSettingsDialog(wx.Dialog):
    def __init__(self, config, title="Laser Settings"):
        super().__init__(None, title=title)
        self.config = config
        self.ctrls = {}

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        control_box = wx.FlexGridSizer(cols=2, gap=Size(GRID_GAP, GRID_GAP))

        for key, meta in config.FIELDS.items():
            label = wx.StaticText(panel, label=meta["label"] + ":")

            if "choices" in meta:
                choices = list(meta["choices"].values())
                ctrl = wx.Choice(panel, choices=choices)
                current = meta["choices"].get(getattr(config, key), choices[0])
                ctrl.SetStringSelection(current)
            elif meta["type"] == bool:
                ctrl = wx.CheckBox(panel)
                ctrl.SetValue(getattr(config, key))
            elif key == "user_dir":
                hbox = wx.BoxSizer(wx.HORIZONTAL)
                text = wx.TextCtrl(panel, value=getattr(config, key))
                btn = wx.Button(panel, label="...")
                btn.Bind(wx.EVT_BUTTON, lambda evt, c=text: self.on_choose_dir(evt, c))
                hbox.Add(label, flag=wx.ALIGN_CENTER_VERTICAL, border=GRID_GAP)
                hbox.Add(text, flag=wx.EXPAND, border=GRID_GAP)

                control_box.Add(hbox, flag=wx.EXPAND | wx.ALL)
                control_box.Add(btn, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
                self.ctrls[key] = text
                continue
            else:
                ctrl = wx.TextCtrl(panel, value=str(getattr(config, key)))
            control_box.Add(label, flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
            control_box.Add(ctrl, flag=wx.EXPAND)
            self.ctrls[key] = ctrl

        vbox.Add(control_box, flag=wx.EXPAND | wx.ALL, border=GRID_GAP)

        # Кнопки
        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK, "Генерировать")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Выйти")
        hbox_btns.Add(ok_btn, flag=wx.ALL, border=GRID_GAP)
        hbox_btns.Add(cancel_btn, flag=wx.ALL, border=GRID_GAP)
        vbox.Add(hbox_btns, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)
        panel.Layout()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizerAndFit(main_sizer)
        self.Layout()

    def on_choose_dir(self, event, ctrl):
        dialog = wx.DirDialog(self, "Выберите директорию")
        if dialog.ShowModal() == wx.ID_OK:
            ctrl.SetValue(dialog.GetPath())
        dialog.Destroy()

    def apply_changes(self):
        """Сохраняем данные из формы в объект config"""
        for key, meta in self.config.FIELDS.items():
            ctrl = self.ctrls[key]

            if isinstance(ctrl, wx.TextCtrl):
                val = ctrl.GetValue()
                if meta["type"] == int:
                    try:
                        val = int(val)
                    except ValueError:
                        val = meta["default"]
                setattr(self.config, key, val)

            elif isinstance(ctrl, wx.CheckBox):
                setattr(self.config, key, ctrl.GetValue())

            elif isinstance(ctrl, wx.Choice):
                choice_text = ctrl.GetStringSelection()
                rev_map = {v: k for k, v in meta["choices"].items()}
                setattr(self.config, key, rev_map[choice_text])


class PenFrame(wx.Dialog):
    def __init__(self, title):
        super().__init__(None, title=title)
        panel = wx.Panel(self)
        text = wx.StaticText(panel, label="Processing...")
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 0, wx.ALL | wx.CENTER, 10)
        panel.SetSizer(sizer)
        self.SetSize((250, 100))
        self.Show()
        wx.Yield()


class GUI:
    def __init__(self, title="Laser CAM"):
        self.spinner = None
        self.title = title

    def show_spinner(self):
        self.spinner = PenFrame(self.title)

    def destroy_spinner(self):
        self.spinner.Destroy()

    def show_msq(self, message):
        dlg = wx.MessageDialog(None, message, self.title, wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def get_gui_config(self):
        config = PluginConfig()
        config.load_config()

        dlg = LaserSettingsDialog(config, self.title)
        if dlg.ShowModal() == wx.ID_OK:
            dlg.apply_changes()
            config.save_config()
            dlg.Destroy()
            return config
        dlg.Destroy()
        return None
