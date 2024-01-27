import re
from django.db import models
from django.db.models.signals import post_save, post_delete,pre_save, pre_delete
from django.contrib.auth.models import User, Group
from django.dispatch import receiver
from datetime import datetime, timedelta
from django.forms import ValidationError
import requests
from bs4 import BeautifulSoup
from infotrading.models import DateNotTrading, StockPriceFilter, DividendManage, get_list_stock_price
from django.db.models import Sum
from django.utils import timezone
from telegram import Bot
from django.db.models import Q
from cpd.models import ClientPartnerInfo
from django.contrib.auth.hashers import make_password
from regulations.models import *
from accfifo import Entry, FIFO


maintenance_margin_ratio = OperationRegulations.objects.get(pk=4).parameters
force_sell_margin_ratio = OperationRegulations.objects.get(pk=5).parameters
# maintenance_margin_ratio =17
# force_sell_margin_ratio =13

def get_default_parameters(pk):
    try:
        return OperationRegulations.objects.get(pk=pk).parameters
    except OperationRegulations.DoesNotExist:
        # Trả về giá trị mặc định nếu không tìm thấy đối tượng
        return 0.0  # hoặc giá trị mặc định của bạn

def get_interest_fee_default():
    return get_default_parameters(pk=3)

def get_transaction_fee_default():
    return get_default_parameters(pk=1)

def get_tax_fee_default():
    return get_default_parameters(pk=2)

def get_credit_limit_default():
    return get_default_parameters(pk=6)







# Create your models here.
class Account (models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name= 'Tên KH')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    description = models.TextField(max_length=255, blank=True, verbose_name= 'Mô tả')
    cpd = models.ForeignKey(ClientPartnerInfo,null=True, blank = True,on_delete=models.CASCADE, verbose_name= 'Người giới thiệu' )
    #biểu phí dịch vụ
    interest_fee = models.FloatField(default=get_interest_fee_default, verbose_name='Lãi suất')
    transaction_fee = models.FloatField(default=get_transaction_fee_default, verbose_name='Phí giao dịch')
    tax = models.FloatField(default=get_tax_fee_default, verbose_name='Thuế')
    # interest_fee = models.FloatField(default=0, verbose_name='Lãi suất')
    # transaction_fee = models.FloatField(default=0, verbose_name='Phí giao dịch')
    # tax = models.FloatField(default=0, verbose_name='Thuế')
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
    # credit_limit = models.FloatField(default=1000000000, verbose_name='Hạn mức mua')
    milestone_date_lated = models.DateTimeField(null =True, blank =True, verbose_name = 'Ngày tất toán gần nhất')
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
        self.total_loan_interest = self.total_temporarily_interest + self.total_interest_paid
        self.cash_balance = self.net_cash_flow + self.net_trading_value + self.total_temporarily_interest
        self.interest_cash_balance =  self.cash_t0 + self.total_buy_trading_value 
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
        self.total_temporarily_pl= self.nav - self.net_cash_flow
        self.total_pl  = self.total_temporarily_pl + self.total_closed_pl
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
    interest_fee = models.FloatField(default=0.16, verbose_name='Lãi suất')
    transaction_fee = models.FloatField(default=0.0015, verbose_name='Phí giao dịch')
    tax = models.FloatField(default=0.0001, verbose_name='Thuế')
    # Phục vụ tính tổng cash_balace:
    net_cash_flow= models.FloatField(default=0,verbose_name= 'Nạp rút tiền ròng')
    total_buy_trading_value= models.FloatField(default=0,verbose_name= 'Tổng giá trị mua')
    net_trading_value = models.FloatField(default=0,verbose_name= 'Giao dịch ròng')
    interest_paid= models.FloatField(default=0,verbose_name= 'Tổng lãi vay đã trả')
    closed_pl= models.FloatField(default=0,verbose_name= 'Tổng lời lỗ đã chốt')
    

    class Meta:
         verbose_name = 'Mốc Tài khoản'
         verbose_name_plural = 'Mốc Tài khoản'

    def __str__(self):
        return str(self.account) +str('_Lần_')+ str(self.milestone)

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
            if self.account.milestone_date_lated:
                date_cal = self.account.milestone_date_lated
            else:
                date_cal = self.account.created_at
            self.avg_price = round(cal_avg_price(self.account.pk,self.stock,date_cal ),0)
            self.profit = round((self.market_price - self.avg_price)*self.sum_stock,0)
            self.percent_profit = round((self.market_price/self.avg_price-1)*100,2)
            self.market_value = self.market_price*self.sum_stock
        super(Portfolio, self).save(*args, **kwargs)



        
    

def define_t_plus(initial_date, date_milestone):
    try:
        if date_milestone >= initial_date:
            t = 0
            check_date = initial_date 
            max_iterations = (date_milestone - check_date).days   # Số lần lặp tối đa để tránh vòng lặp vô tận
            for _ in range(max_iterations + 1):  
                check_date += timedelta(days=1)
                if check_date > date_milestone or t==2:
                    break  # Nếu đã vượt qua ngày mốc, thoát khỏi vòng lặp
                weekday = check_date.weekday() 
                check_in_dates =  DateNotTrading.objects.filter(date=check_date).exists()
                if not (check_in_dates or weekday == 5 or weekday == 6):
                    t += 1
            return t
        else:
            print(f'Lỗi: date_milestone không lớn hơn hoặc bằng initial_date')
    except Exception as e:
        print(f'Lỗi: {e}')



    



def define_date_receive_cash(initial_date, t_plus):
    t = 0
    check_date = initial_date 
    while t < t_plus:
        check_date += timedelta(days=1)
        weekday = check_date.weekday()
        check_in_dates = DateNotTrading.objects.filter(date=check_date).exists()
        if not (check_in_dates or weekday == 5 or weekday == 6):
            t += 1
        if t == t_plus:
            nunber_days = (check_date-initial_date).days
            return check_date, nunber_days


def cal_avg_price(account,stock, date_time): 
    item_transactions = Transaction.objects.filter(account=account, stock__stock = stock, created_at__gt =date_time).order_by('date','created_at')
    fifo = FIFO([])
    for item in item_transactions:
    # Kiểm tra xem giao dịch có phải là mua hay bán
        if item.position == 'buy':
            # Nếu là giao dịch mua, thêm một Entry mới với quantity dương vào FIFO
            entry = Entry(item.qty, item.price)
        else:
            # Nếu là giao dịch bán, thêm một Entry mới với quantity âm vào FIFO
            entry = Entry(-item.qty, item.price)
        # Thêm entry vào FIFO
        fifo._push(entry) if entry.buy else fifo._fill(entry)
        
        # fifo.trace in ra từng giao dịch bán
        # fifo.profit_and_loss tính lời lỗ
    return fifo.avgcost






def get_stock_market_price(stock):
    linkbase = 'https://www.cophieu68.vn/quote/summary.php?id=' + stock
    try:
        # Attempt to get stock price from the primary source
        r = requests.get(linkbase)
        r.raise_for_status()  # Check for HTTP errors
        soup = BeautifulSoup(r.text, 'html.parser')
        div_tag = soup.find('div', id='stockname_close')
        return float(div_tag.text) * 1000
    except requests.exceptions.RequestException as primary_exception:
        try:
            print(f"lỗi truy cập cổ phiếu 68")
            list_stock=[]
            list_stock.append(stock)
            return get_list_stock_price(list_stock) 
        except Exception as alternative_exception:
            print(f"Lỗi truy cập TPBS: {alternative_exception}")
            return 0
    
        





   

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
                description = f"Thuế phát sinh bán với lệnh bán {instance.stock} số lượng {instance.qty} và giá {instance.price } "
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
            if define_t_plus(item.date, today) == 0:
                        receiving_t2 += item.qty                           
            elif define_t_plus(item.date, today) == 1:
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
        if define_t_plus(item.date,today) == 0:
            cash_t2 += item.net_total_value 
        elif define_t_plus(item.date, today) == 1:
            cash_t1+= item.net_total_value 
        else:
            cash_t0 += item.net_total_value 
    account.cash_t2 = cash_t2
    account.cash_t1 = cash_t1
    account.cash_t0 = cash_t0
    account.total_buy_trading_value = total_value_buy
    account.net_trading_value = sum(item.net_total_value for item in transaction_items)
    




def update_or_created_expense_transaction(instance, description_type):
    description_tax = f"Thuế với lệnh bán {instance.stock} số lượng {instance.qty} và giá {instance.price } "
    description_transaction = f"PGD phát sinh với lệnh {instance.position} {instance.stock} số lượng {instance.qty} và giá {instance.price } "
    ExpenseStatement.objects.update_or_create(
        description = description_tax if description_type == 'tax' else description_transaction,
        type=description_type,
        defaults={
            'account': instance.account,
            'date': instance.date,
            'amount': instance.tax*-1 if description_type == 'tax' else instance.transaction_fee*-1,
        }
    )


def process_cash_flow(cash_t0, cash_t1, cash_t2):
    cash_t0 += cash_t1
    cash_t1 = 0
    cash_t1 += cash_t2
    cash_t2 = 0
    return cash_t0, cash_t1, cash_t2

def add_list_interest(account, list_data, cash_t0, total_buy_value, date_interest):
    # Kiểm tra xem date_interest đã tồn tại trong list_data hay chưa
    existing_data = next((item for item in list_data if item['date'] == date_interest), None)
    interest_cash_balance = cash_t0 + total_buy_value if cash_t0 + total_buy_value <= 0 else 0
    interest = round(interest_cash_balance * account.interest_fee / 360, 0)
    # Nếu date_interest đã tồn tại
    if existing_data:
        existing_data['interest_cash_balance'] = interest_cash_balance
        existing_data['interest'] = interest
    else:
        dict_data = {
            'date': date_interest,
            'interest_cash_balance': interest_cash_balance,
            'interest': interest
        }
        list_data.append(dict_data)
    return list_data

from operation.models import*
# account =Account.objects.get(pk=7)

def delete_and_recreate_interest_expense(account):
    end_date = datetime.now().date() - timedelta(days=1)
    milestone_account = AccountMilestone.objects.filter(account=account).order_by('-created_at').first()
    if milestone_account:
        date_previous = milestone_account.created_at
    else:
        date_previous = account.created_at
    transaction_items_merge_date = Transaction.objects.filter(
        account=account,
        created_at__gt=date_previous
    ).values('position', 'date').annotate(total_value=Sum('net_total_value')).order_by('date')
    list_data = []
    total_buy_value = 0
    cash_t2, cash_t1, cash_t0 = 0, 0, 0
    if transaction_items_merge_date and transaction_items_merge_date[0]['date']<=end_date:
        for index, item in enumerate(transaction_items_merge_date):
            # Kiểm tra xem có ngày tiếp theo hay không
            if index < len(transaction_items_merge_date) - 1:
                next_item_date = transaction_items_merge_date[index + 1]['date']
            else:
                # Nếu đến cuối list, thì thay thế ngày tiếp theo bằng ngày hôm nay
                next_item_date = end_date
            next_day = define_date_receive_cash(item['date'], 1)[0]
    
            if cash_t1 !=0 or cash_t2!=0:
                cash_t0, cash_t1, cash_t2 = process_cash_flow(cash_t0, cash_t1, cash_t2)

            if item['position']== 'buy':
                    print()
                    total_buy_value += item['total_value']
                    print(f"Mua ngày {item['date']} giá trị {total_buy_value}  ")
            else:
                    cash_t2 += item['total_value']
                    print(f"Bán ngày {item['date']} giá trị {cash_t2}  ")
            print(total_buy_value, cash_t0)
            add_list_interest(account,list_data,cash_t0 ,total_buy_value,item['date'])
            

            while next_day <= next_item_date:
                date_while_loop = next_day
                cash_t0, cash_t1, cash_t2 = process_cash_flow(cash_t0, cash_t1, cash_t2)
                print(f"chạy thanh toán ngày {date_while_loop} {cash_t0, cash_t1, cash_t2}")
                add_list_interest(account,list_data,cash_t0 ,total_buy_value,date_while_loop)
                next_day = define_date_receive_cash(next_day, 1)[0]
                if next_day == next_item_date:
                    break
        # Tạo một danh sách chứa tất cả các ngày từ ngày đầu tiên đến ngày cuối
        all_dates = [list_data[0]['date'] + timedelta(days=i) for i in range((list_data[-1]['date'] - list_data[0]['date']).days + 1)]
        # Tạo một danh sách mới chứa các phần tử đã có và điền giá trị bằng giá trị trước đó nếu thiếu
        new_data = []
        for d in all_dates:
            existing_entry = next((item for item in list_data if item['date'] == d), None)
            if existing_entry:
                new_data.append(existing_entry)
            else:
                previous_entry = new_data[-1]
                new_entry = {'date': d, 'interest_cash_balance': previous_entry['interest_cash_balance'], 'interest': previous_entry['interest']}
                new_data.append(new_entry)
    new_data.sort(key=lambda x: x['date'])
    # expense = ExpenseStatement.objects.filter(account = account, type ='interest')
    # expense.delete()
    # for item in new_data:
    #     if item['interest'] != 0:
    #         ExpenseStatement.objects.create(
    #             description=f"Số dư tính lãi {"{:,.0f}".format(item['interest_cash_balance'])}",
    #             type='interest',
    #             account=account,
    #             date=item['date'],
    #             amount=item['interest'],
    #             interest_cash_balance=item['interest_cash_balance']
    #         )
        
    return new_data



@receiver([post_save, post_delete], sender=AccountMilestone)
def save_field_account(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if not created:
        account = instance.account
        item_milestone = AccountMilestone.objects.filter(account=account)
        account.total_interest_paid = sum(item.interest_paid for item in item_milestone)
        account.total_closed_pl =  sum(item.closed_pl for item in item_milestone)
        account.save()




@receiver([post_save, post_delete], sender=Transaction)
@receiver([post_save, post_delete], sender=CashTransfer)
def save_field_account(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    account = instance.account
    milestone_account = AccountMilestone.objects.filter(account =account).order_by('-created_at').first()
    if milestone_account:
            date_mileston = milestone_account.created_at
    else:
            date_mileston = account.created_at
    
    if sender == CashTransfer:
        if not created:
            cash_items = CashTransfer.objects.filter(account=account,created_at__gt = date_mileston)
            account.net_cash_flow = sum(item.amount for item in cash_items)
        else:
            account.net_cash_flow +=  instance.amount
        
    elif sender == Transaction:
        portfolio = Portfolio.objects.filter(stock =instance.stock, account= instance.account).first()
        transaction_items = Transaction.objects.filter(account=account,created_at__gt = date_mileston)
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
    account = instance.account 
    # tìm mileston gần nhất
    milestone_account = AccountMilestone.objects.filter(account = account).order_by('-created_at').first()
    if milestone_account:
        date_mileston = milestone_account.created_at
    else:
        date_mileston = account.created_at
    interests_period = ExpenseStatement.objects.filter(account= account , type ='interest' , created_at__gt = date_mileston)
    sum_interest = 0
    if interests_period:
        sum_interest = sum( item.amount for item in interests_period)
    account.total_temporarily_interest = sum_interest
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
                ExpenseStatement.objects.create(
                    account=instance,
                    date=datetime.now().date()-timedelta(days=1),
                    type = 'interest',
                    amount = amount,
                    description=f"Số dư tính lãi {"{:,.0f}".format(instance.interest_cash_balance)}",
                    interest_cash_balance = instance.interest_cash_balance
                    )

def pay_money_back():
    account = Account.objects.all()
    if account:
        for instance in account:
        # chuy?n ti?n d?n lên 1 ngày
            instance.interest_cash_balance += instance.cash_t1
            instance.cash_t0 += instance.cash_t1
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



def setle_milestone_account(account ):
    status = False
    if account.market_value == 0  and account.total_temporarily_interest !=0 and account.interest_cash_balance <=0:
        status = True
        date=datetime.now().date()
        if account.cash_t1 !=0 and account.cash_t2 !=0:
            number_interest_t1 = define_date_receive_cash(date,1)[1]
            number_interest = define_date_receive_cash(date,2)[1]
            amount1 = account.interest_fee *(account.interest_cash_balance)*number_interest_t1 /360
            amount2 = account.interest_fee *(account.interest_cash_balance - account.cash_t1)*number_interest /360
            amount =amount1+amount2
        
        elif account.cash_t1 !=0 and account.cash_t2 ==0:
            number_interest = define_date_receive_cash(date,1)[1]
            amount = account.interest_fee *(account.interest_cash_balance)*number_interest /360
        elif account.cash_t1 ==0 and account.cash_t2 !=0:
            number_interest = define_date_receive_cash(date,2)[1]
            amount = account.interest_fee *(account.interest_cash_balance)*number_interest /360  
        else:
            print('Vẫn còn âm tiền, cần giải pháp đòi nọ')
            amount = 0
            
        description = f"TK {account.pk} tính lãi gộp tất toán cho {number_interest} ngày"
        if  amount != 0 :
            ExpenseStatement.objects.create(
                    account=account,
                    date=date,
                    type = 'interest',
                    amount = amount,
                    description = description,
                    interest_cash_balance = account.interest_cash_balance
                    )
        withdraw_cash = CashTransfer.objects.create(
            account = account,
            date = date,
            amount = -account.nav,
            description = "Tất toán tài khoản, lệnh rút tiền tự động",      
        )
        number = len(AccountMilestone.objects.filter(account=account)) +1
        a = AccountMilestone.objects.create(
            account=account,
            milestone = number,
            interest_fee = account.interest_fee,
            transaction_fee = account.transaction_fee,
            tax = account.tax,
            net_cash_flow = account.net_cash_flow,
            total_buy_trading_value = account.total_buy_trading_value,
            net_trading_value = account.net_trading_value,
            interest_paid  = account.total_temporarily_interest,
            closed_pl    = account.total_temporarily_pl   )
        
        
        account.cash_t0 = 0
        account.cash_t1 = 0
        account.cash_t2 = 0
        account.total_interest_paid += a.interest_paid
        account.total_closed_pl += a.closed_pl
        account.milestone_date_lated = a.created_at
        account.net_cash_flow = 0
        account.net_trading_value = 0
        account.total_buy_trading_value = 0
        account.total_temporarily_interest = 0
        account.total_temporarily_pl = 0
        account.save()
    return  status




                