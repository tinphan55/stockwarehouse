from django.contrib import admin
from .models import *
from django.contrib.humanize.templatetags.humanize import intcomma
from django.contrib import messages
from django.utils import timezone
from django import forms
from django.core.exceptions import ValidationError
from realstockaccount.models import *
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect


# Register your models here.



def real_min_power(date): 
    value = RealTradingPower.objects.filter(date = date).first()
    if value:
        value_trading  =value.min_amount
    else:
        value_trading = 0
    return value_trading
    
def real_max_power(date):   
    value = RealTradingPower.objects.filter(date = date).first()
    if value:
        value_trading  =value.max_amount
    else:
        value_trading = 0
    return value_trading
class AccountAdmin(admin.ModelAdmin):
    model= Account
    ordering = ['-nav']
    list_display = ['name', 'id', 'formatted_cash_balance', 'formatted_interest_cash_balance', 'formatted_market_value', 'formatted_nav', 'margin_ratio','formatted_excess_equity','formatted_total_temporarily_pl', 'status','interest_payments']
    fieldsets = [
        ('Thông tin cơ bản', {'fields': ['name','cpd','user_created','description']}),
        ('Biểu phí tài khoản', {'fields': ['interest_fee', 'transaction_fee', 'tax','credit_limit']}),
        ('Trạng thái tài khoản', {'fields': ['cash_balance', 'interest_cash_balance','net_cash_flow','net_trading_value','market_value','nav','initial_margin_requirement','margin_ratio','excess_equity',]}),
        ('Thông tin lãi', {'fields': ['total_loan_interest','total_interest_paid','total_temporarily_interest']}),
        ('Hiệu quả đầu tư', {'fields': ['total_pl','total_closed_pl','total_temporarily_pl']}),
        ('Thành phần số dư tiền tính lãi', {'fields': ['cash_t0','cash_t1','cash_t2','total_buy_trading_value']}),
    ]
    readonly_fields = ['cash_balance', 'market_value', 'nav', 'margin_ratio', 'excess_equity', 'user_created', 'initial_margin_requirement', 'net_cash_flow', 'net_trading_value', 'status','cash_t2','cash_t1',
                       'excess_equity', 'interest_cash_balance' , 'total_loan_interest','total_interest_paid','total_temporarily_interest','total_pl','total_closed_pl','total_temporarily_pl', 'user_modified',
                       'cash_t0','total_buy_trading_value'
                       ]
    search_fields = ['id','name']
    list_filter = ['name',]
    
    def save_model(self, request, obj, form, change):
        # Lưu người dùng đang đăng nhập vào trường user nếu đang tạo cart mới
        if not change:  # Kiểm tra xem có phải là tạo mới hay không
            obj.user_created = request.user
        else:
            obj.user_modified = request.user.username
        super().save_model(request, obj, form, change)
    


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

    actions = ['select_account_settlement']

    def interest_payments(self, obj):
        # Display a custom button in the admin list view
        if obj.market_value == 0 and obj.total_temporarily_interest !=0 :
                return 'Tất toán'      
        return '-'

    interest_payments.short_description = 'Tất toán'

    def select_account_settlement(self, request, queryset):
         # Check if the user is a superuser
        if request.user.is_superuser:
            # Custom action to reset selected accounts
            for account in queryset:
                if account.market_value == 0  and account.total_temporarily_interest !=0:
                    amount =0
                    if account.interest_cash_balance <=0:
                        date=datetime.now().date()
                        amount1 = account.interest_fee * account.interest_cash_balance/360
                        if account.cash_t1 !=0:
                            if account.interest_cash_balance+account.cash_t1 <0:
                                amount_2 = account.interest_fee * (account.interest_cash_balance+account.cash_t1)/360    
                            else:
                                amount_2 = 0
                        else:
                            amount_2=amount1 
                        amount = amount1 +    amount_2  
                        print(amount_2) 
                        description = f"TK {account.pk} tính lãi gộp tất toán"
                        
                        ExpenseStatement.objects.create(
                            account=account,
                            date=date,
                            type = 'interest',
                            amount = amount,
                            description = description,
                            interest_cash_balance = account.interest_cash_balance
                            )
                        account.total_loan_interest += amount
                        account.save()
                        
                    account.total_interest_paid += account.total_temporarily_interest 
                    account.total_closed_pl += account.total_temporarily_pl
                    account.interest_cash_balance =account.interest_cash_balance + account.cash_t1 + account.cash_t2- account.total_temporarily_pl + account.total_temporarily_interest
                    account.cash_t1 = 0
                    account.cash_t2 = 0

                    # Save the changes
                    account.save()
                    self.message_user(request, f'Reset {queryset.count()} selected accounts.')
                else:
                    self.message_user(request, 'Tài khoản chưa đủ điều kiện để thanh toán lãi', level='ERROR')
        else:
            self.message_user(request, 'You do not have permission to perform this action.', level='ERROR')

    select_account_settlement.short_description = 'Tất toán tài khoản'

    
    formatted_cash_balance.short_description = 'Số dư tiền'
    formatted_interest_cash_balance.short_description = 'Số dư tính lãi'
    formatted_market_value.short_description = 'Giá trị thị trường'
    formatted_nav.short_description = 'Tài sản ròng'
    formatted_margin_ratio.short_description = 'Tỷ lệ kí quỹ'
    formatted_excess_equity.short_description = 'Dư kí quỹ'
    formatted_total_temporarily_pl.short_description = 'Tổng lãi lỗ'


admin.site.register(Account,AccountAdmin)

class MaxTradingPowerAccountAdmin(admin.ModelAdmin):
    model = MaxTradingPowerAccount
    list_display = ['name', 'id','list_stock_2_8','list_stock_3_7']#,'real_min_power','real_max_power']
    search_fields = ['name','id']
    readonly_fields = ['name', 'id','cpd','user_created','description','total_pl','total_closed_pl','total_temporarily_pl']
    fieldsets = [
        ('Thông tin cơ bản', {'fields': ['name','cpd','user_created','description']}),
        ('Hiệu quả đầu tư', {'fields': ['total_pl','total_closed_pl','total_temporarily_pl']}),]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(nav__gt=0)
    

    
    def list_stock_2_8(self, obj):
        max_value = 0
        if obj.excess_equity >0:
            pre_max_value = obj.excess_equity / (20/100)
            credit_limit = obj.credit_limit
            max_value =min(pre_max_value,credit_limit,real_max_power(datetime.now().date()))     
        return '{:,.0f}'.format(max_value)
    list_stock_2_8.short_description = 'Nhóm mã 2:8'

    def list_stock_3_7(self, obj):
        max_value = 0
        if obj.excess_equity >0:
            pre_max_value = obj.excess_equity / (30/100)
            credit_limit = obj.credit_limit
            max_value =min(pre_max_value,credit_limit,real_min_power(datetime.now().date()))     
        return '{:,.0f}'.format(max_value)
    list_stock_3_7.short_description = 'Nhóm mã 3:7'

    

    def has_add_permission(self, request):
        # Return False to disable the "Add" button
        return False
    
    



admin.site.register(MaxTradingPowerAccount,MaxTradingPowerAccountAdmin)


class StockListMarginAdmin(admin.ModelAdmin):
    model= StockListMargin
    list_display = ['stock','initial_margin_requirement','ranking','exchanges','created_at','modified_at','user_created']
    search_fields = ['stock',]
    readonly_fields = ['modified_at','user_created']
    def save_model(self, request, obj, form, change):
        # Lưu người dùng đang đăng nhập vào trường user nếu đang tạo cart mới
        if not change:  # Kiểm tra xem có phải là tạo mới hay không
            obj.user_created = request.user
        else:
            obj.user_modified = request.user.username
        super().save_model(request, obj, form, change)



admin.site.register(StockListMargin,StockListMarginAdmin)



class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = '__all__'
    
    # def clean(self):
    #     cleaned_data = super().clean()
    #     change = self.instance.pk is not None  # Kiểm tra xem có phải là sửa đổi không
    #     today = timezone.now().date()
    #     # Kiểm tra quyền
    #     if change and self.instance.created_at.date() != today:
    #             raise ValidationError("Bạn không có quyền sửa đổi các bản ghi được tạo ngày trước đó.")
    #     return cleaned_data
    
    
class TransactionAdmin(admin.ModelAdmin):
    form = TransactionForm
    list_display_links = ['stock',]
    list_display = ['account','date','stock','position','formatted_price','formatted_qty','formatted_net_total_value','created_at','user_created','formatted_transaction_fee','formatted_tax']
    readonly_fields = ['user_created','user_modified','transaction_fee','tax','total_value','net_total_value']
    search_fields = ['account__id','account__name','stock__stock']
    list_filter = ['account__name',]
    def save_model(self, request, obj, form, change):
        # Lưu người dùng đang đăng nhập vào trường user nếu đang tạo cart mới
        if not change:  # Kiểm tra xem có phải là tạo mới hay không
            obj.user_created = request.user
            super().save_model(request, obj, form, change)
        else:
            today = timezone.now().date()
            obj.user_modified = request.user.username
            if obj.created_at.date() != today:
                if not request.user.is_superuser:
                    raise PermissionDenied("Bạn không có quyền sửa đổi bản ghi.")
                else:
                    # Thêm dòng cảnh báo cho siêu người dùng
                    messages.warning(request, "Sao kê phí lãi vay đã được cập nhật.")
                    super().save_model(request, obj, form, change)
                    delete_and_recreate_interest_expense(obj.account)
            else:
                super().save_model(request, obj, form, change)
    
    

                
    



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

admin.site.register(Transaction,TransactionAdmin)

class PortfolioAdmin(admin.ModelAdmin):
    model = Portfolio
    list_display = ['account', 'stock', 'formatted_market_price', 'formatted_avg_price', 'formatted_on_hold', 'formatted_receiving_t1', 'formatted_receiving_t2', 'formatted_profit', 'percent_profit', 'formatted_sum_stock']
    readonly_fields = ['account','stock','market_price','avg_price','on_hold','receiving_t1','receiving_t2','profit','percent_profit', 'sum_stock', 'market_value']
    search_fields = ['stock','account__id','account__name']
    list_filter = ['account__name',]
    def get_queryset(self, request):
        # Chỉ trả về các bản ghi có sum_stock > 0
        return super().get_queryset(request).filter(sum_stock__gt=0)

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
    
admin.site.register(Portfolio,PortfolioAdmin)

class ExpenseStatementAdmin(admin.ModelAdmin):
    model = ExpenseStatement
    list_display = ['account', 'date', 'type', 'formatted_amount', 'description']
    search_fields = ['account__id','account__name']
    list_filter = ['type']

    def formatted_amount(self, obj):
        return '{:,.0f}'.format(obj.amount)
    

    formatted_amount.short_description = 'Số tiền'

    def has_add_permission(self, request):
        # Return False to disable the "Add" button
        return False

admin.site.register(ExpenseStatement, ExpenseStatementAdmin)

class CashTransferForm(forms.ModelForm):
    class Meta:
        model = CashTransfer
        fields = '__all__'

    # def clean(self):
    #     cleaned_data = super().clean()
    #     change = self.instance.pk is not None  # Kiểm tra xem có phải là sửa đổi không

    #     today = timezone.now().date()

    #     # Kiểm tra quyền
    #     if change and self.instance.created_at.date() != today:
    #         raise ValidationError("Bạn không có quyền sửa đổi các bản ghi được tạo ngày trước đó.")

    #     return cleaned_data

class CashTransferAdmin(admin.ModelAdmin):
    form  = CashTransferForm
    list_display = ['account', 'date', 'formatted_amount', 'user_created', 'user_modified', 'created_at']
    readonly_fields = ['user_created', 'user_modified']
    search_fields = ['account__id','account__name']
    list_filter = ['account__name',]
    def formatted_amount(self, obj):
        return '{:,.0f}'.format(obj.amount)

    formatted_amount.short_description = 'Số tiền'
    
    # def save_model(self, request, obj, form, change):
    #     if not change:  # Kiểm tra xem có phải là tạo mới hay không
    #         obj.user_created = request.user
    #      # Check if the record is being edited
    #     else:
    #         obj.user_modified = request.user.username
                
    #     super().save_model(request, obj, form, change)
    
    def save_model(self, request, obj, form, change):
        # Lưu người dùng đang đăng nhập vào trường user nếu đang tạo cart mới
        if not change:  # Kiểm tra xem có phải là tạo mới hay không
            obj.user_created = request.user
            super().save_model(request, obj, form, change)
        else:
            today = timezone.now().date()
            obj.user_modified = request.user.username
            if obj.created_at.date() != today:
                if not request.user.is_superuser:
                    raise PermissionDenied("Bạn không có quyền sửa đổi bản ghi.")
                else:
                    # Thêm dòng cảnh báo cho siêu người dùng
                    messages.warning(request, "Số dư tiền và tài sản đã được cập nhật lại")
                    super().save_model(request, obj, form, change)
                    
            else:
                super().save_model(request, obj, form, change)

        


admin.site.register(CashTransfer,CashTransferAdmin)