from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse, NoReverseMatch
from urllib.parse import quote
from django.db import models
from django.db.models import Prefetch
from decimal import Decimal
from .models import Order, ReservedSlot, Ticket, TicketPhoto, ReservedSlot, GameRequest, Product, StorageDevice, Cart, CartItem, CartStorageItem
from django.contrib.auth import authenticate, login as dj_login, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_GET
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction, IntegrityError

User = get_user_model()

# ---- HTML pages (TemplateHTMLRenderer) ----


def _redirect_to_login(request):
    login_url = reverse("login-page")
    return redirect(f"{login_url}?next={quote(request.get_full_path())}")


@api_view(["GET"])  # Home
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def home_page(request):
    """this renders the Home HTML page"""
    user_initial = None
    if request.user.is_authenticated:
        name = request.user.get_username() or getattr(request.user, "email", "") or ""
        if name:
            user_initial = name[0].upper()
    return Response({"user": request.user, "user_initial": user_initial}, template_name="home.html")


@api_view(["GET"])  # Login page (renders form)
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def login_page(request):
    """this renders the login HTML page"""
    return Response({}, template_name="login.html")


@api_view(["GET"])  # Register page (renders form)
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def register_page(request):
    """this renders the register HTML page"""
    return Response({}, template_name="register.html")

# ---- JSON APIs ----


@api_view(["POST"])  # Expects: { username OR email, password }
@renderer_classes([JSONRenderer])
def api_login(request):
    """this api get the user entered username and password and validate the user for login"""
    identifier = request.data.get("username") or request.data.get("email")
    password = request.data.get("password")
    if not identifier or not password:
        return Response({"detail": "username/email and password are required."},
                        status=status.HTTP_400_BAD_REQUEST)

    # login by username OR email
    username = identifier
    if "@" in identifier:
        try:
            user_obj = User.objects.get(email__iexact=identifier)
            username = user_obj.username
        except User.DoesNotExist:
            return Response({"detail": "No account with that email."},
                            status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({"detail": "Invalid credentials."},
                        status=status.HTTP_400_BAD_REQUEST)

    dj_login(request, user)
    return Response({
        "detail": "Login successful.",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone_number": getattr(user, "phone_number", None),
        },
    })


@api_view(["POST"])  # Expects: { username, email, phone_number, password }
@renderer_classes([JSONRenderer])
def api_register(request):
    """this is the user register api that saves new user info in the backend"""
    username = request.data.get("username")
    email = request.data.get("email")
    phone_number = request.data.get("phone_number")
    password = request.data.get("password")

    missing = [f for f, v in [
        ("username", username),
        ("email", email),
        ("phone_number", phone_number),
        ("password", password),
    ] if not v]
    if missing:
        return Response({"detail": f"Missing field(s): {', '.join(missing)}."},
                        status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username__iexact=username).exists():
        return Response({"detail": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(email__iexact=email).exists():
        return Response({"detail": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(phone_number__iexact=phone_number).exists():
        return Response({"detail": "Phone number already in use."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=username,
        email=email,
        phone_number=phone_number,
        password=password,
    )
    # Optional: auto-login after register
    dj_login(request, user)

    return Response({
        "detail": "Registration successful.",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number,
        },
    }, status=status.HTTP_201_CREATED)


# NEW: Render the submit ticket page with the user's orders
@api_view(["GET"])  # Support page (renders template)
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def ticket_submit_page(request):
    """this renders the 4 step ticket submition HTML page"""
    if not request.user.is_authenticated:
        return _redirect_to_login(request)

    user_initial = None
    if request.user.is_authenticated:
        name = request.user.get_username() or getattr(request.user, "email", "") or ""
        if name:
            user_initial = name[0].upper()

    # Load this user's orders (if logged in); otherwise empty queryset
    orders = Order.objects.none()
    if request.user.is_authenticated:
        orders = Order.objects.filter(
            users=request.user).order_by("-ordered_at")

    # Initial date for slot availability (today unless ?date=YYYY-MM-DD is passed)
    date_str = request.query_params.get("date") or request.GET.get("date")
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    # Unavailable slots for the selected date (used only if you want server-side prefill)
    unavailable_slots = list(
        ReservedSlot.objects.filter(
            date=selected_date).values_list("slot", flat=True)
    )

    return Response(
        {
            "user": request.user,
            "user_initial": user_initial,
            "orders": orders,
            # Optional: if you later want to pre-apply these in the template
            "selected_date": selected_date,
            "unavailable_slots": unavailable_slots,
        },
        template_name="submit_ticket.html",
    )


# NEW: JSON API to query reserved/unavailable slots for a given date
@api_view(["GET"])  # /api/slots/?date=YYYY-MM-DD
@renderer_classes([JSONRenderer])
@ensure_csrf_cookie
def api_reserved_slots(request):
    """
    this api grab the reserved slot informations for the ticet submition process 
    so the user can't book a already booked slot
    """
    date_str = request.query_params.get("date")
    if not date_str:
        return Response({"detail": "Missing 'date' query param (YYYY-MM-DD)."}, status=400)

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    booked = list(ReservedSlot.objects.filter(
        date=d).values_list("slot", flat=True))
    all_slots = [choice[0] for choice in ReservedSlot.Slot.choices]
    available = [s for s in all_slots if s not in booked]

    return Response({
        "date": d.isoformat(),
        "unavailable": booked,
        "available": available,
    })


@login_required
@require_POST
def api_create_ticket(request):
    """
    Create Ticket + TicketPhoto[] + ReservedSlot (1-hour). Returns JSON.
    """
    data = request.POST
    files = request.FILES

    source = data.get("source")
    if source not in (Ticket.Source.DARAZ, Ticket.Source.VIRTUAL_LAB):
        return JsonResponse({"ok": False, "error": "Invalid source."}, status=400)

    # If Virtual Lab, validate the chosen order belongs to the user
    order = None
    if source == Ticket.Source.VIRTUAL_LAB:
        oid = data.get("order_id")
        if oid:
            try:
                order = Order.objects.filter(users=request.user).get(id=oid)
            except Order.DoesNotExist:
                return JsonResponse({"ok": False, "error": "Order not found."}, status=404)

    subject = (data.get("subject") or "").strip()
    description = (data.get("description") or "").strip()
    if not subject or not description:
        return JsonResponse({"ok": False, "error": "Subject and description are required."}, status=400)

    # Daraz extra info (your Ticket model doesn’t have explicit fields;
    # we safely prepend them inside description so nothing is lost).
    # If you prefer dedicated fields, we can add them later.
    if source == Ticket.Source.DARAZ:
        d_num = data.get("daraz_order_number") or "—"
        d_date = data.get("daraz_order_date") or "—"
        description = f"[Daraz Order #{d_num} on {d_date}]\n{description}"

    visit_date = parse_date(data.get("visit_date"))
    slot = data.get("slot")
    valid_slots = dict(ReservedSlot.Slot.choices).keys()
    if not visit_date or slot not in valid_slots:
        return JsonResponse({"ok": False, "error": "Valid date and slot are required."}, status=400)

    video = files.get("video")
    photos = files.getlist("photos")
    if len(photos) > 5:
        return JsonResponse({"ok": False, "error": "Up to 5 photos allowed."}, status=400)

    try:
        with transaction.atomic():
            ticket = Ticket.objects.create(
                source=source,
                order=order,
                subject=subject,
                description=description,
                video=video if video else None,
            )
            ticket.users.add(request.user)  # your model uses M2M to users

            for img in photos:
                TicketPhoto.objects.create(ticket=ticket, image=img)

            reservation = ReservedSlot.objects.create(
                ticket=ticket,
                user=request.user,
                date=visit_date,
                slot=slot,
            )
    except IntegrityError:
        # unique_together(date, slot) collision -> already taken
        return JsonResponse(
            {"ok": False, "error": "Selected time slot is already reserved. Please choose another."},
            status=409,
        )

    return JsonResponse(
        {
            "ok": True,
            "ticket": {"id": ticket.id, "reference": ticket.reference},
            "reservation": {"date": str(reservation.date), "slot": reservation.slot},
        },
        status=201,
    )


@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
def tickets_page(request):
    """
    this renders the tickets page HTML for the user. in there he can see all teh tickets he submited
    """
    if not request.user.is_authenticated:
        return _redirect_to_login(request)

    user_initial = None
    if request.user.is_authenticated:
        name = request.user.get_username() or getattr(request.user, "email", "") or ""
        if name:
            user_initial = name[0].upper()

    qs = (
        Ticket.objects.filter(users=request.user)
        .select_related("order")
        .prefetch_related("photos")
        .order_by("-created_at")
    )

    status_value = request.GET.get("status")
    if status_value in dict(Ticket.Status.choices):
        qs = qs.filter(status=status_value)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    return Response(
        {
            "page_obj": page_obj,
            "tickets": page_obj.object_list,
            "status_filter": status_value or "",
            "Ticket": Ticket,
            "user_initial": user_initial
        },
        template_name="my_tickets.html",  # full path
    )


@login_required
@require_GET
def api_my_tickets(request):
    """
    JSON list of the current user's tickets.
    Optional ?status=VALUE to filter by Ticket.Status.
    """
    qs = (
        Ticket.objects
        .filter(users=request.user)
        .select_related("order", "reservation")   # reverse O2O is fine here
        .prefetch_related("photos")
        .order_by("-created_at")
    )

    status_value = request.GET.get("status")
    if status_value and status_value in dict(Ticket.Status.choices):
        qs = qs.filter(status=status_value)

    def serialize(t: Ticket):
        # Safely read reverse OneToOne (reservation may not exist)
        try:
            r = t.reservation
        except ReservedSlot.DoesNotExist:
            r = None

        return {
            "id": t.id,
            "reference": t.reference,
            "subject": t.subject,
            "status": t.status,
            "status_display": t.get_status_display(),
            "priority": t.priority,
            "source": t.source,
            "source_display": t.get_source_display(),
            # Keep API key consistent with model field name:
            "daraz_order_number": t.daraz_order_number,
            # Django's JSON encoder will serialize date as "YYYY-MM-DD"
            "daraz_order_date": t.daraz_order_date,
            "order_id": t.order_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            # If you want to avoid an extra COUNT query, use len(t.photos.all())
            "photo_count": t.photos.count(),
            "has_video": bool(t.video),
            "reservation": (
                {
                    "date": r.date.isoformat(),
                    "slot": r.slot,
                    "slot_display": r.get_slot_display(),
                } if r else None
            ),
        }

    data = [serialize(t) for t in qs]
    return JsonResponse({"ok": True, "results": data})


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])  # allow anonymous + logged-in
def api_request_game(request):
    """
    Create a GameRequest from modal: accepts either { game, edition } or { game_name, edition_name }.
    Returns the saved record JSON.
    """
    # Accept both key styles to match your front-end
    game = (request.data.get("game") or request.data.get(
        "game_name") or "").strip()
    edition = (request.data.get("edition")
               or request.data.get("edition_name") or "").strip()

    if not game:
        return Response({"detail": "game name is required."}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user if request.user.is_authenticated else None
    gr = GameRequest.objects.create(
        game_name=game, edition_name=edition, user=user)

    return Response({
        "ok": True,
        "id": gr.id,
        "game_name": gr.game_name,
        "edition_name": gr.edition_name,
        "user": gr.user_id,                # null for anonymous
        "request_date": gr.request_date.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def shop_page(request):
    """
    Renders the Shop HTML which fetches games from /api/products/.
    """
    user_initial = None
    if request.user.is_authenticated:
        name = request.user.get_username() or getattr(request.user, "email", "") or ""
        if name:
            user_initial = name[0].upper()
    return Response({"user": request.user, "user_initial": user_initial}, template_name="shop.html")


# ---------- JSON API ----------
@api_view(["GET"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_products(request):
    """
    JSON list of games. Always 10 items per page.
    Optional filters: ?q= (title icontains), ?genre= (slug or name).
    """
    # fixed page size = 10 as requested
    PER_PAGE = 50

    qs = Product.objects.filter(is_active=True).prefetch_related("images")
    # filters (optional)
    q = (request.query_params.get("q") or "").strip()
    if q:
        qs = qs.filter(title__icontains=q)

    genre = (request.query_params.get("genre") or "").strip()
    if genre:
        qs = qs.filter(models.Q(genres__slug__iexact=genre) |
                       models.Q(genres__name__iexact=genre)).distinct()

    # paginate
    paginator = Paginator(qs, PER_PAGE)
    try:
        page_number = int(request.query_params.get("page") or 1)
    except ValueError:
        page_number = 1
    page_obj = paginator.get_page(page_number)

    def product_image_url(p):
        # pick primary image first, else the first one
        img = p.images.filter(is_primary=True).first() or p.images.first()
        if not img:
            return None
        return request.build_absolute_uri(img.image.url)

    def product_url(p):
        try:
            return request.build_absolute_uri(reverse("game-detail", args=[p.slug]))
        except NoReverseMatch:
            # fallback if you don't have a 'game-detail' route yet
            return request.build_absolute_uri(f"/products/{p.slug}/")

    def price_display(p):
        return f"{p.currency} {p.price:.2f}"

    results = []
    for p in page_obj.object_list:
        results.append({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "currency": p.currency,
            "price": str(p.price),
            "price_display": price_display(p),
            "game_size_gb": str(p.game_size_gb),
            "size_display": f"{p.game_size_gb} GB",
            "edition": p.edition,
            "cover_url": product_image_url(p),
            "url": product_url(p),
        })

    return Response({
        "ok": True,
        "count": paginator.count,
        "total_pages": paginator.num_pages,  # <-- used by the HTML pager
        "page": page_obj.number,
        "per_page": PER_PAGE,
        "results": results,
    })


def _abs(request, url: str) -> str:
    try:
        return request.build_absolute_uri(url)
    except Exception:
        return url


def serialize_product(p, request) -> dict:
    imgs_qs = (p.images.all()
               .order_by('-is_primary', 'id') if hasattr(p.images.model, 'is_primary')
               else p.images.all().order_by('id'))
    images = [{
        "url": _abs(request, img.image.url),
        "alt": getattr(img, "alt_text", None) or p.title,
        "is_primary": bool(getattr(img, "is_primary", False)),
    } for img in imgs_qs]

    data = {
        "id": p.id,
        "sku": getattr(p, "sku", None),
        "slug": p.slug,
        "title": p.title,
        "edition": getattr(p, "edition", None),
        "description": getattr(p, "description", ""),
        "genres": [g.name for g in p.genres.all()] if hasattr(p, "genres") else [],
        "developer": getattr(getattr(p, "developer", None), "name", None),
        "publisher": getattr(getattr(p, "publisher", None), "name", None),
        "price": float(getattr(p, "price", 0)),
        "currency": getattr(p, "currency", "LKR"),
        "game_size_gb": float(p.game_size_gb) if getattr(p, "game_size_gb", None) is not None else None,
        "is_active": bool(getattr(p, "is_active", True)),
        "images": images,
        "cover_url": images[0]["url"] if images else None,
        "url": f"/products/{p.slug}/",
    }
    data["dlcs"] = [serialize_dlc(d, request) for d in p.dlcs.all()]

    sysreq = getattr(p, "system_requirements", None)
    if sysreq:
        data["system_requirements"] = {
            "minimum": {
                "cpu": getattr(sysreq, "min_cpu", None),
                "ram_gb": getattr(sysreq, "min_ram_gb", None),
                "gpu": getattr(sysreq, "min_gpu", None),
                "storage_gb": float(getattr(sysreq, "min_storage_gb", 0)) if getattr(sysreq, "min_storage_gb", None) is not None else None,
                "os": getattr(sysreq, "min_os", None),
            },
            "recommended": {
                "cpu": getattr(sysreq, "rec_cpu", None),
                "ram_gb": getattr(sysreq, "rec_ram_gb", None),
                "gpu": getattr(sysreq, "rec_gpu", None),
                "storage_gb": float(getattr(sysreq, "rec_storage_gb", 0)) if getattr(sysreq, "rec_storage_gb", None) is not None else None,
                "os": getattr(sysreq, "rec_os", None),
            },
        }
    return data


def serialize_dlc(d, request):
    try:
        img_url = request.build_absolute_uri(d.image.url) if d.image else None
    except Exception:
        img_url = None
    return {
        "title": d.title,
        "description": d.description or "",
        "image_url": img_url,
    }


@require_GET
def api_product_detail_by_slug(request, slug: str):
    qs = (Product.objects
          .filter(is_active=True)
          .select_related("developer", "publisher", "system_requirements")
          .prefetch_related("genres", "images", "dlcs"))
    p = get_object_or_404(qs, slug=slug)
    return JsonResponse(serialize_product(p, request))


def product_page(request, slug: str):
    return render(request, "product_details.html", {"slug": slug})


def serialize_storage(d, request):
    try:
        img = request.build_absolute_uri(d.image.url) if d.image else None
    except Exception:
        img = None
    return {
        "id": d.id,
        "name": d.name,
        "category": d.category,
        # <-- this is what the HTML now uses
        "category_label": d.get_category_display(),
        "price": float(getattr(d, "price", 0)),       # <-- added
        "currency": getattr(d, "currency", "LKR"),    # <-- added
        "true_capacity_gb": float(d.true_capacity_gb),
        "marketing_capacity_gb": float(d.marketing_capacity_gb),
        "image_url": img,
    }


@require_GET
def api_storage_devices(request):
    qs = StorageDevice.objects.all()
    return JsonResponse({"results": [serialize_storage(d, request) for d in qs]})


# --- CART HELPERS -----------------------------------------------------------

def _ensure_session(request):
    """Guarantee a session_key for anonymous carts."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _get_or_create_cart(request) -> Cart:
    """Return the cart bound to session; attach user if logged in."""
    sess_key = _ensure_session(request)
    cart, _ = Cart.objects.get_or_create(session_key=sess_key)
    if request.user.is_authenticated and not cart.users.filter(id=request.user.id).exists():
        cart.users.add(request.user)
    return cart


def _abs(request, url: str) -> str:
    """Absolute URL helper (you already use a similar one)."""
    try:
        return request.build_absolute_uri(url)
    except Exception:
        return url


def _product_primary_image_url(p, request):
    imgs = getattr(p, "images", None)
    if not imgs:
        return None
    # Prefer primary if your Image model has 'is_primary'; else first()
    primary = imgs.filter(is_primary=True).first() if hasattr(
        imgs.model, "is_primary") else None
    img = primary or imgs.first()
    return _abs(request, img.image.url) if img else None


def serialize_cart_item(ci: CartItem, request) -> dict:
    p = ci.product
    return {
        "id": ci.id,
        "quantity": ci.quantity,
        "unit_price": str(getattr(ci, "unit_price", p.price)),
        "subtotal": str(ci.subtotal),
        "product": {
            "id": p.id,
            "title": p.title,
            "edition": getattr(p, "edition", None),
            "price": str(p.price),
            "currency": getattr(p, "currency", "LKR"),
            "game_size_gb": str(getattr(p, "game_size_gb", "")) if getattr(p, "game_size_gb", None) is not None else None,
            "primary_image": _product_primary_image_url(p, request),
        },
    }


def serialize_device_for_cart(d: StorageDevice, request) -> dict:
    img = _abs(request, d.image.url) if getattr(d, "image", None) else None
    return {
        "id": d.id,
        "name": d.name,
        "price": str(getattr(d, "price", 0)),
        "currency": getattr(d, "currency", "LKR"),
        "true_capacity_gb": str(d.true_capacity_gb),
        "marketing_capacity_gb": str(d.marketing_capacity_gb),
        "category": d.category,
        "category_display": d.get_category_display(),
        "image_url": img,
    }


def serialize_cart(cart: Cart, request) -> dict:
    left_items = [serialize_cart_item(ci, request)
                  for ci in cart.cartitem_set.all()]
    right_items = [serialize_cart_item(
        si, request) for si in cart.cartstorageitem_set.all()]  # same shape

    device = serialize_device_for_cart(
        cart.storage_device, request) if cart.storage_device else None

    return {
        # left/right
        "left_items": left_items,
        "device": device,
        "right_items": right_items,

        # totals (as strings to preserve decimal precision)
        "direct_total": str(cart.direct_total),                 # LEFT subtotal
        "storage_device_price": str(cart.storage_device_price),  # device price
        # RIGHT games subtotal
        "storage_games_total": str(cart.storage_games_total),
        # device + right games
        "storage_total": str(cart.storage_total),
        "grand_total": str(cart.grand_total),                   # everything

        # capacity (right side only)
        "device_capacity_gb": str(cart.device_capacity_gb),
        "device_used_gb": str(cart.device_used_gb),
        "device_remaining_gb": str(cart.device_remaining_gb),
        "device_percent_used": str(cart.device_percent_used),
    }

# --- HTML PAGE (TemplateHTMLRenderer), like your shop/tickets pages ----------


@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def cart_page(request):
    """
    Renders the Cart HTML page; the page fetches /api/cart/ for data.
    """
    user_initial = None
    if request.user.is_authenticated:
        name = request.user.get_username() or getattr(request.user, "email", "") or ""
        if name:
            user_initial = name[0].upper()
    return Response({"user": request.user, "user_initial": user_initial}, template_name="cart.html")

# --- JSON API (function-based; JSONRenderer; AllowAny like api_products) -----


@api_view(["GET"])
@renderer_classes([JSONRenderer])
# allow guests (session cart) and logged-in users
@permission_classes([AllowAny])
def api_cart(request):
    """
    Returns the current user's/session's cart in JSON.
    """
    base = _get_or_create_cart(request)
    # Reload with relations to avoid N+1
    cart = (
        Cart.objects
        .select_related("storage_device")
        .prefetch_related(
            Prefetch("cartitem_set", queryset=CartItem.objects.select_related(
                "product").prefetch_related("product__images")),
            Prefetch("cartstorageitem_set", queryset=CartStorageItem.objects.select_related(
                "product").prefetch_related("product__images")),
        )
        .get(pk=base.pk)
    )
    return Response(serialize_cart(cart, request))


@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def storage_pick_page(request):
    """Renders the HTML that lets the user choose a storage device."""
    user_initial = None
    if request.user.is_authenticated:
        name = request.user.get_username() or getattr(request.user, "email", "") or ""
        if name:
            user_initial = name[0].upper()
    return Response({"user": request.user, "user_initial": user_initial}, template_name="pick_storage.html")


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])  # allow guest carts
def api_cart_select_storage(request):
    """
    Set/replace the cart's storage_device.
    Body: { "device_id": <int> }
    """
    did = request.data.get("device_id")
    if not did:
        return Response({"detail": "device_id is required."}, status=400)

    cart = _get_or_create_cart(request)  # you already have this helper
    device = get_object_or_404(StorageDevice, id=did)
    cart.storage_device = device
    cart.save(update_fields=["storage_device"])
    return Response({"ok": True, "device_id": device.id, "device_name": device.name})


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_cart_add_direct(request):
    """
    Body: { product_id: int, quantity?: int }
    Creates/updates CartItem; unit_price = Product.price at time of add.
    """
    cart = _get_or_create_cart(request)
    pid = request.data.get("product_id")
    qty = int(request.data.get("quantity") or 1)
    if not pid:
        return Response({"detail": "product_id is required."}, status=400)
    if qty < 1:
        return Response({"detail": "quantity must be >= 1."}, status=400)

    p = get_object_or_404(Product.objects.filter(is_active=True), id=pid)

    with transaction.atomic():
        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart, product=p,
            defaults={"quantity": qty, "unit_price": p.price}
        )
        if not created:
            item.quantity += qty
            # keep original unit_price as captured-at-add, or re-price if you prefer:
            # item.unit_price = p.price
            item.save(update_fields=["quantity"])

    return Response({"ok": True, "left_count": cart.cartitem_set.count()})

# Add a product to the RIGHT side (on the selected storage device)


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_cart_add_to_device(request):
    """
    Body: { product_id: int, quantity?: int }
    Requires a selected storage_device and enough free capacity.
    """
    cart = _get_or_create_cart(request)
    if not cart.storage_device:
        return Response({"detail": "Select a storage device first."}, status=400)

    pid = request.data.get("product_id")
    qty = int(request.data.get("quantity") or 1)
    if not pid:
        return Response({"detail": "product_id is required."}, status=400)
    if qty < 1:
        return Response({"detail": "quantity must be >= 1."}, status=400)

    p = get_object_or_404(Product.objects.filter(is_active=True), id=pid)
    game_size = Decimal(p.game_size_gb or 0) * qty
    if cart.device_used_gb + game_size > cart.device_capacity_gb:
        return Response({"detail": "Not enough space on the selected device."}, status=400)

    with transaction.atomic():
        si, created = CartStorageItem.objects.select_for_update().get_or_create(
            cart=cart, product=p,
            defaults={"quantity": qty, "unit_price": p.price}
        )
        if not created:
            si.quantity += qty
            si.save(update_fields=["quantity"])

    return Response({"ok": True, "right_count": cart.cartstorageitem_set.count()})


# --- CART: removals ------------------------------------------------------------


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_cart_remove_from_device(request):
    """
    Remove a single game from the RIGHT side (on-device list).
    Body: { "storage_item_id": <int> } OR { "product_id": <int> }
    """
    cart = _get_or_create_cart(request)

    storage_item_id = request.data.get("storage_item_id")
    product_id = request.data.get("product_id")

    if not storage_item_id and not product_id:
        return Response({"detail": "storage_item_id or product_id is required."}, status=400)

    if storage_item_id:
        qs = CartStorageItem.objects.filter(id=storage_item_id, cart=cart)
        if not qs.exists():
            return Response({"detail": "Item not found on device."}, status=404)
        qs.delete()
    else:
        # unique per (cart, product) by model Meta, so at most one
        csi = get_object_or_404(
            CartStorageItem, cart=cart, product_id=product_id)
        csi.delete()

    # Optionally return updated cart payload for instant UI refresh:
    return Response({"ok": True})
    # Or: return Response({"ok": True, "cart": serialize_cart(cart, request)})


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_remove_product_from_cart(request):
    """
    Remove a LEFT-side direct-buy line item.
    Body: { "item_id": <int> } OR { "product_id": <int> }
    """
    cart = _get_or_create_cart(request)
    item_id = request.data.get("item_id")
    product_id = request.data.get("product_id")

    if not item_id and not product_id:
        return Response({"detail": "item_id or product_id is required."}, status=400)

    if item_id:
        ci = get_object_or_404(CartItem, id=item_id, cart=cart)
        ci.delete()
    else:
        ci = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        ci.delete()

    return Response({"ok": True})


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_remove_storage_device_from_cart(request):
    """
    Remove the selected storage device and clear all RIGHT-side games.
    Body: {}  (no body needed)
    """
    cart = _get_or_create_cart(request)

    if not cart.storage_device_id:
        return Response({"ok": True, "detail": "No device on cart."})

    # Clear all on-device games first (capacity becomes fully available)
    CartStorageItem.objects.filter(cart=cart).delete()

    # Detach the device
    cart.storage_device = None
    cart.save(update_fields=["storage_device"])

    return Response({"ok": True})
