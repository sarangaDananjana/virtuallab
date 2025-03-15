from django import forms


class SearchForm(forms.Form):
    query = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Search...',
        'class': 'form-control',
    }))
