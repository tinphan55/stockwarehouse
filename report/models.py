from django.db import models
from datetime import datetime, timedelta
from operation.models import *
from cpd.models import *

# Create your models here.
class SaleReportParam(models.Model):
    month_year = models.DateField(verbose_name='Tháng/Năm')
    month_year_str = models.CharField(max_length=255, blank=True, null=True, verbose_name='Tháng/Năm')
    ratio_fee_transaction_securities = models.FloatField(verbose_name='Tỷ lệ PGD trả CTCK' )
    ratio_tax_broker= models.FloatField(verbose_name='Tỷ lệ thuế thu nhập broker' )
    ratio_commission_securities= models.FloatField(verbose_name='Tỷ lệ hoa hồng CTCK trả broker')
    ratio_interest_partner = models.FloatField(verbose_name='Tỷ lệ lãi trả đối tác')
    total_interest_fee_paid_securities = models.FloatField(verbose_name='Tổng lãi vay trả CTCK')
    total_depository_fees = models.FloatField(verbose_name='Tổng phí lưu kí')

    def __str__(self):
            return f"Báo cáo tháng {self.month_year_str}"
    
    def save(self, *args, **kwargs):
        self.month_year_str = "{}/{}".format(str(self.month_year.month), str(self.month_year.year))
        super(SaleReportParam , self).save(*args, **kwargs)
    




class SaleReport(models.Model):
    month_year_str = models.CharField(max_length=255, blank=True, null=True, verbose_name='Tháng/Năm')
    month_year = models.ForeignKey(SaleReportParam,on_delete=models.CASCADE, verbose_name='Tháng/Năm')
    transaction_fee_revenue = models.FloatField(verbose_name='Doanh thu phí giao dịch', blank=True, null=True)
    interest_revenue = models.FloatField(verbose_name='Doanh thu lãi', blank=True, null=True)
    advance_fee_revenue = models.FloatField(verbose_name='Doanh thu phí tiền ứng', blank=True, null=True)
    brokerage_commission = models.FloatField(verbose_name='Hoa hồng môi giới', blank=True, null=True)
    total_revenue = models.FloatField(verbose_name='Tổng doanh thu', blank=True, null=True)
    transaction_costs_paid_securities = models.FloatField(verbose_name='Chi phí giao dịch trả CTCK', blank=True, null=True)
    interest_costs_paid_securities = models.FloatField(verbose_name='Chi phí lãi trả CTCK', blank=True, null=True)
    depository_fees = models.FloatField(verbose_name='Phí lưu kí chứng khoán', blank=True, null=True)
    interest_paid_partners = models.FloatField(verbose_name='Lãi suất trả cho đối tác', blank=True, null=True)
    advance_paid_partners = models.FloatField(verbose_name='Phí ứng trả cho đối tác', blank=True, null=True)
    total_cost = models.FloatField(verbose_name='Tổng chi phí', blank=True, null=True)
    cp_commission = models.FloatField(verbose_name='Hoa hồng CP', blank=True, null=True)
    salary = models.FloatField(verbose_name='Lương', blank=True, null=True)
    other_expense = models.FloatField(verbose_name='Chi phí khác', blank=True, null=True)
    total_expense = models.FloatField(verbose_name='Tổng chi phí', blank=True, null=True)
    net_profit = models.FloatField(verbose_name='Lợi nhuận', blank=True, null=True)

    def __str__(self):
        return f"Report for {self.month_year_str}"
    def save(self, *args, **kwargs):
        self.month_year_str = self.month_year.month_year_str
        self.total_revenue = self.transaction_fee_revenue + self.interest_revenue + self.advance_fee_revenue+self.brokerage_commission
        self.total_cost = self.transaction_costs_paid_securities + self.depository_fees + self.interest_paid_partners  + self.interest_costs_paid_securities
        # self.total_expense = self.cp_commission + self.other_expense + self.salary
        self.total_expense = 0
        self.net_profit = self.total_revenue -self.total_cost -self.total_expense
        super(SaleReport , self).save(*args, **kwargs)

def define_period_date(month_year):
    end_period = month_year.replace(day=20)
    # Tính ngày đầu tiên của tháng trước đó
    start_period = month_year - timedelta(days=month_year.day)
    start_period = start_period.replace(day=20)
    return start_period, end_period

def run_sale_report(month_year_str):
    cp_item = ClientPartnerCommission.objects.filter(month_year_str = month_year_str)
    report = SaleReportParam.objects.get(month_year_str = month_year_str)
    period_date = define_period_date(report.month_year)
    transaction_item = Transaction.objects.filter(date__gte = period_date[0],date__lte = period_date[1])
    expense = ExpenseStatement.objects.filter(date__gte = period_date[0],date__lte = period_date[1])
    advance_fee_revenue = sum(item.amount for item in expense if item.type == 'advance_fee')
    interest_revenue = sum(item.amount for item in expense if item.type == 'interest')
    total_value = sum(item.total_value for item in transaction_item)
    transaction_fee_revenue = total_value * get_transaction_fee_default()
    transaction_costs_paid_securities = total_value *report.ratio_fee_transaction_securities
    interest_costs_paid_securities = report.total_interest_fee_paid_securities
    depository_fees = report.total_depository_fees
    interest_paid_partners = sum(item.interest_cash_balance *report.ratio_interest_partner for item in expense if item.type == 'interest' )
    advance_paid_partners = sum(item.advance_cash_balance *report.ratio_interest_partner for item in expense if item.type == 'advance_fee' )
    cp_commission = sum(item.total_commission for item in cp_item)
    brokerage_commission = (total_value*report.ratio_fee_transaction_securities - total_value*0.0003)*report.ratio_commission_securities*(1-report.ratio_tax_broker)
    return {
        'month_year' : report,
        'transaction_fee_revenue': transaction_fee_revenue,
        'interest_revenue': interest_revenue,
        'advance_fee_revenue': advance_fee_revenue,
        'brokerage_commission':brokerage_commission,
        'transaction_costs_paid_securities': transaction_costs_paid_securities,
        'interest_costs_paid_securities': interest_costs_paid_securities,
        'depository_fees': depository_fees,
        'interest_paid_partners': interest_paid_partners,
        'advance_paid_partners': advance_paid_partners,
        'cp_commission': cp_commission,
    }
    
def update_or_create_sale_report(month_year_str):
    value = run_sale_report(month_year_str)
    # Kiểm tra và gán giá trị mặc định 0 cho các trường nếu không tồn tại trong value
    default_values = {
        'transaction_fee_revenue': 0,
        'interest_revenue': 0,
        'advance_fee_revenue': 0,
        'brokerage_commission': 0,
        'transaction_costs_paid_securities': 0,
        'interest_costs_paid_securities': 0,
        'depository_fees': 0,
        'interest_paid_partners': 0,
        'advance_paid_partners': 0,
        'cp_commission': 0,
    }
    for key in default_values:
        value[key] = value.get(key, default_values[key])

    try:
        # Kiểm tra xem có bản ghi SaleReport nào có month_year_str tương ứng không
        sale_report = SaleReport.objects.get(month_year_str=month_year_str)
        
        # Cập nhật các trường của bản ghi đã tồn tại với giá trị từ value
        for key, val in value.items():
            setattr(sale_report, key, val)
        
        # Lưu lại các thay đổi
        sale_report.save()
        
        return sale_report
    except SaleReport.DoesNotExist:
        # Nếu không có bản ghi nào thỏa mãn điều kiện, tạo mới SaleReport với value
        sale_report = SaleReport(month_year_str=month_year_str, **value)
        sale_report.save()
        
        return sale_report