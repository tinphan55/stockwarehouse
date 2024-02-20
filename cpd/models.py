from django.db import models
from django.contrib.auth.models import User, Group
from datetime import datetime, timedelta
from django.db.models import F
# Create your models here.

class ClientPartnerInfo (models.Model):
    RANK_CHOICES = [
        ('1', '1'),
        ('2', '2'),
        ('3','3'),
    ]
    full_name = models.CharField(max_length= 50, verbose_name='Tên đầy đủ')
    phone = models.IntegerField(null=False, verbose_name='Điện thoại', unique=True)
    email = models.EmailField(max_length=100)
    created_date = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    address = models.CharField(max_length=100, null= True, blank = True, verbose_name='Địa chỉ')
    birthday = models.DateField(null=True, blank = True, verbose_name='Ngày sinh')
    note =  models.CharField(max_length= 200,null=True, blank = True, verbose_name='Ghi chú')
    company = models.CharField(max_length= 50,null=True, blank=True, verbose_name='Công ty')
    rank= models.CharField(max_length=4,choices=RANK_CHOICES, null=False, blank=False,verbose_name = 'Cấp')
    commission = models.FloatField(default = 0.3, verbose_name='Tỷ lệ chia hoa hồng')
    class Meta:
        verbose_name = 'Đối tác giới thiệu KH'
        verbose_name_plural = 'Đối tác giới thiệu KH'

    def __str__(self):
        return str(self.full_name) + '_' + str(self.pk)
    
    def save(self, *args, **kwargs):
        if self.rank ==1:
            self.commission = 0.2
        elif self.rank ==2:
            self.commission = 0.4
        else:
            self.commission =0
        super(ClientPartnerInfo, self).save(*args, **kwargs)


class ClientPartnerCommission (models.Model):
    cp = models.ForeignKey(ClientPartnerInfo,on_delete=models.CASCADE, verbose_name= 'Người giới thiệu' )
    month_year_str  = models.CharField(blank=True, null=True,verbose_name = 'Tháng/Năm' )
    month_year = models.DateField()
    user_created = models.ForeignKey(User,on_delete=models.CASCADE,null=True, blank= True,                   verbose_name="Người tạo")
    user_modified = models.CharField(max_length=150, blank=True, null=True,verbose_name="Người chỉnh sửa")
    total_value= models.FloatField(default=0, verbose_name= 'Tổng Giá trị GD')
    trading_fee_spreads = models.FloatField(default=0, verbose_name= 'DT chênh lệch PGD')
    commission_back = models.FloatField(default=0, verbose_name= 'HH HSC trả')
    total_revenue = models.FloatField(default=0, verbose_name= 'Tổng Doanh thu tính thu nhập')
    total_commission = models.FloatField(default=0, verbose_name= 'Thu nhập CTV')
    
    class Meta:
         verbose_name = 'Thu nhập CTV '
         verbose_name_plural = 'Thu nhập CTV '
    def __str__(self):
        return self.cp.full_name
    
    def save(self, *args, **kwargs):
        self.month_year_str = "{}/{}".format(self.month_year.month, self.month_year.year)
        self.trading_fee_spreads = self.total_value*0.0005
        self.commission_back = (self.total_value*0.0015 -self.total_value*0.0003)*0.85*0.9
        self.total_revenue = self.trading_fee_spreads + self.commission_back
        self.total_commission = self.total_revenue * self.cp.commission
        super(ClientPartnerCommission , self).save(*args, **kwargs)


def define_month_year_cp_commission(instance):
    if instance.date.day >=21:
        month_year =  datetime(instance.date.year, instance.date.month, 1)
    else:
        month_year = instance.date - timedelta(days=instance.date.day)
        month_year = month_year.replace(day=1)
    return instance


def cp_create_transaction(account, instance, month_year):
    ClientPartnerCommission.objects.update_or_create(
        cp=account.cpd,
        month_year=month_year,
        defaults={
            'total_value': F('total_value') + instance.total_value,}
        )
def cp_update_transaction(account, instance,transaction_cpd , month_year):
    end_period = month_year.replace(day=20)
    # Tính ngày đầu tiên của tháng trước đó
    start_period = month_year - timedelta(days=month_year.day)
    start_period = start_period.replace(day=20)
    total_value_items = transaction_cpd.filter(date__gt =start_period,date__lte = end_period )
    commission_record = ClientPartnerCommission.objects.get(cp=account.cpd, month_year=month_year)
    commission_record.total_value = sum (item.total_value for item in total_value_items)
    commission_record.save()
    
    






