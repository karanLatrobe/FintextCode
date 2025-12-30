from django.contrib import admin
from .models import ExcelRow

@admin.register(ExcelRow)
class ExcelRowAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "file_id", "row_index")
    list_filter = ("user", "file_id")
    search_fields = ("file_id", "user__username")
