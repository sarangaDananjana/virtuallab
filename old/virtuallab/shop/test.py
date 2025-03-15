from django.http import JsonResponse  # Import JsonResponse


def games_shop(request):
    games = Game.objects.all()

    if Cart.objects.filter(user=request.user.id).exists():
        shop_cart = Cart.objects.filter(user=request.user).get()
        storage_device = shop_cart.cart_storage
        available_storage = storage_device - \
            sum(game.size for game in shop_cart.cart_game.all())

        if request.method == "POST":
            game_id = request.POST.get("game_id")
            action = request.POST.get("action")

            if game_id:
                game = Game.objects.get(id=game_id)

                if action == "add":
                    if not shop_cart.cart_game.filter(id=game_id).exists() and game.size <= available_storage:
                        shop_cart.cart_game.add(game)
                        available_storage -= game.size
                        shop_cart.save()
                        if request.is_ajax():
                            return JsonResponse({'message': 'Game added to cart', 'success': True})
                elif action == "remove":
                    if shop_cart.cart_game.filter(id=game.id).exists():
                        shop_cart.cart_game.remove(game)
                        available_storage += game.size
                        shop_cart.save()
                        if request.is_ajax():
                            return JsonResponse({'message': 'Game removed from cart', 'success': True})

            if request.is_ajax():
                return JsonResponse({'message': 'Invalid action', 'success': False}, status=400)

        return render(request, "shop/shop.html", {
            "games": games,
            "cart": shop_cart,
            "available_storage": available_storage
        })

    return render(request, "shop/shop.html", {"games": games})
