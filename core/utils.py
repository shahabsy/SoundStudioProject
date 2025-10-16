import sys, os
from core.project_manager import BASE_DIR

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        #base_path = os.path.abspath(".")
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(base_path)
    return os.path.join(base_path, relative_path)

def app_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)