import os

from werkzeug.utils import secure_filename

from .storage import Storage


class LocalStorage(Storage):
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        if not os.path.exists(upload_folder):  # noqa: PTH110
            os.makedirs(upload_folder)  # noqa: PTH103

    def save(self, file, filename):
        filename = secure_filename(filename)
        filepath = os.path.join(self.upload_folder, filename)  # noqa: PTH118
        file.save(filepath)
        return filepath

    def retrieve(self, filename):
        # This would need to be implemented with Flask's send_from_directory
        # For now, we just return the path
        return os.path.join(self.upload_folder, filename)  # noqa: PTH118
