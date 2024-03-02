from django.db import models
from operation.models import *
from realstockaccount.models import *

# Create your models here.
class PartnerInfoProxy(PartnerInfo):
    class Meta:
        proxy = True
        verbose_name = 'Đăng kí đối tác'
        verbose_name_plural = 'Đăng kí đối tác'
    
    def __str__(self):
        return str(self.name)
    
class AccountPartner (models.Model):
    name = models.ForeignKey(Account,on_delete=models.CASCADE, verbose_name= 'Tài khoản' )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    description = models.TextField(max_length=255, blank=True, verbose_name= 'Mô tả')
    partner = models.ForeignKey(PartnerInfo,on_delete=models.CASCADE, verbose_name= 'Đối tác')
    net_cash_flow= models.FloatField(default=0,verbose_name= 'Nạp rút tiền ròng')
    net_trading_value= models.FloatField(default=0,verbose_name= 'Giao dịch ròng')
    cash_balance  = models.FloatField(default=0,verbose_name= 'Số dư tiền')
    market_value = models.FloatField(default=0,verbose_name= 'Giá trị thị trường')
    nav = models.FloatField(default=0,verbose_name= 'Tài sản ròng')
    initial_margin_requirement= models.FloatField(default=0,verbose_name= 'Kí quy ban đầu')
    margin_ratio = models.FloatField(default=0,verbose_name= 'Tỷ lệ margin')
    excess_equity= models.FloatField(default=0,verbose_name= 'Dư kí quỹ')
    #Phục vụ tính số dư tiền tính lãi vay: interest_cash_balance = net_cash_flow + total_buy_trading_value  + casht0
    total_buy_trading_value= models.FloatField(default=0,verbose_name= 'Tổng giá trị mua')
    cash_t1 = models.FloatField(default=0,verbose_name= 'Số dư tiền T1')
    cash_t2= models.FloatField(default=0,verbose_name= 'Số dư tiền T2')
    cash_t0= models.FloatField(default=0,verbose_name= 'Số dư tiền bán đã về')
    interest_cash_balance= models.FloatField(default=0,verbose_name= 'Số dư tiền tính lãi')
    total_loan_interest= models.FloatField(default=0,verbose_name= 'Tổng lãi vay')
    total_interest_paid= models.FloatField(default=0,verbose_name= 'Tổng lãi vay đã trả')
    total_temporarily_interest =models.FloatField(default=0,verbose_name= 'Tổng lãi vay tạm tính')
    total_advance_fee= models.FloatField(default=0,verbose_name= 'Tổng phí ứng')
    total_advance_fee_paid= models.FloatField(default=0,verbose_name= 'Tổng phí ứng đã trả')
    total_temporarily_advance_fee =models.FloatField(default=0,verbose_name= 'Tổng phí ứng tạm tính')
    total_pl = models.FloatField(default=0,verbose_name= 'Tổng lời lỗ')
    total_closed_pl= models.FloatField(default=0,verbose_name= 'Tổng lời lỗ đã chốt')
    total_temporarily_pl= models.FloatField(default=0,verbose_name= 'Tổng lời lỗ tạm tính')
    credit_limit = models.FloatField(default=get_credit_limit_default, verbose_name='Hạn mức mua')
    # credit_limit = models.FloatField(default=1000000000, verbose_name='Hạn mức mua')
    milestone_date_lated = models.DateTimeField(null =True, blank =True, verbose_name = 'Ngày tất toán gần nhất')
    advance_cash_balance= models.FloatField(default=0,verbose_name= 'Số dư tiền tính phí ứng')
    maintenance_margin_ratio = models.FloatField(default=15,verbose_name= 'Tỷ lệ gọi kí quỹ')
    force_sell_margin_ratio= models.FloatField(default=13,verbose_name= 'Tỷ lệ giải chấp')


    class Meta:
         verbose_name = 'Tài khoản đối tác'
         verbose_name_plural = 'Tài khoản đối tác'

    def __str__(self):
        return self.name
    
    @property
    def status(self):
        check = self.margin_ratio
        value_force = round((maintenance_margin_ratio - self.margin_ratio)*self.market_value/100,0)
        value_force_str = '{:,.0f}'.format(value_force)
        status = ""
        port = Portfolio.objects.filter(account_id = self.pk, sum_stock__gt=0).first()
        if port:
            price_force_sell = round(-self.cash_balance/( 0.87* port.sum_stock),0)
            if abs(self.cash_balance) >1000 and value_force !=0:
                if check <= maintenance_margin_ratio and check >force_sell_margin_ratio:
                    status = f"CẢNH BÁO, số âm {value_force_str}, giá bán {port.stock}: {'{:,.0f}'.format(price_force_sell)}"
                elif check <= force_sell_margin_ratio:
                    status = f"GIẢI CHẤP {'{:,.0f}'.format(value_force*5)}, giá bán {port.stock}:\n{'{:,.0f}'.format(price_force_sell)}"

                return status
   
    
    def save(self, *args, **kwargs):
    # Your first save method code
        self.total_loan_interest = self.total_temporarily_interest + self.total_interest_paid
        self.total_advance_fee = self.total_temporarily_advance_fee + self.total_advance_fee_paid
        self.cash_balance = self.net_cash_flow + self.net_trading_value + self.total_temporarily_interest + self.total_temporarily_advance_fee
        stock_mapping = {obj.stock: obj.initial_margin_requirement for obj in StockListMargin.objects.all()}
        port = Portfolio.objects.filter(account=self.pk, sum_stock__gt=0)
        sum_initial_margin = 0
        market_value = 0
        if port:
            for item in port:
                initial_margin = stock_mapping.get(item.stock, 0) * item.sum_stock * item.avg_price / 100
                sum_initial_margin += initial_margin
                market_value += item.market_value
        self.margin_ratio = 0
        self.market_value = market_value
        self.nav = self.market_value + self.cash_balance
        self.initial_margin_requirement = sum_initial_margin
        self.excess_equity = self.nav - self.initial_margin_requirement
        self.advance_cash_balance = (self.cash_t1 + self.cash_t2)*-1
        if self.market_value != 0:
            self.margin_ratio = abs(round((self.nav / self.market_value) * 100, 2))
        self.total_temporarily_pl= self.nav - self.net_cash_flow
        self.total_pl  = self.total_temporarily_pl + self.total_closed_pl
        super(Account, self).save(*args, **kwargs)

        
class ExpenseStatementPartner(models.Model):
    POSITION_CHOICES = [
        ('interest', 'Lãi vay'),
        ('transaction_fee', 'Phí giao dịch'),
        ('tax', 'Thuế bán'),
        ('advance_fee', 'Phí ứng tiền bán'),
    ]
    account = models.ForeignKey(AccountPartner,on_delete=models.CASCADE, null=False, blank=False, verbose_name = 'Tài khoản' )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    date =models.DateField( verbose_name = 'Ngày' )
    type =models.CharField(max_length=50, choices=POSITION_CHOICES, null=False, blank=False,verbose_name = 'Loại phí')
    amount = models.FloatField (verbose_name='Số tiền')
    description = models.CharField(max_length=100,null=True, blank=True, verbose_name='Diễn giải')
    interest_cash_balance = models.FloatField (null = True,blank =True ,verbose_name='Số dư tiền tính lãi')
    advance_cash_balance= models.FloatField (null = True,blank =True ,verbose_name='Số dư tiền tính phí ứng')
    transaction_id =models.CharField(max_length= 200,null = True,blank =True ,verbose_name= 'Mã lệnh')
    class Meta:
         verbose_name = 'Bảng kê chi phí '
         verbose_name_plural = 'Bảng kê chi phí '
    
    


    def __str__(self):
        return str(self.type) + str('_')+ str(self.date)

class PortfolioPartner (models.Model):
    account = models.ForeignKey(AccountPartner,on_delete=models.CASCADE, null=False, blank=False, verbose_name = 'Tài khoản' )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    stock = models.CharField(max_length=10, verbose_name = 'Cổ phiếu')
    avg_price = models.FloatField(default=0,verbose_name = 'Giá')
    on_hold = models.IntegerField(default=0,null=True,blank=True,verbose_name = 'Khả dụng')
    receiving_t2 = models.IntegerField(default=0,null=True,blank=True,verbose_name = 'Chờ về T2')
    receiving_t1 = models.IntegerField(default=0,null=True,blank=True,verbose_name = 'Chờ về T1')
    cash_divident = models.FloatField(default=0,null=True,blank=True,verbose_name = 'Cổ tức bằng tiền')
    stock_divident =models.IntegerField(default=0,null=True,blank=True,verbose_name = 'Cổ tức cổ phiếu')
    market_price = models.FloatField(default=0,null=True,blank=True,verbose_name = 'Giá thị trường')
    profit = models.FloatField(default=0,null=True,blank=True,verbose_name = 'Lợi nhuận')
    percent_profit = models.FloatField(default=0,null=True,blank=True,verbose_name = '%Lợi nhuận')
    sum_stock =models.IntegerField(default=0,null=True,blank=True,verbose_name = 'Tổng cổ phiếu')
    market_value = models.FloatField(default=0,null=True,blank=True,verbose_name = 'Giá trị thị trường')
    class Meta:
         verbose_name = 'Danh mục '
         verbose_name_plural = 'Danh mục '

    def __str__(self):
        return self.stock
    
    def save(self, *args, **kwargs):
        self.sum_stock = self.receiving_t2+ self.receiving_t1+self.on_hold 
        self.profit =0
        self.percent_profit = 0
        if self.sum_stock >0:
            self.market_price = round(get_stock_market_price(str(self.stock)),0)
            if self.account.milestone_date_lated:
                date_cal = self.account.milestone_date_lated
            else:
                date_cal = self.account.created_at
            self.avg_price = round(cal_avg_price(self.account.pk,self.stock,date_cal ),0)
            self.profit = round((self.market_price - self.avg_price)*self.sum_stock,0)
            self.percent_profit = round((self.market_price/self.avg_price-1)*100,2)
            self.market_value = self.market_price*self.sum_stock
        super(Portfolio, self).save(*args, **kwargs)

class TransactionPartner(Transaction):
    class Meta:
        proxy = True
        verbose_name = 'Sổ lệnh đối tác'
        verbose_name_plural = 'Sổ lệnh đối tác'
    def get_queryset(self):
        return super().get_queryset().filter(product__is_sell=False)
    def __str__(self):
        return str(self.name)

class CashTransferPartner(RealBankCashTransfer):
    class Meta:
        proxy = True
        verbose_name = 'Sổ lệnh đối tác'
        verbose_name_plural = 'Sổ lệnh đối tác'
    def get_queryset(self):
        return super().get_queryset().filter(product__is_sell=False)
    def __str__(self):
        return str(self.name)