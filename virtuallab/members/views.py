from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.models import User


def login_user(request):
    if request.method == 'POST':
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')

        else:
            messages.success(request, 'There was an error Loging In')
            return redirect('login')
    else:
        return render(request, 'login.html', {})


def logout_user(request):
    logout(request)
    messages.success(request, 'You were logged out')
    return redirect('home')


def register_user(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():

            user = form.save(commit=False)

            email = request.POST.get('email')

            if email:
                user.email = email
                user.save()

                username = form.cleaned_data['username']
                password = form.cleaned_data['password1']
                user = authenticate(username=username, password=password)
                if user:
                    login(request, user)
                    messages.success(request, ("Registration Successful!"))
                    return redirect('home')
            else:
                messages.error(request, "Email address is required.")
    else:
        form = UserCreationForm()

    return render(request, 'register_user.html', {
        'form': form,
    })
