from django.db import models
from django.contrib.auth.models import User

class ExcelRow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file_id = models.CharField(max_length=100)   # unique ID
    row_index = models.IntegerField()
    data = models.JSONField()                    # Entire row stored as JSON

    def __str__(self):
        return f"{self.user} - {self.file_id} - {self.row_index}"
