from django import forms
from django.contrib import admin
from realstockaccount.models import *

# Register your models here.


class RealCashTransferForm(forms.ModelForm):
    class Meta:
        model = RealStockAccountCashTransfer
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        change = self.instance.pk is not None  # Kiểm tra xem có phải là sửa đổi không

        today = timezone.now().date()

        # Kiểm tra quyền
        if change and self.instance.created_at.date() != today:
            raise forms.ValidationError("Bạn không có quyền sửa đổi các bản ghi được tạo ngày trước đó.")

        return cleaned_data
    
class RealStockAccountCashTransferAdmin(admin.ModelAdmin):
    form  = RealCashTransferForm
    list_display = ['date','account', 'formatted_amount','description', 'user_created', 'user_modified', 'created_at']
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

        


admin.site.register(RealStockAccountCashTransfer,RealStockAccountCashTransferAdmin)




class RealBankCashTransferForm(forms.ModelForm):
    class Meta:
        model = RealBankCashTransfer
        fields = '__all__'

    # def clean(self):
    #     cleaned_data = super().clean()
    #     change = self.instance.pk is not None  # Kiểm tra xem có phải là sửa đổi không

    #     today = timezone.now().date()

    #     # Kiểm tra quyền
    #     if change and self.instance.created_at.date() != today:
    #         raise forms.ValidationError("Bạn không có quyền sửa đổi các bản ghi được tạo ngày trước đó.")

    #     return cleaned_data
    
class RealBankCashTransferAdmin(admin.ModelAdmin):
    form  = RealBankCashTransferForm
    list_display = ['account','date', 'formatted_amount','description', 'user_created', 'user_modified', 'created_at']
    readonly_fields = ['user_created', 'user_modified',]
    search_fields = ['account__id','account__name']
    list_filter = ['type',]

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

        


admin.site.register(RealBankCashTransfer,RealBankCashTransferAdmin)


class BankCashTransferForm(forms.ModelForm):
    class Meta:
        model = BankCashTransfer
        fields = '__all__'

class BankCashTransferAdmin(admin.ModelAdmin):
    form  = BankCashTransferForm
    list_display = ['source','date','account','partner', 'formatted_amount','description', 'user_created', 'created_at']
    readonly_fields = ['user_created', 'user_modified','customer_cash_id']
    search_fields = ['account__id','account__name']
    list_filter = ['type','account__name']

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

admin.site.register(BankCashTransfer,BankCashTransferAdmin)

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



class RealStockAccountForm(forms.ModelForm):
    class Meta:
        model = RealStockAccount
        fields = '__all__'


class RealStockAccountAdmin(admin.ModelAdmin):
    list_display = ['partner', 'formatted_total_interest_fee', 'formatted_net_cash_flow_trading', 'formatted_net_cash_flow_operation', 'formatted_net_cash_flow', 'formatted_net_trading_value', 'formatted_cash_balance', 'formatted_market_value', 'formatted_nav']

    def formatted_amount(self, obj):
        return '{:,.0f}'.format(obj.amount)
    
    def formatted_total_interest_fee(self, obj):
        return '{:,.0f}'.format(obj.total_interest_fee)
    
    formatted_total_interest_fee.short_description = 'Tổng phí'

    def formatted_net_cash_flow_trading(self, obj):
        return '{:,.0f}'.format(obj.net_cash_flow_trading)
    formatted_net_cash_flow_trading.short_description = 'Nạp rút tiền ròng giao dịch'

    def formatted_net_cash_flow_operation(self, obj):
        return '{:,.0f}'.format(obj.net_cash_flow_operation)
    formatted_net_cash_flow_operation.short_description = 'Nạp rút tiền ròng bổ sung vốn'

    def formatted_net_cash_flow(self, obj):
        return '{:,.0f}'.format(obj.net_cash_flow)
    formatted_net_cash_flow.short_description = 'Nạp rút tiền ròng'

    def formatted_net_trading_value(self, obj):
        return '{:,.0f}'.format(obj.net_trading_value)
    formatted_net_trading_value.short_description = 'Giao dịch ròng'

    def formatted_cash_balance(self, obj):
        return '{:,.0f}'.format(obj.cash_balance)
    formatted_cash_balance.short_description = 'Số dư tiền'

    def formatted_market_value(self, obj):
        return '{:,.0f}'.format(obj.market_value)
    formatted_market_value.short_description = 'Giá trị thị trường'

    def formatted_nav(self, obj):
        return '{:,.0f}'.format(obj.nav)
    formatted_nav.short_description = 'Tài sản ròng'

admin.site.register(RealStockAccount, RealStockAccountAdmin)