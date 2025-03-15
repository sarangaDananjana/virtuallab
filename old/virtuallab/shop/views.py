from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from cart.models import Cart
from .models import StorageDevice, FeaturedProducts, Game
from django.db.models import Q


def home(request):
    featured_products = FeaturedProducts.objects.all()
    return render(request, 'shop/home.html', {'featured_products': featured_products})


def games_shop(request):

    games = Game.objects.all()

    if Cart.objects.filter(user=request.user.id).exists():
        shop_cart = Cart.objects.filter(user=request.user).get()
        storage_full_capacity = shop_cart.cart_storage
        available_storage = storage_full_capacity -\
            sum(game.size for game in shop_cart.cart_game.all())

        if request.method == "POST":
            game_id = request.POST.get("game_id")
            action = request.POST.get("action")
            if game_id:
                game = Game.objects.get(id=game_id)

                if action == "add":
                    storage_device = shop_cart.cart_storage
                    available_storage = storage_device - \
                        sum(game.size for game in shop_cart.cart_game.all())
                    if not shop_cart.cart_game.filter(id=game_id).exists() and game.size <= available_storage:
                        shop_cart.cart_game.add(game)
                        available_storage -= game.size
                        shop_cart.save()

                elif action == "remove":
                    # Remove the game if it exists in the cart
                    if shop_cart.cart_game.filter(id=game.id).exists():
                        shop_cart.cart_game.remove(game)
                        available_storage += game.size
                        shop_cart.save()

        return render(request, "shop/shop.html", {
            "games": games,
            "cart": shop_cart,
            "available_storage": available_storage,
            'storage_full_capacity': storage_full_capacity
        })

    else:

        return render(request, "shop/shop.html", {
            "games": games,
        })


@login_required
def select_storage_device(request):
    user = request.user
    # Fetch the user's cart (if any)
    cart = Cart.objects.filter(user=user).first()

    total_game_size = 0
    if cart:
        total_game_size = sum(game.size for game in cart.cart_game.all())

    storage_devices = StorageDevice.objects.all()

    for device in storage_devices:
        device.is_selected = cart and cart.cart_storage == device.usable_capacity
        device.can_accommodate = device.usable_capacity >= total_game_size

    if request.method == "POST":
        storage_device_id = request.POST.get("storage_device_id")
        selected_device = StorageDevice.objects.get(id=storage_device_id)

        # Create or update the cart for the user
        if cart:
            cart.cart_storage = selected_device.usable_capacity
            cart.cart_price = selected_device.price
            cart.cart_storage_name = selected_device.size
            cart.cart_storage_category = selected_device.category
            cart.save()
        else:
            cart = Cart.objects.create(
                user=user, cart_storage=selected_device.usable_capacity, cart_price=selected_device.price, cart_storage_name=selected_device.size, cart_storage_category=selected_device.category)

        # Reload the page after saving
        return redirect("select_storage_device")

    context = {"storage_devices": storage_devices, "cart": cart}
    return render(request, "shop/select_storage.html", context)


def game_detail(request, slug):
    game = get_object_or_404(Game, slug=slug)
    if Cart.objects.filter(user=request.user.id).exists():
        shop_cart = Cart.objects.filter(user=request.user).get()
        storage_device = shop_cart.cart_storage
        available_storage = storage_device -\
            sum(game.size for game in shop_cart.cart_game.all())

        if request.method == "POST":
            game_id = request.POST.get("game_id")
            action = request.POST.get("action")
            if game_id:
                game = Game.objects.get(id=game_id)

                if action == "add":
                    storage_device = shop_cart.cart_storage
                    available_storage = storage_device - \
                        sum(game.size for game in shop_cart.cart_game.all())
                    if not shop_cart.cart_game.filter(id=game_id).exists() and game.size <= available_storage:
                        shop_cart.cart_game.add(game)
                        available_storage -= game.size
                        shop_cart.save()

                elif action == "remove":
                    # Remove the game if it exists in the cart
                    if shop_cart.cart_game.filter(id=game.id).exists():
                        shop_cart.cart_game.remove(game)
                        available_storage += game.size
                        shop_cart.save()

        return render(request, "shop/product_detail.html", {
            "game": game,
            "cart": shop_cart,
            "available_storage": available_storage
        })

    # Pass the product data to the template
    return render(request, 'shop/product_detail.html', {'game': game})


def search_games(request):
    query = request.GET.get('searched', '')
    if Cart.objects.filter(user=request.user.id).exists():
        shop_cart = Cart.objects.filter(user=request.user).get()
        storage_full_capacity = shop_cart.cart_storage
        available_storage = storage_full_capacity -\
            sum(game.size for game in shop_cart.cart_game.all())

        if request.method == "POST":
            game_id = request.POST.get("game_id")
            action = request.POST.get("action")
            if game_id:
                game = Game.objects.get(id=game_id)

                if action == "add":
                    storage_device = shop_cart.cart_storage
                    available_storage = storage_device - \
                        sum(game.size for game in shop_cart.cart_game.all())
                    if not shop_cart.cart_game.filter(id=game_id).exists() and game.size <= available_storage:
                        shop_cart.cart_game.add(game)
                        available_storage -= game.size
                        shop_cart.save()

                elif action == "remove":
                    # Remove the game if it exists in the cart
                    if shop_cart.cart_game.filter(id=game.id).exists():
                        shop_cart.cart_game.remove(game)
                        available_storage += game.size
                        shop_cart.save()

                        return render(request, 'shop/search_games.html', {'query': query,
                                                                          "cart": shop_cart,
                                                                          "available_storage": available_storage,
                                                                          'storage_full_capacity': storage_full_capacity})

    if query:
        # Example: Searching in 'name' and 'description' fields
        games = Game.objects.filter(
            Q(title__icontains=query))

        return render(request, 'shop/search_games.html', {'query': query, "games": games, })
