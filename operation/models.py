import re
from django.db import models
from django.db.models.signals import post_save, post_delete,pre_save, pre_delete
from django.contrib.auth.models import User, Group
from django.dispatch import receiver
from datetime import datetime, timedelta
from django.forms import ValidationError
import requests
from bs4 import BeautifulSoup
from infotrading.models import DateNotTrading, StockPriceFilter, DividendManage
from django.db.models import Sum
from django.utils import timezone
from telegram import Bot
from django.db.models import Q
from cpd.models import ClientPartnerInfo
from django.contrib.auth.hashers import make_password
from regulations.models import *


maintenance_margin_ratio = 0.0
force_sell_margin_ratio = 0.0
# maintenance_margin_ratio = OperationRegulations.objects.get(pk=4).parameters
# force_sell_margin_ratio = OperationRegulations.objects.get(pk=5).parameters

def get_default_parameters(pk):
    try:
        return OperationRegulations.objects.get(pk=pk).parameters
    except OperationRegulations.DoesNotExist:
        # Trả về giá trị mặc định nếu không tìm thấy đối tượng
        return 0.0  # hoặc giá trị mặc định của bạn

def get_interest_fee_default():
    # return get_default_parameters(pk=3)
    return 0.0
def get_transaction_fee_default():
    # return get_default_parameters(pk=1)
    return 0.0
def get_tax_fee_default():
    # return get_default_parameters(pk=2)
    return 0.0

def get_credit_limit_default():
    # return get_default_parameters(pk=6)
    return 0.0






# Create your models here.
class Account (models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name= 'Tên')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    description = models.TextField(max_length=255, blank=True, verbose_name= 'Mô tả')
    cpd = models.ForeignKey(ClientPartnerInfo,null=True, blank = True,on_delete=models.CASCADE, verbose_name= 'Người giới thiệu' )
    #biểu phí dịch vụ
    interest_fee = models.FloatField(default=get_interest_fee_default, verbose_name='Lãi suất')
    transaction_fee = models.FloatField(default=get_transaction_fee_default, verbose_name='Phí giao dịch')
    tax = models.FloatField(default=get_tax_fee_default, verbose_name='Thuế')
    # Phục vụ tính tổng cash_balace:
    net_cash_flow= models.FloatField(default=0,verbose_name= 'Nạp rút tiền ròng')
    net_trading_value= models.FloatField(default=0,verbose_name= 'Giao dịch ròng')
    cash_balance  = models.FloatField(default=0,verbose_name= 'Số dư tiền')
    market_value = models.FloatField(default=0,verbose_name= 'Giá trị thị trường')
    nav = models.FloatField(default=0,verbose_name= 'Tài sản ròng')
    initial_margin_requirement= models.FloatField(default=0,verbose_name= 'Kí quy ban đầu')
    margin_ratio = models.FloatField(default=0,verbose_name= 'Tỷ lệ margin')
    excess_equity= models.FloatField(default=0,verbose_name= 'Dư kí quỹ')
    user_created = models.ForeignKey(User,on_delete=models.CASCADE,related_name='user',null=True, blank= True,verbose_name="Người tạo")
    user_modified = models.CharField(max_length=150, blank=True, null=True,verbose_name="Người chỉnh sửa")
    #Phục vụ tính số dư tiền tính lãi vay: interest_cash_balance = net_cash_flow + total_buy_trading_value  + casht0
    total_buy_trading_value= models.FloatField(default=0,verbose_name= 'Tổng giá trị mua')
    cash_t1 = models.FloatField(default=0,verbose_name= 'Số dư tiền T1')
    cash_t2= models.FloatField(default=0,verbose_name= 'Số dư tiền T2')
    cash_t0= models.FloatField(default=0,verbose_name= 'Số dư tiền bán đã về')
    interest_cash_balance= models.FloatField(default=0,verbose_name= 'Số dư tiền tính lãi')
    total_loan_interest= models.FloatField(default=0,verbose_name= 'Tổng lãi vay')
    total_interest_paid= models.FloatField(default=0,verbose_name= 'Tổng lãi vay đã trả')
    total_temporarily_interest =models.FloatField(default=0,verbose_name= 'Tổng lãi vay tạm tính')
    total_pl = models.FloatField(default=0,verbose_name= 'Tổng lời lỗ')
    total_closed_pl= models.FloatField(default=0,verbose_name= 'Tổng lời lỗ đã chốt')
    total_temporarily_pl= models.FloatField(default=0,verbose_name= 'Tổng lời lỗ tạm tính')
    credit_limit = models.FloatField(default=get_credit_limit_default, verbose_name='Hạn mức mua')

    class Meta:
         verbose_name = 'Tài khoản'
         verbose_name_plural = 'Tài khoản'

    def __str__(self):
        return self.name
    
    @property
    def status(self):
        check = self.margin_ratio
        value_force = round((maintenance_margin_ratio - self.margin_ratio)*self.market_value/100,0)
        value_force_str = '{:,.0f}'.format(value_force)
        status = ""
        port = Portfolio.objects.filter(account_id = self.pk).first()
        if port and port.sum_stock>0:
            price_force_sell = round(-self.cash_balance/( 0.87* port.sum_stock),0)
            if abs(self.cash_balance) >1000 and value_force !=0:
                if check <= maintenance_margin_ratio and check >force_sell_margin_ratio:
                    status = f"CẢNH BÁO, số âm {value_force_str}, giá bán {port.stock}: {'{:,.0f}'.format(price_force_sell)}"
                elif check <= force_sell_margin_ratio:
                    status = f"GIẢI CHẤP {'{:,.0f}'.format(value_force*5)}, giá bán {port.stock}:\n{'{:,.0f}'.format(price_force_sell)}"

                return status
   
    
    def save(self, *args, **kwargs):
    # Your first save method code
        self.total_temporarily_interest = self.total_loan_interest - self.total_interest_paid
        self.cash_balance = self.net_cash_flow + self.net_trading_value + self.total_loan_interest
        self.interest_cash_balance =  self.cash_t0 + self.total_buy_trading_value   + self.total_interest_paid - self.total_closed_pl
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
        if self.market_value != 0:
            self.margin_ratio = abs(round((self.nav / self.market_value) * 100, 2))
        self.total_pl = self.nav - self.net_cash_flow
        self.total_temporarily_pl = self.total_pl - self.total_closed_pl
        bot = Bot(token='5806464470:AAH9bLZxhx6xXDJ9rlPKkhaJ6lKpKRrZEfA')
        if self.status:
            noti = f"Tài khoản {self.pk}, tên {self.name} bị {self.status} "
            bot.send_message(
                chat_id='-4055438156',
                text=noti)

        # Your second save method code
        super(Account, self).save(*args, **kwargs)

        # Additional code from the second save method
        # ...

        # Tạo hoặc cập nhật User
        user, created = User.objects.get_or_create(username=str(self.pk))
        if created:
            user.set_password("20241q2w3e4r")
            user.save()

            # Thêm user vào nhóm "customer"
            group, created = Group.objects.get_or_create(name='customer')
            user.groups.add(group)

#Tạo model với các ngăn tất toán của tài khoản
class AccountMilestone(models.Model):
    account = models.ForeignKey(Account,on_delete=models.CASCADE,verbose_name="Tài khoản")
    milestone = models.IntegerField(verbose_name = 'Giai đoạn')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    description = models.TextField(max_length=255, blank=True, verbose_name= 'Mô tả')
    interest_fee = models.FloatField(default=get_interest_fee_default, verbose_name='Lãi suất')
    transaction_fee = models.FloatField(default=get_transaction_fee_default, verbose_name='Phí giao dịch')
    tax = models.FloatField(default=get_tax_fee_default, verbose_name='Thuế')
    # Phục vụ tính tổng cash_balace:
    net_cash_flow= models.FloatField(default=0,verbose_name= 'Nạp rút tiền ròng')
    cash_balance  = models.FloatField(default=0,verbose_name= 'Số dư tiền')
    nav = models.FloatField(default=0,verbose_name= 'Tài sản ròng')
    margin_ratio = models.FloatField(default=0,verbose_name= 'Tỷ lệ margin')
    excess_equity= models.FloatField(default=0,verbose_name= 'Dư kí quỹ')
    #Phục vụ tính số dư tiền tính lãi vay: interest_cash_balance = net_cash_flow + total_buy_trading_value  + casht0
    pre_interest_cash_balance= models.FloatField(default=0,verbose_name= 'Số dư tiền tính lãi')
    interest_paid= models.FloatField(default=0,verbose_name= 'Tổng lãi vay đã trả')
    closed_pl= models.FloatField(default=0,verbose_name= 'Tổng lời lỗ đã chốt')
    

    class Meta:
         verbose_name = 'Mốc Tài khoản'
         verbose_name_plural = 'Mốc Tài khoản'

    def __str__(self):
        return str(self.account) + str(self.milestone)

class MaxTradingPowerAccount(Account):
    class Meta:
        proxy = True
        verbose_name = 'Quản lí sức mua'
        verbose_name_plural = 'Quản lí sức mua'
        
    def get_queryset(self):
        return super().get_queryset().filter(nav__gt=0)
    def __str__(self):
        return str(self.name)

class StockListMargin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    stock = models.CharField(max_length=8,verbose_name = 'Cổ phiếu')
    initial_margin_requirement= models.FloatField(verbose_name= 'Kí quy ban đầu')
    ranking =models.IntegerField(verbose_name='Loại')
    exchanges = models.CharField(max_length=10, verbose_name= 'Sàn giao dịch')
    user_created = models.ForeignKey(User,on_delete=models.CASCADE,null=True, blank= True,                   verbose_name="Người tạo")
    user_modified = models.CharField(max_length=150, blank=True, null=True,
                             verbose_name="Người chỉnh sửa")
    class Meta:
         verbose_name = 'Danh mục cho vay'
         verbose_name_plural = 'Danh mục cho vay'

    def __str__(self):
        return str(self.stock)

class CashTransfer(models.Model):
    account = models.ForeignKey(Account,on_delete=models.CASCADE,verbose_name = 'Tài khoản' )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    date = models.DateField( default=timezone.now,verbose_name = 'Ngày nộp tiền' )
    amount = models.FloatField(verbose_name = 'Số tiền')
    description = models.TextField(max_length=255, blank=True,verbose_name = 'Mô tả')
    user_created = models.ForeignKey(User,on_delete=models.CASCADE,null=True, blank= True,                   verbose_name="Người tạo")
    user_modified = models.CharField(max_length=150, blank=True, null=True,
                             verbose_name="Người chỉnh sửa")
    class Meta:
         verbose_name = 'Giao dịch tiền'
         verbose_name_plural = 'Giao dịch tiền'
    
    def __str__(self):
        return str(self.amount) 
    
    

class Transaction (models.Model):
    POSITION_CHOICES = [
        ('buy', 'Mua'),
        ('sell', 'Bán'),
    ]
    account = models.ForeignKey(Account,on_delete=models.CASCADE, null=False, blank=False, verbose_name = 'Tài khoản' )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    date = models.DateField( default=timezone.now,verbose_name = 'Ngày giao dịch' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    stock = models.ForeignKey(StockListMargin,on_delete=models.CASCADE, null=False, blank=False, verbose_name = 'Cổ phiếu')
    position = models.CharField(max_length=4, choices=POSITION_CHOICES, null=False, blank=False,verbose_name = 'Mua/Bán')
    price = models.FloatField(verbose_name = 'Giá')
    qty = models.IntegerField(verbose_name = 'Khối lượng')
    transaction_fee = models.FloatField( verbose_name= 'Phí giao dịch')
    tax = models.FloatField(default=0,verbose_name= 'Thuế')
    total_value= models.FloatField(default=0, verbose_name= 'Giá trị giao dịch')
    net_total_value = models.FloatField(default=0, verbose_name= 'Giá trị giao dịch ròng')
    user_created = models.ForeignKey(User,on_delete=models.CASCADE,null=True, blank= True,                   verbose_name="Người tạo")
    user_modified = models.CharField(max_length=150, blank=True, null=True,
                             verbose_name="Người chỉnh sửa")
    

    class Meta:
         verbose_name = 'Sổ lệnh '
         verbose_name_plural = 'Sổ lệnh '

    def __str__(self):
        return self.stock.stock
    
    def clean(self):
        if self.price < 0: 
            raise ValidationError('Lỗi giá phải lớn hơn 0')

        # account = self.account
        # ratio_requirement = self.stock.initial_margin_requirement/100

        # if self.position == 'buy': 
        #     max_qty = abs((account.nav/(ratio_requirement*account.margin_ratio/100))/self.price)
        #     if self.qty > max_qty :
        #         raise ValidationError({'qty': f'Không đủ sức mua, số lượng cổ phiếu tối đa  {max_qty:,.0f}'})
                   
        if self.position == 'sell':
            port = Portfolio.objects.filter(account = self.account, stock =self.stock).first()
            stock_hold  = port.on_hold
            sell_pending = Transaction.objects.filter(pk=self.pk).aggregate(Sum('qty'))['qty__sum'] or 0
            max_sellable_qty =stock_hold  + sell_pending
            if self.qty > max_sellable_qty:
                    raise ValidationError({'qty': f'Không đủ cổ phiếu bán, tổng cổ phiếu khả dụng là {max_sellable_qty}'})        
                

         
             
        
        
    def save(self, *args, **kwargs):
        self.total_value = self.price*self.qty
        self.transaction_fee = self.total_value*self.account.transaction_fee
        if self.position == 'buy':
            self.tax =0
            self.net_total_value = -self.total_value-self.transaction_fee-self.tax
        else:
            self.tax = self.total_value*self.account.tax
            self.net_total_value = self.total_value-self.transaction_fee-self.tax
        
        super(Transaction, self).save(*args, **kwargs)


        
 
    
class ExpenseStatement(models.Model):
    POSITION_CHOICES = [
        ('interest', 'Lãi vay'),
        ('transaction_fee', 'Phí giao dịch'),
        ('tax', 'Thuế bán'),
    ]
    account = models.ForeignKey(Account,on_delete=models.CASCADE, null=False, blank=False, verbose_name = 'Tài khoản' )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    date =models.DateField( verbose_name = 'Ngày' )
    type =models.CharField(max_length=50, choices=POSITION_CHOICES, null=False, blank=False,verbose_name = 'Loại phí')
    amount = models.FloatField (verbose_name='Số tiền')
    description = models.CharField(max_length=100,null=True, blank=True, verbose_name='Diễn giải')
    interest_cash_balance = models.FloatField (null = True,blank =True ,verbose_name='Số dư tiền tính lãi')
    class Meta:
         verbose_name = 'Bảng kê chi phí '
         verbose_name_plural = 'Bảng kê chi phí '

    def __str__(self):
        return str(self.type) + str('_')+ str(self.date)

class Portfolio (models.Model):
    account = models.ForeignKey(Account,on_delete=models.CASCADE, null=False, blank=False, verbose_name = 'Tài khoản' )
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
            self.avg_price = round(cal_avg_price(self.account.pk,self.stock)*1000,0)
            self.profit = round((self.market_price - self.avg_price)*self.sum_stock,0)
            self.percent_profit = round((self.market_price/self.avg_price-1)*100,2)
            self.market_value = self.market_price*self.sum_stock
        super(Portfolio, self).save(*args, **kwargs)



        
    

def difine_date_receive_stock_buy(check_date, date_milestone):
    t=0
    while t <= 2 and check_date < date_milestone:  
        check_date = check_date + timedelta(days=1)
        weekday = check_date.weekday() 
        check_in_dates =  DateNotTrading.objects.filter(date=check_date).exists()
        if check_in_dates or weekday == 5 or weekday == 6:
            pass
        else:
            t += 1
    return t

def cal_avg_price(pk,stock):
    item = Transaction.objects.filter(account_id=pk, stock__stock = stock ) 
    total_buy = sum(i.qty for i in item if i.position =='buy' )
    total_sell =sum(i.qty for i in item if i.position =='sell' )
    total_value = sum(i.total_value for i in item if i.position =='buy' )
    date_list =list(item.filter(position ='sell').values_list('date', flat=True).distinct()) 
    avg_price = 0
    date_find=None

    #kiểm tra có bán hay không, trường hợp đã có bán
    if total_sell >0:
        date_list.sort(reverse=True) 
        
        # kiểm tra ngày gần nhất bán hết và mua lại
        for date_check in date_list: 
            new_item = item.filter(date__lte =date_check)
            check_total_buy = 0
            check_total_sell =0
            for i in new_item:
                if i.position == 'buy':
                    check_total_buy += i.qty 
                else:
                    check_total_sell +=i.qty
            if check_total_buy == check_total_sell:
                date_find = i.date
                break 
        if date_find:
            cal_item = item.filter(position='buy',date__gt= date_find )
            for i in cal_item:
                if i.position =='buy':
                    total_buy += i.qty 
                    total_value +=i.total_value
                    avg_price = total_value/total_buy/1000
                    
        else:
            avg_price = total_value/total_buy/1000
    # Nếu có mua nhưng chưa bán lệnh nào
    elif total_buy >0:
        avg_price = total_value/total_buy/1000
    return avg_price



def get_stock_market_price(stock):
    linkbase= 'https://www.cophieu68.vn/quote/summary.php?id=' + stock 
    r =requests.get(linkbase)
    soup = BeautifulSoup(r.text,'html.parser')
    div_tag = soup.find('div', id='stockname_close')
    return float(div_tag.text)*1000





   

# cập nhật giá danh mục => cập nhật giá trị tk chứng khoán
@receiver (post_save, sender=StockPriceFilter)
def update_market_price_port(sender, instance, created, **kwargs):
    port = Portfolio.objects.filter(sum_stock__gt=0, stock =instance.ticker)
    if port:
        for item in port:
            new_price = instance.close*1000
            item.market_price = new_price*item.sum_stock
            item.save()
            account = Account.objects.get(pk =item.account.pk)
            account.save()


            
# Các hàm cập nhập cho account và port

def created_transaction(instance, portfolio, account):
    if instance.position == 'buy':
            #điều chỉnh account
            account.net_trading_value += instance.net_total_value # Dẫn tới thay đổi cash_balace, nav, pl
            account.total_buy_trading_value+= instance.net_total_value #Dẫn tới thay đổi interest_cash_balance 
            if portfolio:
                # điều chỉnh danh mục
                    portfolio.receiving_t2 = portfolio.receiving_t2 + instance.qty 
            else: 
                #tạo danh mục mới
                    Portfolio.objects.create(
                    stock=instance.stock,
                    account= instance.account,
                    receiving_t2 = instance.qty ,)
    elif instance.position == 'sell':
        # điều chỉnh danh mục
        portfolio.on_hold = portfolio.on_hold -instance.qty
        #điều chỉnh account
        account.net_trading_value += instance.net_total_value # Dẫn tới thay đổi cash_balace, nav, pl
        account.cash_t2 += instance.net_total_value #Dẫn tới thay đổi cash_t0 trong tương lai và thay đổi interest_cash_balance 
        
        # tạo sao kê thuế
        ExpenseStatement.objects.create(
                account=instance.account,
                date=instance.date,
                type = 'tax',
                amount = instance.tax*-1,
                description = instance.pk
                )
    
    
    
    
                

            
def update_portfolio_transaction(instance,transaction_items, portfolio):
    #sửa danh mục
    stock_transaction = transaction_items.filter(stock = instance.stock)
    sum_sell = sum(item.qty for item in stock_transaction if item.position =='sell')
    item_buy = stock_transaction.filter( position = 'buy')
    
    if portfolio:
        receiving_t2 =0
        receiving_t1=0
        on_hold =0 
        today  = datetime.now().date()      
        for item in item_buy:
            if difine_date_receive_stock_buy(item.date, today) == 0:
                        receiving_t2 += item.qty                           
            elif difine_date_receive_stock_buy(item.date, today) == 1:
                        receiving_t1 += item.qty                             
            else:
                        on_hold += item.qty

        on_hold = on_hold - sum_sell
                                           
        portfolio.receiving_t2 = receiving_t2
        portfolio.receiving_t1 = receiving_t1
        portfolio.on_hold = on_hold
        
        
# thay đổi sổ lệnh sẽ thay đổi trực tiếp cash_t0 và total_buy_trading_value, net_trading_value
def update_account_transaction(account, transaction_items):
    item_all_sell = transaction_items.filter( position = 'sell')
    cash_t2 = 0
    cash_t1 = 0
    cash_t0 =0
    total_value_buy= sum(i.net_total_value for i in transaction_items if i.position =='buy')
    today  = datetime.now().date()     
    for item in item_all_sell:
        if difine_date_receive_stock_buy(item.date,today) == 0:
            cash_t2 += item.net_total_value 
        elif difine_date_receive_stock_buy(item.date, today) == 1:
            cash_t1+= item.net_total_value 
        else:
            cash_t0 += item.net_total_value 
    account.cash_t2 = cash_t2
    account.cash_t1 = cash_t1
    account.cash_t0 = cash_t0
    account.total_buy_trading_value = total_value_buy
    account.net_trading_value = sum(item.net_total_value for item in transaction_items)
    




def update_or_created_expense_transaction(instance, description_type):
    ExpenseStatement.objects.update_or_create(
        description=instance.pk,
        type=description_type,
        defaults={
            'account': instance.account,
            'date': instance.date,
            'amount': instance.tax*-1 if description_type == 'tax' else instance.transaction_fee*-1,
        }
    )

#chỉ chạy nếu chỉnh tiền/sổ lệnh của ngày trước đó
def delete_and_recreate_interest_expense(account): 
    date_previous = account.created_at.date()
    transaction_items_merge_date =Transaction.objects.filter(account=account).values('position', 'date').annotate(total_value=Sum('net_total_value')).order_by('date')
      #nếu thay đổi nạp tiền
    list_data = []
    total_buy_value = 0
    cash_t2  =0
    cash_t1=0
    cash_t0=0
    if transaction_items_merge_date:
        for item in transaction_items_merge_date:
            dict_data ={}
            #chu kì thanh toán tiền về cho ngày mới
            if item['date'] > date_previous and (cash_t2 > 0 or cash_t1 > 0):
                    if difine_date_receive_stock_buy(date_previous, item['date']) == 1:
                        cash_t0 += cash_t1
                        cash_t1 = 0
                        cash_t1 += cash_t2
                        cash_t2 = 0
                    elif difine_date_receive_stock_buy(date_previous, item['date']) >= 2:
                        cash_t0+= cash_t1 + cash_t2
                        cash_t1=0
                        cash_t2=0
            if item['position'] == 'buy':
                total_buy_value += item['total_value']
            else:
                cash_t2 += item['total_value']
            dict_data['date'] = item['date']
            dict_data['interest_cash_balance'] =  cash_t0 +total_buy_value
            dict_data['interest'] = round(dict_data['interest_cash_balance']*account.interest_fee/360,0)
            list_data.append(dict_data)
            date_previous = item['date']   
    start_date = list_data[0]['date']
    end_date = datetime.now().date() -  timedelta(days=1)
    date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    for date in date_range:
        if date not in [item['date'] for item in list_data]:
            # Lấy giá trị từ ngày liền trước đó
            previous_day = date - timedelta(days=1)
            previous_value = next(item for item in reversed(list_data) if item['date'] == previous_day)
            new_record = {
                'date': date,
                'interest_cash_balance': previous_value['interest_cash_balance'],
                'interest': previous_value['interest']
            }
            list_data.append(new_record)
    list_data.sort(key=lambda x: x['date'])
    expense = ExpenseStatement.objects.filter(account = account, type ='interest')
    expense.delete()
    for item in list_data:
        if item['interest'] != 0:
            ExpenseStatement.objects.create(
                description=account.pk,
                type='interest',
                account=account,
                date=item['date'],
                amount=item['interest'],
                interest_cash_balance=item['interest_cash_balance']
            )
    return list_data, date_range

            




@receiver([post_save, post_delete], sender=Transaction)
@receiver([post_save, post_delete], sender=CashTransfer)
def save_field_account(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    account = instance.account
    
    if sender == CashTransfer:
        if not created:
            cash_items = CashTransfer.objects.filter(account=account)
            account.net_cash_flow = sum(item.amount for item in cash_items)
        else:
            account.net_cash_flow +=  instance.amount
        
    elif sender == Transaction:
        portfolio = Portfolio.objects.filter(stock =instance.stock, account= instance.account).first()
        transaction_items = Transaction.objects.filter(account=account)
        if not created:
            # sửa sao kê phí và thuế
            update_or_created_expense_transaction(instance,'transaction_fee' )
            if instance.position =='sell':
                update_or_created_expense_transaction(instance,'tax' )
            # sửa sao kê lãi
            # sửa danh mục
            update_portfolio_transaction(instance,transaction_items, portfolio)
            
            # sửa account
            update_account_transaction( account, transaction_items)
           
        else:
            created_transaction(instance, portfolio, account)
            update_or_created_expense_transaction(instance,'transaction_fee' )
        if portfolio:
            portfolio.save()   
    account.save()
        
          
            
@receiver(post_delete, sender=Transaction)
def delete_expense_statement(sender, instance, **kwargs):
    expense = ExpenseStatement.objects.filter(description=instance.pk)
    # porfolio = Portfolio.objects.filter(account=instance.account, stock =instance.stock).first()
    if expense:
        expense.delete()      
        
    


          
@receiver([post_save, post_delete], sender=ExpenseStatement)
def save_field_account(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    account = instance.account 
    interests = ExpenseStatement.objects.filter(account= account , type ='interest')
    if not created and interests :
        sum_interest =0
        for item in interests:
            sum_interest +=item.amount
        account.total_loan_interest = sum_interest
        account.save()
                

    
        
    

        


            

    
        



#chạy 1 phút 1 lần
def update_market_price_for_port():
    port = Portfolio.objects.filter(sum_stock__gt=0)
    for item in port:
        item.market_price = get_stock_market_price(item.stock)
        # item.profit = (item.market_price - item.avg_price)*item.sum_stock
        # item.percent_profit = round((item.market_price/item.avg_price-1)*100,2)
        item.save()

def calculate_interest():
    #kiểm tra vào tính lãi suất
    account = Account.objects.filter(interest_cash_balance__lt=0)
    if account:
        for instance in account:
            amount = instance.interest_fee * instance.interest_cash_balance/360
            if abs(amount)>10:
                instance.total_loan_interest += amount
                instance.save()
                ExpenseStatement.objects.create(
                    account=instance,
                    date=datetime.now().date()-timedelta(days=1),
                    type = 'interest',
                    amount = amount,
                    description = instance.pk,
                    interest_cash_balance = instance.interest_cash_balance
                    )

def pay_money_back():
    account = Account.objects.all()
    if account:
        for instance in account:
        # chuyển tiền dồn lên 1 ngày
            instance.interest_cash_balance += instance.cash_t1
            instance.cash_t1= instance.cash_t2
            instance.cash_t2 =0
            instance.save()

def atternoon_check():
    port = Portfolio.objects.filter(sum_stock__gt=0)
    if port:
        for item in port:
            buy_today = Transaction.objects.filter(account = item.account,position ='buy',date = datetime.now().date(),stock__stock = item.stock)
            qty_buy_today = sum(item.qty for item in buy_today )
            item.on_hold += item.receiving_t1
            item.receiving_t1 = item.receiving_t2  - qty_buy_today
            item.receiving_t2 = qty_buy_today
            item.save()

def check_dividend_recevie():
    #check cổ tức
    port = Portfolio.objects.filter(Q(cash_divident__gt=0) | Q(stock_divident__gt=0))
    if port:
        for item in port:
            item.on_hold += item.stock_divident
            account = item.account
            account.cash_balance += item.cash_divident
            account.interest_cash_balance += item.cash_divident
            item.save()
            account.save()


# stockbiz đổi web, tạm thời hàm lỗi
def save_event_stock(stock):
    list_event =[]
    linkbase= 'https://www.stockbiz.vn/MarketCalendar.aspx?Symbol='+ stock
    r = requests.get(linkbase)
    soup = BeautifulSoup(r.text,'html.parser')
    table = soup.find('table', class_='dataTable')  # Tìm bảng chứa thông tin
    if table:
        rows = table.find_all('tr')  # Lấy tất cả các dòng trong bảng (loại bỏ dòng tiêu đề)
        cash_value= 0
        stock_value=0
        stock_option_value=0
        price_option_value=0
        dividend_type = 'order'
        for row in rows[1:]:  # Bắt đầu từ vị trí thứ hai (loại bỏ dòng tiêu đề)
            dividend  = {}
            columns = row.find_all('td')  # Lấy tất cả các cột trong dòng
            if len(columns) >= 3:  # Kiểm tra số lượng cột
                dividend['ex_rights_date'] = columns[0].get_text(strip=True)
                dividend['event'] = columns[4].get_text(strip=True)
                list_event.append(dividend)
                event = dividend['event'].lower()
                ex_rights_date = datetime.strptime(dividend['ex_rights_date'], '%d/%m/%Y').date()
                if ex_rights_date == datetime.now().date():
                    if 'tiền' in event:
                        dividend_type = 'cash'
                        cash = re.findall(r'\d+', event)  # Tìm tất cả các giá trị số trong chuỗi
                        if cash:
                            value1 = int(cash[-1])/1000  # Lấy giá trị số đầu tiên
                            cash_value += value1
                    elif 'cổ phiếu' in event and 'phát hành' not in event:
                        dividend_type = 'stock'
                        stock_values = re.findall(r'\d+', event)
                        if stock_values:
                            value2 = int(stock_values[-1])/int(stock_values[-2])
                            stock_value += value2
                    elif 'cổ phiếu' in event and 'giá' in event and 'tỷ lệ' in event:
                        dividend_type = 'option'
                        option = re.findall(r'\d+', event)
                        if option:
                                stock_option_value = int(option[-2])/int(option[-3])
                                price_option_value = int(option[-1])
        if dividend_type == 'order':
            pass
        else:
            DividendManage.objects.update_or_create(
                        ticker= stock,  # Thay thế 'Your_Ticker_Value' bằng giá trị ticker thực tế
                        date_apply=ex_rights_date,
                        defaults={
                            'type': dividend_type,
                            'cash': cash_value,
                            'stock': stock_value,
                            'price_option': price_option_value,
                            'stock_option':stock_option_value
                        }
                    )
    return list_event

def check_dividend():
    signal = Portfolio.objects.filter(sum_stock__gt=0).distinct('stock') 
    for stock in signal:
        dividend = save_event_stock(stock.stock)
    dividend_today = DividendManage.objects.filter(date_apply =datetime.now().date() )
    for i in dividend_today:
        i.save()



def new_func(account, ):
    if account.market_value == 0  and account.total_temporarily_interest !=0 and account.interest_cash_balance <=0:
        amount =0
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
        description = f"TK {account.pk} tính lãi gộp tất toán"
            
        ExpenseStatement.objects.create(
                account=account,
                date=date,
                type = 'interest',
                amount = amount,
                description = description,
                interest_cash_balance = account.interest_cash_balance
                )
        
        
        # Tạo account_milestones 
        # account.total_interest_paid += account.total_temporarily_interest 
        # account.total_closed_pl += account.total_temporarily_pl
        lated_setle  = AccountMilestone.objects.filter(account = account).order_by('created_at').first()
        if lated_setle:
            number = lated_setle.pk +1
        else:
            number =1

        a = AccountMilestone.objects.create(
            account=account,
            milestone = number,
            interest_fee = account.interest_fee,
            transaction_fee = account.transaction_fee,
            tax = account.tax,
            net_cash_flow = account.net_cash_flow,
            cash_balance = account.cash_balace,
            nav = account.nav,
            margin_ratio = account.margin_ratio,
            excess_equity = account.excess_equity,
            pre_interest_cash_balance = account.interest_cash_balance  ,
            interest_paid  = account.total_temporarily_interest + amount,
            closed_pl    = account.total_temporarily_pl   )
        
        account.total_loan_interest += amount
        account.cash_t0 = account.cash_t0 + account.cash_t1 + account.cash_t2
        account.cash_t1 = 0
        account.cash_t2 = 0
        account.total_interest_paid += a.interest_paid
        account.total_closed_pl += a.losed_pl
        account.save()
    return account, a


                