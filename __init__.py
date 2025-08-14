import os
import sys

ap_dir = os.path.dirname(os.path.abspath(__file__))
if ap_dir not in sys.path:
    sys.path.insert(0, ap_dir)

from laser_action import Laser
Laser().register()