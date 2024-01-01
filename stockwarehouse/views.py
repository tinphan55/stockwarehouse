from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from operation.models import *
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm


def LoginUser(request):
    pk = request.user.username
    if pk=="":
        return render(request,"stockwarehouse/login.html")
    else:
        return redirect('customer_detail',pk=pk)

@login_required(login_url="/loginuser/")
def customer_view(request, pk):
    account = get_object_or_404(Account, pk=pk)
    port = Portfolio.objects.filter(account=account, sum_stock__gt=0)
    transaction = Transaction.objects.filter(account=account)
    cash = CashTransfer.objects.filter(account=account)
    expense = ExpenseStatement.objects.filter(account=account)
    list_margin = StockListMargin.objects.all()

    context = {
        'account': account,
        'port': port,
        'transaction': transaction,
        'cash': cash,
        'expense': expense,
        'list_margin': list_margin,
    }

    if request.user.username == str(pk):
        template = loader.get_template('stockwarehouse/customer_home.html')
        return HttpResponse(template.render(context, request))
    else:
        return HttpResponse("<h1>Permission denied<h1>")
    



# def clicklogin(request):
#     if request.method!="POST":
#         return HttpResponse("<h1> Methoid not allowed<h1>")
#     else:
#         username = request.POST.get('username','')
#         password = request.POST.get('password','')
        
#         user=authenticate(username=username,password=password)
#         try:
#             if user!=None:
#                 login(request,user)
#                 pk=user.pk
#                 return redirect('customer_detail', pk=pk)
#                 # return HttpResponseRedirect('homepage')
#             else:
#                 messages.warning(request, 'Mật khẩu không đúng.')
#                 return HttpResponseRedirect('loginuser')

#         except user.DoesNotExist:
#             # Xử lý khi tài khoản không tồn tại
#             messages.warning(request, 'Tài khoản không tồn tại.')

def clicklogin(request):
    if request.method != "POST":
        return HttpResponse("<h1> Method not allowed<h1>")
    else:
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_authenticated:
                # Nếu người dùng đã đăng nhập, sử dụng user.pk
    
                return redirect('customer_detail', pk=username)
            else:
                # Xử lý nếu người dùng chưa đăng nhập
                # Ví dụ: return redirect('home')
                return HttpResponseRedirect(reverse('loginuser'))
        else:
            messages.warning(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
            return HttpResponseRedirect(reverse('loginuser'))



def LogoutUser(request):
    logout(request)
    request.user=None
    # return HttpResponseRedirect("loginuser")       
    return redirect('loginuser')     


@login_required(login_url="/loginuser/")
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Đảm bảo người dùng vẫn đăng nhập
            messages.success(request, 'Mật khẩu đã được thay đổi thành công.')
            return redirect('change_password')
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin đầu vào.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'stockwarehouse/change_password.html', {'form': form})