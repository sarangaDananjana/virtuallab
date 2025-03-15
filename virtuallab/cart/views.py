from django.shortcuts import render, redirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from shop.models import StorageDevice, Game
from .models import Cart, Order
from .forms import OrderForm


def cart_view(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_games = Cart.objects.filter(
            user=request.user).prefetch_related('cart_game')
    except Cart.DoesNotExist:
        return redirect("select_storage_device")

    # Calculate total storage used by selected games
    total_game_size = sum(game.size for game in cart.cart_game.all())
    available_space = cart.cart_storage - total_game_size

    # Fetch available storage devices with usable capacity greater than total_game_size
    cart = Cart.objects.get(user=request.user)
    available_storage_devices = StorageDevice.objects.filter(
        usable_capacity__gte=total_game_size)
    cart_total_value = int(cart.cart_price) + 450

    if request.method == "POST":
        # Check if it's a game removal request
        game_id = request.POST.get("game_id")
        if game_id:
            game = Game.objects.get(id=game_id)
            if game in cart.cart_game.all():
                cart.cart_game.remove(game)
                cart.save()
            return redirect("cart")  # Refresh the page

        # Check if it's a storage device change request
        storage_device_id = request.POST.get("storage_device")
        if storage_device_id:
            new_storage_device = StorageDevice.objects.get(
                id=storage_device_id)
            if new_storage_device.usable_capacity >= total_game_size:

                cart.cart_storage = new_storage_device.usable_capacity
                cart.cart_price = new_storage_device.price
                cart.cart_storage_name = new_storage_device.size
                cart.cart_storage_category = new_storage_device.category
                cart.save()
            # Refresh the page
            return redirect("cart")

    return render(request, "cart/cart.html", {
        "cart": cart,
        "available_storage_devices": available_storage_devices,
        "total_game_size": total_game_size,
        'available_space': available_space,
        'cart_games': cart_games,
        'cart_total_value': cart_total_value
    })


def order_success(request):
    return render(request, 'cart/order_success.html')


def checkout(request):

    form = OrderForm()
    cart = Cart.objects.get(user=request.user)
    cart_total_value = int(cart.cart_price) + 450

    if request.method == 'POST':
        user_data = OrderForm(request.POST, request.FILES)
        checkout_cart = Cart.objects.filter(user=request.user).get()
        orderd_storage = checkout_cart.cart_storage
        user_data = {
            # Replace 'field1' with actual field names
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'phone_number': request.POST.get('phone_number'),
            'e_mail': request.POST.get('e_mail'),
            'address': request.POST.get('address'),
            'payment_proof': request.FILES.get('payment_proof'),
            # Add more fields as necessary
        }
        order = Order.objects.create(
            user=request.user, orderd_storage=orderd_storage, order_value=checkout_cart.cart_price, **user_data)
    # Transfer cart_games to order_games
        order.game_list.set(checkout_cart.cart_game.all())
        order.save()

        checkout_cart.delete()

        return redirect("order_success")
    checkout_cart = Cart.objects.filter(user=request.user).get()
    cart_games = checkout_cart.cart_game.all() if checkout_cart else []

    return render(request, 'cart/checkout.html', {'form': form,
                                                  'checkout_cart': checkout_cart,
                                                  'cart_games': cart_games,
                                                  'cart_total_value': cart_total_value})


@login_required
def orders(request):

    user = request.user

    pending_orders = Order.objects.filter(
        user=user, order_status=Order.PENDING_PAYMENT).prefetch_related('game_list')
    identified_orders = Order.objects.filter(
        user=user, order_status=Order.PAYMENT_IDENTIFIED).prefetch_related('game_list')
    completed_orders = Order.objects.filter(
        user=user, order_status=Order.PAYMENT_COMPLETE).prefetch_related('game_list')
    failed_orders = Order.objects.filter(
        user=user, order_status=Order.PAYEMENT_FAILED).prefetch_related('game_list')

    context = {
        'pending_orders': pending_orders,
        'identified_orders': identified_orders,
        'completed_orders': completed_orders,
        'failed_orders': failed_orders,
        'user': user
    }

    return render(request, 'cart/orders.html', context)
