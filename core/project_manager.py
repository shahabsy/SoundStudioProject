import os, json
from PyQt5.QtCore import QStringListModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECENT_PROJECTS_PATH = os.path.join(DATA_DIR, "recent_projects.json")

class ProjectManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(RECENT_PROJECTS_PATH):
            with open(RECENT_PROJECTS_PATH, 'w') as f:
                json.dump([], f)
        
        self.projects = self.load_recent_projects()
    
    def load_recent_projects(self):
        if os.path.exists(RECENT_PROJECTS_PATH):
            with open(RECENT_PROJECTS_PATH, "r") as f:
                return json.load(f)
        return []
    
    def get_recent_projects(self):
        with open(RECENT_PROJECTS_PATH, 'r') as f:
            return json.load(f)

    def add_to_recent_project(self, folder):
        projects = self.get_recent_projects()

        if folder in projects:
            projects.remove(folder)       
        projects.insert(0, folder)
        with open(RECENT_PROJECTS_PATH, 'w') as f:
            json.dump(projects[:10], f) # save up to 10 projects
    
    def create_project(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        self.add_to_recent_project(folder)
    
    #def save_recent_projects(self):
    def save_recent_projects(self, projects):
        with open(RECENT_PROJECTS_PATH, "w") as f:
            json.dump(projects[:10], f, indent=4)
        self.projects = projects

    def get_list_model(self, parent=None):
        model = QStringListModel()
        model.setStringList(self.projects)
        return model
    def clear_recent_projects(self):
        if os.path.exists(RECENT_PROJECTS_PATH):
            with open(RECENT_PROJECTS_PATH, 'w') as f:
                json.dump([], f)
    
    def remove_from_recent_projects(self, folder):
        projects = self.get_recent_projects()
        if folder in projects:
            projects.remove(folder)
            with open(RECENT_PROJECTS_PATH, 'w') as f:
                json.dump(projects[:10], f)
        self.projects = projects