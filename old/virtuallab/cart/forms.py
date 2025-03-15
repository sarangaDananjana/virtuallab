from django import forms
from . models import Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name',
                  'e_mail', 'phone_number', 'payment_proof', 'address']
