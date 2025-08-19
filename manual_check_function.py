import wx
from core.gui import GUI
from core.machine import Machine


class MyApp(wx.App):
    def OnInit(self):
        gui = GUI("Laser processor")
        print(gui.get_gui_config())
        return True



if __name__ == '__main__':
    # Тест генератора скорости
    for l in range(12):
        print(l+1, "mm, F:", Machine.get_speed(l+1, 900, 700, 2, 8))


    # app = MyApp()
    # app.MainLoop()
