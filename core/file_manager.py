import os

class FileManager:
    @staticmethod
    def create_project_structure(project_path, name):
        full_path = os.path.join(project_path, name)
        os.makedirs(full_path, exist_ok=True)
        os.makedirs(os.path.join(full_path, "audio"))
        os.makedirs(os.path.join(full_path, "metadata"))
        return full_path