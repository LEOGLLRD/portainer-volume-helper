import os

from django.db import models


class FileNode(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)  # 'file' ou 'folder'
    full_path = models.CharField(max_length=1024, unique=True)  # Chemin complet
    def __str__(self):
        return self.name

    def extension(self):
        name, ext = os.path.splitext(self.name)[1]
        print(name)
        print(ext)
        return ext
