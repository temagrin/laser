import wx

from core.gui import get_gui_config


class MyApp(wx.App):
    def OnInit(self):
        print(get_gui_config("Laser processor"))
        return True


if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()

