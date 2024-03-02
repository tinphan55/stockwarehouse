from django.contrib import admin
from .models import *
from django import forms
from django.utils.html import format_html
# Register your models here.

admin.site.register(PartnerInfoProxy)

class AccountPartnerAdmin(admin.ModelAdmin):
    model= AccountPartner
    ordering = ['-nav']
    list_display = ['account','partner', 'id', 'formatted_cash_balance', 'formatted_interest_cash_balance', 'formatted_market_value', 'formatted_nav', 'margin_ratio','formatted_excess_equity','formatted_total_temporarily_pl', 'custom_status_display']
    fieldsets = [
        ('Thông tin cơ bản', {'fields': ['account','partner','description']}),
        ('Trạng thái tài khoản', {'fields': ['cash_balance', 'interest_cash_balance','advance_cash_balance','net_cash_flow','net_trading_value','market_value','nav','initial_margin_requirement','margin_ratio','excess_equity','custom_status_display','milestone_date_lated']}),
        ('Thông tin lãi và phí ứng', {'fields': ['total_loan_interest','total_interest_paid','total_temporarily_interest','total_advance_fee','total_advance_fee_paid','total_temporarily_advance_fee']}),
        ('Hiệu quả đầu tư', {'fields': ['total_pl','total_closed_pl','total_temporarily_pl',]}),
        ('Thành phần số dư tiền tính lãi', {'fields': ['cash_t0','cash_t1','cash_t2','total_buy_trading_value']}),
    ]
    readonly_fields = ['cash_balance', 'market_value', 'nav', 'margin_ratio', 'excess_equity','initial_margin_requirement', 'net_cash_flow', 'net_trading_value', 'custom_status_display','cash_t2','cash_t1',
                       'excess_equity', 'interest_cash_balance' , 'total_loan_interest','total_interest_paid','total_temporarily_interest','total_pl','total_closed_pl','total_temporarily_pl', 
                       'cash_t0','total_buy_trading_value','milestone_date_lated','advance_cash_balance','total_advance_fee','total_advance_fee_paid','total_temporarily_advance_fee',
                       'account','partner'
                       ]
    search_fields = ['id','account__name']
    list_filter = ['partner__name','account__name',]
    
    def has_add_permission(self, request):
        # Return False to disable the "Add" button
        return False
    

    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

    def formatted_number(self, value):
        # Format number with commas as thousand separators and no decimal places
        return '{:,.0f}'.format(value)

    def formatted_cash_balance(self, obj):
        return self.formatted_number(obj.cash_balance)
    def formatted_excess_equity(self, obj):
        return self.formatted_number(obj.excess_equity)

    def formatted_interest_cash_balance(self, obj):
        return self.formatted_number(obj.interest_cash_balance)

    def formatted_market_value(self, obj):
        return self.formatted_number(obj.market_value)

    def formatted_nav(self, obj):
        return self.formatted_number(obj.nav)

    def formatted_margin_ratio(self, obj):
        return self.formatted_number(obj.margin_ratio)


    def formatted_total_temporarily_pl(self, obj):
        return self.formatted_number(obj.total_temporarily_pl)
    # Add other formatted_* methods for other numeric fields


    def interest_payments(self, obj):
        # Display a custom button in the admin list view with arrow formatting
        icon = 'fa-check' if obj.market_value == 0 and obj.total_temporarily_interest != 0 else 'fa-times'
        color = 'green' if obj.market_value == 0 and obj.total_temporarily_interest != 0 else 'gray'
        background_color = '#77cd8b' if color == 'green' else 'white'
        return format_html('<div style="text-align: center; width: 25px; margin: 0 auto; background-color: {0}; border: 1px solid {1}; padding: 5px; border-radius: 5px;"><i class="fas {2}" style="color: {3}; font-size: 12px;"></i></div>', background_color, color, icon, color)

    
    formatted_cash_balance.short_description = 'Số dư tiền'
    formatted_interest_cash_balance.short_description = 'Số dư tính lãi'
    formatted_market_value.short_description = 'Giá trị thị trường'
    formatted_nav.short_description = 'Tài sản ròng'
    formatted_margin_ratio.short_description = 'Tỷ lệ kí quỹ'
    formatted_excess_equity.short_description = 'Dư kí quỹ'
    formatted_total_temporarily_pl.short_description = 'Tổng lãi lỗ'

    def custom_status_display(self, obj):
        if obj.status:
            # Thêm HTML cho màu sắc dựa trên điều kiện
            color = 'red' if 'giải chấp' in obj.status.lower() else 'green'
            # Thêm <br> để xuống dòng
            return format_html('<span style="color: {};">{}</span><br>', color, obj.status)
        return format_html('<span></span>')  # Trả về một span trống nếu status không tồn tại

    custom_status_display.short_description = 'Trạng thái'


admin.site.register(AccountPartner,AccountPartnerAdmin)

class TransactionPartnerForm(forms.ModelForm):
    class Meta:
        model = TransactionPartner
        exclude = ['user_created', 'user_modified']

class TransationPartnerAdmin(admin.ModelAdmin):
    form = TransactionPartnerForm
    list_display_links = ['stock',]
    list_display = ['account','partner','date','stock','position','formatted_price','formatted_qty','formatted_net_total_value','created_at','user_created','formatted_transaction_fee','formatted_tax']
    readonly_fields = ['account','partner', 'date', 'stock', 'position', 'price', 'qty','user_created','user_modified','transaction_fee','tax','total_value','net_total_value']
    fieldsets = (
        ('Thông tin giao dịch', {
            'fields': ('account','partner', 'date', 'stock', 'position', 'price', 'qty')
        }),
       
    )
    def has_add_permission(self, request):
        # Return False to disable the "Add" button
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    
    search_fields = ['account__id','account__name','stock__stock']
    list_filter = ['account__name',]

    def formatted_number(self, value):
        # Format number with commas as thousand separators and no decimal places
        return '{:,.0f}'.format(value)
    
    def formatted_price(self, obj):
        return self.formatted_number(obj.price)
    def formatted_tax(self, obj):
        return self.formatted_number(obj.tax)
    
    def formatted_transaction_fee(self, obj):
        return self.formatted_number(obj.transaction_fee)
    
    def formatted_qty(self, obj):
        return self.formatted_number(obj.qty)
    
    def formatted_net_total_value(self, obj):
        return self.formatted_number(obj.net_total_value)

    # Add other formatted_* methods for other numeric fields

    formatted_transaction_fee.short_description = 'Phí giao dịch'
    formatted_tax.short_description = 'Thuế'
    formatted_price.short_description = 'Giá'
    formatted_qty.short_description = 'Khối lượng'
    formatted_net_total_value.short_description = 'Giá trị giao dịch ròng'

admin.site.register(TransactionPartner,TransationPartnerAdmin)

class PortfolioPartnerAdmin(admin.ModelAdmin):
    model = PortfolioPartner
    list_display = ['account', 'stock', 'formatted_market_price', 'formatted_avg_price', 'formatted_on_hold', 'formatted_receiving_t1', 'formatted_receiving_t2', 'formatted_profit', 'percent_profit', 'formatted_sum_stock']
    readonly_fields = ['account','stock','market_price','avg_price','on_hold','receiving_t1','receiving_t2','profit','percent_profit', 'sum_stock', 'market_value']
    search_fields = ['stock','account__id','account__name']
    list_filter = ['account__partner__name','account__account',]
    
    # def get_queryset(self, request):
    #     # Chỉ trả về các bản ghi có sum_stock > 0
    #     return super().get_queryset(request).filter(sum_stock__gt=0)

    def formatted_number(self, value):
        # Format number with commas as thousand separators and no decimal places
        return '{:,.0f}'.format(value)

    def formatted_market_price(self, obj):
        return self.formatted_number(obj.market_price)

    def formatted_avg_price(self, obj):
        return self.formatted_number(obj.avg_price)

    def formatted_on_hold(self, obj):
        return self.formatted_number(obj.on_hold)

    def formatted_receiving_t1(self, obj):
        return self.formatted_number(obj.receiving_t1)

    def formatted_receiving_t2(self, obj):
        return self.formatted_number(obj.receiving_t2)

    def formatted_profit(self, obj):
        return self.formatted_number(obj.profit)


    def formatted_sum_stock(self, obj):
        return self.formatted_number(obj.sum_stock)

    formatted_market_price.short_description = 'Giá thị trường'
    formatted_avg_price.short_description = 'Giá TB'
    formatted_on_hold.short_description = 'Khả dụng'
    formatted_receiving_t1.short_description = 'Chờ về T+1'
    formatted_receiving_t2.short_description = 'Chờ về T+2'
    formatted_profit.short_description = 'Lợi nhuận'
    formatted_sum_stock.short_description = 'Tổng cổ phiếu'

    def has_add_permission(self, request):
        # Return False to disable the "Add" button
        return False
    
admin.site.register(PortfolioPartner,PortfolioPartnerAdmin)


class CashTransferPartnerForm(forms.ModelForm):
    class Meta:
        model = CashTransferPartner
        exclude = ['user_created', 'user_modified']

class CashTransferPartnerAdmin(admin.ModelAdmin):
    form  = CashTransferPartnerForm
    list_display = ['account', 'date', 'formatted_amount', 'user_created', 'user_modified', 'created_at']
    readonly_fields = ['user_created', 'user_modified']
    search_fields = ['account__id','account__name']
    # list_filter = ['account__name',]

    def has_add_permission(self, request):
        # Return False to disable the "Add" button
        return False
    

    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def formatted_amount(self, obj):
        return '{:,.0f}'.format(obj.amount)
    
    formatted_amount.short_description = 'Số tiền'
    
admin.site.register(CashTransferPartner,CashTransferPartnerAdmin)

