from django.contrib import admin
from .models import *

# Register your models here.
class ClientPartnerInfoAdmin(admin.ModelAdmin):
    model= ClientPartnerInfo
    list_display = ['full_name', 'id', 'rank', 'phone']
    search_fields = ['id','full_name']

admin.site.register(ClientPartnerInfo,ClientPartnerInfoAdmin)