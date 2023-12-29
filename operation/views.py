import math
from django.shortcuts import render
from django.http import HttpResponse
from .models import *
from django.template import loader
from statistics import mean
from django.http import JsonResponse
from infotrading.models import get_list_stock_price


def warehouse(request):
    # Xử lý logic cho trang warehouse ở đây
    if request.method == 'POST':
        # Xử lý logic khi có yêu cầu POST từ form
        action = request.POST.get('action', None)

        if action == 'update_market_price':
            # Xử lý cập nhật giá thị trường cho các cổ phiếu trong danh sách
            stock_list = Portfolio.objects.values_list('stock', flat=True).distinct()
            stock_list_python = list(stock_list)
            get_list_stock_price(stock_list_python)



        elif action == 'calculate_max_qty_buy':
            # Xử lý tính toán số lượng tối đa có thể mua
            account = float(request.POST['account'])
            ticker = request.POST['ticker'].upper()
            price = float(request.POST['price'])
            account = Account.objects.get(pk=account)
            margin = StockListMargin.objects.filter(stock=ticker).first()
            max_value = 0
            if account.excess_equity > 0 and margin:
                max_value = abs(account.excess_equity / (margin.initial_margin_requirement/100))
            
                
            qty = math.floor(int(max_value / price))
            return JsonResponse({'qty': '{:,.0f}'.format(qty)})

    # Trả về template chung cho cả hai trường hợp
    return render(request, 'stockwarehouse/warehouse.html')


def customer_view(request, pk):
    template = loader.get_template('stockwarehouse/tradingweb.html')
    account = Account.objects.get(pk=pk)
    port = Portfolio.objects.filter(account = account, sum_stock__gt=0)
    transaction = Transaction.objects.filter(account = account)
    cash = CashTransfer.objects.filter(account=account)
    expense = ExpenseStatement.objects.filter(account=account)
    list_margin = StockListMargin.objects.all()
    context = {
        'account':account,
        'port': port,
        'transaction':transaction,
        'cash':cash,
        'expense':expense,
        'list_margin':list_margin,


    }
    return HttpResponse(template.render(context, request))