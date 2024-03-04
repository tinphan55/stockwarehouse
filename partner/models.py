from django.db import models
from realstockaccount.models import *
from operation.models import *

# Create your models here.
def partner_cal_avg_price(account,partner,stock, date_time): 
    item_transactions = Transaction.objects.filter(account=account,partner =partner, stock__stock = stock, created_at__gt =date_time).order_by('date','created_at')
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

def partner_total_value_inventory_stock(account,partner, stock, date_time, end_date=None):
    if end_date is None:
        end_date = datetime.now().date()
    item_transactions = Transaction.objects.filter(account=account.account,partner =partner, stock__stock=stock, created_at__gt=date_time, date__lte=end_date).order_by('date', 'created_at')
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
    fifo_inventory =fifo.inventory
    total_value = 0
    for entry in fifo_inventory:
        quantity, price = entry.quantity, entry.price
        total_value += quantity * price *(1+account.account.transaction_fee)
    return total_value

def partner_define_interest_cash_balace(account,partner,date_mileston, end_date=None):
    if end_date is None:
        end_date = datetime.now().date()
    all_port = PortfolioPartner.objects.filter(account=account, sum_stock__gt=0)
    interest_cash_balance =0
    for item in all_port:
        interest_cash_balance += partner_total_value_inventory_stock (account,partner,item.stock, date_mileston, end_date)
    return -interest_cash_balance

class PartnerInfoProxy(PartnerInfo):
    class Meta:
        proxy = True
        verbose_name = 'Đăng kí đối tác'
        verbose_name_plural = 'Đăng kí đối tác'
    
    def __str__(self):
        return str(self.name)
    
class AccountPartner (models.Model):
    account = models.ForeignKey(Account,on_delete=models.CASCADE, verbose_name= 'Tài khoản' )
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
        return f"TK {self.account.name}-{self.partner}"
    
    @property
    def status(self):
        check = self.margin_ratio
        value_force = round((maintenance_margin_ratio - self.margin_ratio)*self.market_value/100,0)
        value_force_str = '{:,.0f}'.format(value_force)
        status = ""
        port = PortfolioPartner.objects.filter(account_id = self.pk, sum_stock__gt=0).first()
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
        port = PortfolioPartner.objects.filter(account=self.pk, sum_stock__gt=0)
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
        super(AccountPartner, self).save(*args, **kwargs)


   
    
    

        
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
         verbose_name = 'Bảng kê chi phí đối tác '
         verbose_name_plural = 'Bảng kê chi phí đối tác '
    
    


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
         verbose_name = 'Danh mục đối tác'
         verbose_name_plural = 'Danh mục đối tác'

    def __str__(self):
        return self.stock
    
    def save(self, *args, **kwargs):
        self.sum_stock = self.receiving_t2+ self.receiving_t1+self.on_hold 
        self.profit =0
        self.percent_profit = 0
        if self.sum_stock >0:
            self.market_price = round(get_stock_market_price(str(self.stock)),0)
            if self.account.account.milestone_date_lated:
                date_cal = self.account.account.milestone_date_lated
            else:
                date_cal = self.account.account.created_at
            self.avg_price = round(partner_cal_avg_price(self.account.account.pk,self.account.partner,self.stock,date_cal ),0)
            self.profit = round((self.market_price - self.avg_price)*self.sum_stock,0)
            self.percent_profit = round((self.market_price/self.avg_price-1)*100,2)
            self.market_value = self.market_price*self.sum_stock
        super(PortfolioPartner, self).save(*args, **kwargs)

class TransactionPartnerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(partner=None)

class TransactionPartner(Transaction):
    objects = TransactionPartnerManager()

    class Meta:
        proxy = True
        verbose_name = 'Sổ lệnh đối tác'
        verbose_name_plural = 'Sổ lệnh đối tác'
    

    def __str__(self):
        return str(self.stock)
    

class CashTransferPartnerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(partner=None)


class CashTransferPartner(BankCashTransfer):
    objects =CashTransferPartnerManager()
    class Meta:
        proxy = True
        verbose_name = 'Giao dịch tiền đối tác'
        verbose_name_plural = 'Giao dịch tiền đối tác'
    
    def __str__(self):
        return str(self.account)
    
def update_or_created_expense_partner(instance,account, description_type):
    description_tax = f"Thuế với lệnh bán {instance.stock} số lượng {instance.qty} và giá {instance.price } "
    description_transaction = f"PGD phát sinh với lệnh {instance.position} {instance.stock} số lượng {instance.qty} và giá {instance.price } "
    if description_type=='tax':
        amount = instance.tax*-1
    elif description_type== 'transaction_fee':
        amount = instance.transaction_fee*-1

    ExpenseStatementPartner.objects.update_or_create(
        transaction_id=instance.pk,
        type=description_type,
        defaults={
            'account': account,
            'date': instance.date,
            'amount': amount,
            'description': description_tax if description_type == 'tax' else description_transaction,
    
        }
    )


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

def created_transaction_partner(instance,account,date_mileston):
    partner = instance.partner
    account_partner , created= AccountPartner.objects.get_or_create(
        account=account,
        partner=partner,
        defaults={'description': ''}  # Trường 'description' không bị cập nhật
    )
    # tạo phí giao dịch
    update_or_created_expense_partner(instance,account_partner, description_type='transaction_fee')
    if instance.position == 'buy':
        #điều chỉnh account partner
        account_partner.net_trading_value += instance.net_total_value # Dẫn tới thay đổi cash_balace, nav, pl
        account_partner.total_buy_trading_value+= instance.net_total_value #Dẫn tới thay đổi interest_cash_balance 
        account_partner.interest_cash_balance += instance.net_total_value
        try:
            portfolio_partner = PortfolioPartner.objects.get(stock=instance.stock, account=account_partner)
            # Nếu đối tượng tồn tại, điều chỉnh danh mục
            portfolio_partner.receiving_t2 += instance.qty
            portfolio_partner.save()
        except PortfolioPartner.DoesNotExist:
            # Nếu không tìm thấy, tạo danh mục mới
            PortfolioPartner.objects.create(
                stock=instance.stock,
                account=account_partner,
                receiving_t2=instance.qty,
            )
        
    elif instance.position == 'sell':
        # điều chỉnh danh mục
        portfolio_partner = PortfolioPartner.objects.get(stock=instance.stock, account=account_partner)
        portfolio_partner.on_hold = portfolio_partner.on_hold -instance.qty
        portfolio_partner.save()
        #điều chỉnh account_partner
        account_partner.net_trading_value += instance.net_total_value # Dẫn tới thay đổi cash_balace, nav, pl
        account_partner.cash_t2 += instance.total_value #Dẫn tới thay đổi cash_t0 trong tương lai và thay đổi interest_cash_balance 
        account_partner.interest_cash_balance = partner_define_interest_cash_balace(account_partner,partner,date_mileston)
        update_or_created_expense_partner(instance,account_partner, description_type='tax')
    
    account_partner.save()

def partner_update_transaction(instance,date_mileston):
    account_partner = AccountPartner.objects.get(account=instance.account, partner=instance.partner)
    transaction = Transaction.objects.filter(partner =instance.partner,created_at__gt = date_mileston)
    # sửa chi phí
    update_or_created_expense_partner(instance,account_partner, description_type='transaction_fee')
    if instance.position == 'sell':
        update_or_created_expense_partner(instance,account_partner, description_type='tax')
    # sửa danh mục
    portfolio_partner = PortfolioPartner.objects.filter(stock =instance.stock, account= account_partner).first()
    stock_transaction = transaction.filter(stock = instance.stock)
    sum_sell = sum(item.qty for item in stock_transaction if item.position =='sell')
    item_buy = stock_transaction.filter( position = 'buy')
    
    if portfolio_partner:
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
                                           
        portfolio_partner.receiving_t2 = receiving_t2
        portfolio_partner.receiving_t1 = receiving_t1
        portfolio_partner.on_hold = on_hold
        portfolio_partner.save()
    # sửa tài khoản    
    item_all_sell = transaction.filter(position = 'sell')
    cash_t0, cash_t1, cash_t2 =0,0,0
    total_value_buy= sum(i.net_total_value for i in transaction if i.position =='buy')
    today  = datetime.now().date()  
    if item_all_sell:
        for item in item_all_sell:
            if define_t_plus(item.date,today) == 0:
                cash_t2 += item.total_value 
            elif define_t_plus(item.date, today) == 1:
                cash_t1+= item.total_value 
            else:
                cash_t0 += item.total_value 
        account_partner.cash_t2 = cash_t2
        account_partner.cash_t1 = cash_t1
        account_partner.cash_t0 = cash_t0
    account_partner.total_buy_trading_value = total_value_buy
    account_partner.net_trading_value = sum(item.net_total_value for item in transaction)
    account_partner.interest_cash_balance = partner_define_interest_cash_balace(account_partner,instance.partner,date_mileston)
    account_partner.save()

    
@receiver([post_save, post_delete], sender=BankCashTransfer)
def save_field_account_partner(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if instance.type == 'trade_transfer' and instance.partner:
        account = instance.account
        account_partner , created= AccountPartner.objects.get_or_create(
        account=account,
        partner=instance.partner,
        defaults={'description': ''}  # Trường 'description' không bị cập nhật
            )
        milestone_account = AccountMilestone.objects.filter(account =account).order_by('-created_at').first()
        if milestone_account:
            date_mileston = milestone_account.created_at
        else:
            date_mileston = account.created_at
        amount =instance.amount*-1
        
        if not created:
            cash_items = BankCashTransfer.objects.filter(account=account,partner =instance.partner,created_at__gt = date_mileston)
            account_partner.net_cash_flow = sum(-item.amount for item in cash_items)
           

        else:
            account_partner.net_cash_flow +=  amount
            
        account_partner.save()
