import wx
from core.gui import GUI


class MyApp(wx.App):
    def OnInit(self):
        gui = GUI("Laser processor")
        print(gui.get_gui_config())
        return True


if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()
