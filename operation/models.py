import re
from django.db import models
from django.db.models.signals import post_save, post_delete,pre_save, pre_delete
from django.contrib.auth.models import User
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



maintenance_margin_ratio = 17
force_sell_margin_ratio = 13


# Create your models here.
class Account (models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name= 'Tên')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name = 'Ngày tạo' )
    modified_at = models.DateTimeField(auto_now=True, verbose_name = 'Ngày chỉnh sửa' )
    description = models.TextField(max_length=255, blank=True, verbose_name= 'Mô tả')
    cpd = models.ForeignKey(ClientPartnerInfo,null=True, blank = True,on_delete=models.CASCADE, verbose_name= 'Người giới thiệu' )
    interest_fee = models.FloatField(default=0.16,verbose_name= 'Lãi suất')
    transaction_fee = models.FloatField(default=0.0015, verbose_name= 'Phí giao dịch')
    tax = models.FloatField(default=0.001, verbose_name= 'Thuế')
    # bot = models.ForeignKey(BotTelegram,on_delete=models.CASCADE, verbose_name= 'Bot' )
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
    cash_t1 = models.FloatField(default=0,verbose_name= 'Số dư tiền T1')
    cash_t2= models.FloatField(default=0,verbose_name= 'Số dư tiền T2')
    interest_cash_balance= models.FloatField(default=0,verbose_name= 'Số dư tiền tính lãi')
    total_loan_interest= models.FloatField(default=0,verbose_name= 'Tổng lãi vay đã trả')
    total_pl = models.FloatField(default=0,verbose_name= 'Tổng lời lỗ')
    class Meta:
         verbose_name = 'Tài khoản'
         verbose_name_plural = 'Tài khoản'

    def __str__(self):
        return self.name
    
    @property
    def status(self):
        check = self.margin_ratio
        value_force = '{:,.0f}'.format(round((maintenance_margin_ratio - self.margin_ratio)*self.market_value/100,0))
        status = ""
        if self.cash_balance <0:
            if check <= maintenance_margin_ratio and check >force_sell_margin_ratio:
                status = f"CẢNH BÁO, số âm {value_force}"
            elif check <= force_sell_margin_ratio:
                status = f"BÁN GIẢI CHẤP {value_force*5}"
            return status
    
    def save(self, *args, **kwargs):
        self.cash_balance = self.net_cash_flow + self.net_trading_value + self.total_loan_interest
        stock_mapping = {obj.stock: obj.initial_margin_requirement  for obj in StockListMargin.objects.all()}
        port = Portfolio.objects.filter(account =self.pk, sum_stock__gt=0)
        sum_initial_margin = 0
        market_value =0
        if port:
            for item in port:
                initial_margin = stock_mapping.get(item.stock, 0)*item.sum_stock*item.avg_price/100
                sum_initial_margin +=initial_margin
                market_value += item.market_value
        self.margin_ratio = 0
        # self.market_value = Portfolio.objects.filter(account=self.pk).aggregate(Sum('market_value'))['market_value__sum'] or 0
        self.market_value = market_value
        self.nav = self.market_value + self.cash_balance 
        self.initial_margin_requirement = sum_initial_margin
        self.excess_equity = self.nav - self.initial_margin_requirement
        if self.market_value !=0:
            self.margin_ratio = abs(round((self.nav/self.market_value)*100,2))
        self.total_pl = self.nav - self.net_cash_flow
        bot = Bot(token='5806464470:AAH9bLZxhx6xXDJ9rlPKkhaJ6lKpKRrZEfA')
        if self.status:
            noti = f"Tài khoản {self.pk}, tên {self.name} bị {self.status} "
            bot.send_message(
                chat_id='-4055438156', 
                text=noti)
        super(Account, self).save(*args, **kwargs)
    

   

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
        ('buy', 'Buy'),
        ('sell', 'Sell'),
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
            max_qty_sell = port.on_hold
            if self.qty > max_qty_sell:
                raise ValidationError({'qty': f'Không đủ cổ phiếu bán, tổng cổ phiếu khả dụng là {max_qty_sell}'})
        
             
        
        
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
        ('interest', 'interest'),
        ('transaction_fee', 'transaction_fee'),
        ('tax', 'tax'),
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



        
    

def difine_date_receive_stock_buy(check_date):
    t=0
    while t <= 2 and check_date < datetime.now().date():  
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




@receiver(post_delete, sender=Transaction)
def delete_expense_statement(sender, instance, **kwargs):
    expense = ExpenseStatement.objects.filter(description=instance.pk)
    # porfolio = Portfolio.objects.filter(account=instance.account, stock =instance.stock).first()
    if expense:
        expense.delete()
   

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


            
# tách hàm

def created_transaction(instance, portfolio, account):
    if instance.position == 'buy':
            #điều chỉnh account
            account.net_trading_value += instance.net_total_value
            account.interest_cash_balance += instance.net_total_value
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
        #điều chỉnh account
        account.net_trading_value += instance.net_total_value
        account.cash_t2 += instance.net_total_value 
        # điều chỉnh danh mục
        portfolio.on_hold = portfolio.on_hold -instance.qty
          
        # tạo sao kê thuế
        ExpenseStatement.objects.create(
                account=instance.account,
                date=instance.date,
                type = 'tax',
                amount = instance.tax*-1,
                description = instance.pk
                )
    
    
    
    
                

            
def update_portfolio_transaction(instance, portfolio, account):
    transaction_items = Transaction.objects.filter(account=account)
    #sửa danh mục
    stock_transaction = transaction_items.filter(stock = instance.stock)
    sum_sell = sum(item.qty for item in stock_transaction if item.position =='sell')
    item_buy = stock_transaction.filter( position = 'buy')
    
    if portfolio:
        receiving_t2 =0
        receiving_t1=0
        on_hold =0
               
        for item in item_buy:
                    if difine_date_receive_stock_buy(item.date) == 0:
                        receiving_t2 += item.qty                           
                    elif difine_date_receive_stock_buy(item.date) == 1:
                        receiving_t1 += item.qty                             
                    else:
                        on_hold += item.qty- sum_sell
                                           
        portfolio.receiving_t2 = receiving_t2
        portfolio.receiving_t1 = receiving_t1
        portfolio.on_hold = on_hold
        
        

def update_account_transaction(account, transaction_items):
    item_all_sell = transaction_items.filter( position = 'sell')
    cash_t2 = 0
    cash_t1 = 0
    cash_t0= sum(i.net_total_value for i in transaction_items if i.position =='buy')
    for item in item_all_sell:
        if difine_date_receive_stock_buy(item.date) == 0:
            cash_t2 += item.net_total_value 
        elif difine_date_receive_stock_buy(item.date) == 1:
            cash_t1+= item.net_total_value 
        else:
            cash_t0 += item.net_total_value 
    account.cash_t2 = cash_t2
    account.cash_t1 = cash_t1
    account.interest_cash_balance = cash_t0 
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
        account.save()

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
            update_portfolio_transaction(instance, portfolio, account)     
            # sửa account
            update_account_transaction( account, transaction_items)
            account.save()
            
        else:
            created_transaction(instance, portfolio, account)
            if portfolio:
                portfolio.save()
            account.save()
            update_or_created_expense_transaction(instance,'transaction_fee' )
            
            
        
    


          
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

def morning_check():
    #kiểm tra vào tính lãi suất
    account = Account.objects.filter(interest_cash_balance__lt=0)
    if account:
        for instance in account:
            amount = instance.interest_fee * instance.interest_cash_balance/360
            ExpenseStatement.objects.create(
                account=instance,
                date=datetime.now().date()-timedelta(days=1),
                type = 'interest',
                amount = amount,
                description = instance.pk,
                interest_cash_balance = instance.interest_cash_balance
                )
    # chuyển tiền dồn lên 1 ngày
            instance.interest_cash_balance += instance.cash_t1
            instance.cash_t1= instance.cash_t2
            instance.cash_t2 =0
            instance.total_loan_interest += amount
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