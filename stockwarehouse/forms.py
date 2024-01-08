# forms.py
from django import forms

class SellingForm(forms.Form):
    selling_price = forms.FloatField(label='Giá bán')
    selling_date = forms.DateField(label='Ngày bán')
