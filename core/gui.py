import wx

from core.settings import PluginConfig


class LaserSettingsDialog(wx.Dialog):
    def __init__(self, config, title="Laser Settings"):
        super().__init__(None, title=title)
        self.config = config
        self.ctrls = {}

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        for key, meta in config.FIELDS.items():
            hbox = wx.BoxSizer(wx.HORIZONTAL)
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
                text = wx.TextCtrl(panel, value=getattr(config, key))
                btn = wx.Button(panel, label="...")
                btn.Bind(wx.EVT_BUTTON, lambda evt, c=text: self.on_choose_dir(evt, c))
                hbox.Add(label, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)
                hbox.Add(text, proportion=1, flag=wx.EXPAND)
                hbox.Add(btn, flag=wx.LEFT, border=5)
                vbox.Add(hbox, flag=wx.EXPAND | wx.ALL, border=5)
                self.ctrls[key] = text
                continue
            else:
                ctrl = wx.TextCtrl(panel, value=str(getattr(config, key)))

            hbox.Add(label, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)
            hbox.Add(ctrl, proportion=1, flag=wx.EXPAND)
            vbox.Add(hbox, flag=wx.EXPAND | wx.ALL, border=5)

            self.ctrls[key] = ctrl

        # Кнопки
        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK, "Генерировать")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Выйти")
        hbox_btns.Add(ok_btn, flag=wx.ALL, border=5)
        hbox_btns.Add(cancel_btn, flag=wx.ALL, border=5)
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
        text = wx.StaticText(panel, label="Работаю...")
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 0, wx.ALL | wx.CENTER, 10)
        panel.SetSizer(sizer)
        self.SetSize((250, 100))
        self.Show()
        wx.Yield()


def show_msq(title, message):
    dlg = wx.MessageDialog(None, message, title, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()


def get_gui_config(title):
    config = PluginConfig()
    config.load_config()

    dlg = LaserSettingsDialog(config, title)
    if dlg.ShowModal() == wx.ID_OK:
        dlg.apply_changes()
        config.save_config()
        dlg.Destroy()
        return config
    dlg.Destroy()
    return None
