from django import forms
from django.contrib import admin
from realstockaccount.models import *

# Register your models here.
class RealCashTransferForm(forms.ModelForm):
    class Meta:
        model = RealCashTransfer
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        change = self.instance.pk is not None  # Kiểm tra xem có phải là sửa đổi không

        today = timezone.now().date()

        # Kiểm tra quyền
        if change and self.instance.created_at.date() != today:
            raise forms.ValidationError("Bạn không có quyền sửa đổi các bản ghi được tạo ngày trước đó.")

        return cleaned_data
    
class RealCashTransferAdmin(admin.ModelAdmin):
    form  = RealCashTransferForm
    list_display = ['date', 'formatted_amount','description', 'user_created', 'user_modified', 'created_at']
    readonly_fields = ['user_created', 'user_modified']
    search_fields = ['account__id','account__name']

    def formatted_amount(self, obj):
        return '{:,.0f}'.format(obj.amount)

    formatted_amount.short_description = 'Số tiền'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Kiểm tra xem có phải là tạo mới hay không
            obj.user_created = request.user
         # Check if the record is being edited
        else:
            obj.user_modified = request.user.username
                
        super().save_model(request, obj, form, change)

        


admin.site.register(RealCashTransfer,RealCashTransferAdmin)


class RealTradingPowerForm(forms.ModelForm):
    class Meta:
        model = RealTradingPower
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        change = self.instance.pk is not None  # Kiểm tra xem có phải là sửa đổi không

        today = timezone.now().date()

        # Kiểm tra quyền
        if change and self.instance.created_at.date() != today:
            raise forms.ValidationError("Bạn không có quyền sửa đổi các bản ghi được tạo ngày trước đó.")

        return cleaned_data

class RealTradingPowerAdmin(admin.ModelAdmin):
    form  = RealTradingPowerForm
    list_display = ['date', 'formatted_min_amount','formatted_max_amount','description', 'user_created', 'user_modified', 'created_at']
    readonly_fields = ['user_created', 'user_modified']
    search_fields = ['account__id','account__name']

    def formatted_min_amount(self, obj):
        return '{:,.0f}'.format(obj.min_amount)

    formatted_min_amount.short_description = 'Sức mua tối thiểu'

    def formatted_max_amount(self, obj):
        return '{:,.0f}'.format(obj.max_amount)

    formatted_max_amount.short_description = 'sức mua tối đa'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Kiểm tra xem có phải là tạo mới hay không
            obj.user_created = request.user
         # Check if the record is being edited
        else:
            obj.user_modified = request.user.username
                
        super().save_model(request, obj, form, change)

        


admin.site.register(RealTradingPower,RealTradingPowerAdmin)