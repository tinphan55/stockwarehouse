from django.contrib import admin
from .models import *

# Register your models here.
class ClientPartnerInfoAdmin(admin.ModelAdmin):
    model= ClientPartnerInfo
    list_display = ['full_name', 'id', 'rank', 'phone','commission']
    search_fields = ['id','full_name']

admin.site.register(ClientPartnerInfo,ClientPartnerInfoAdmin)

class ClientPartnerCommissionAdmin(admin.ModelAdmin):
    model= ClientPartnerCommission
    list_display = ('cp', 'month_year_str', 'month_year', 'user_created', 'user_modified', 'total_value', 'trading_fee_spreads', 'commission_back', 'total_revenue', 'total_commission')

admin.site.register(ClientPartnerCommission, ClientPartnerCommissionAdmin)