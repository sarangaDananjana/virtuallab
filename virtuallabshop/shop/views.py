import hmac
import hashlib
import json
import re
import uuid
from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal, InvalidOperation
import requests
from virtuallabshop.settings import GENIE_API_KEY, GENIE_API_URL, GENIE_WEBHOOK_URL
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse, NoReverseMatch
from urllib.parse import quote
from django.db import models
from django.db.models import Prefetch, Q

from .models import (
    Order, OfflineGames, Ticket, ActivationTicket, TicketPhoto, ReservedSlot,
    GameRequest, Product, StorageDevice, Cart, CartItem, CartStorageItem, User,
    OrderItem, OrderStorageItem, Blog, BlogPhoto, Genre,
    Quiz, Question, Choice, QuizAttempt, UserAnswer  # <-- ADD THESE
)

# Also, make sure 'timezone' is imported near the top (it's used in the new views)
from django.utils import timezone

from django.contrib.auth import authenticate, login as dj_login, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_GET
from rest_framework.decorators import api_view, renderer_classes, parser_classes
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction, IntegrityError

User = get_user_model()

# ---- HTML pages (TemplateHTMLRenderer) ----


def _redirect_to_login(request):
    login_url = reverse("login-page")
    return redirect(f"{login_url}?next={quote(request.get_full_path())}")


# ---------- Profile HTML page ----------
@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def profile_page(request):
    """Render the Profile HTML page (requires login)."""
    if not request.user.is_authenticated:
        return _redirect_to_login(request)

    name = request.user.get_username() or getattr(request.user, "email", "") or ""
    user_initial = name[0].upper() if name else None
    return Response({"user": request.user, "user_initial": user_initial}, template_name="profile.html")


# ---------- Profile JSON APIs ----------
def _serialize_me(u: User) -> dict:
    return {
        # matches your profile.html JS keys
        "name": (f"{u.first_name} {u.last_name}".strip() or u.username),
        "email": u.email or "",
        "phone": getattr(u, "phone_number", "") or "",
        "address_no": getattr(u, "address_no", "") or "",
        "address_line1": getattr(u, "address_line1", "") or "",
        "address_line2": getattr(u, "address_line2", "") or "",
        "city": getattr(u, "city", "") or "",
        "postal_code": getattr(u, "postal_code", "") or "",
        "member_since": u.date_joined,  # ISO string in DRF response
        "is_cod_approved": u.is_cod_approved or False,
        "steam_username": getattr(u, "steam_username", "") or "",
        "steam_email": getattr(u, "steam_email", "") or "",
    }


@api_view(["GET"])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def api_me(request):
    """Return the current user's profile info."""
    return Response(_serialize_me(request.user))


@api_view(["PATCH", "POST"])
@parser_classes([JSONParser, FormParser, MultiPartParser])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def api_me_update(request):
    """
    Update current user's profile.
    Allowed fields: name, email, phone, address_no, address_line1, address_line2, city, postal_code.
    Explicitly ignores username/password changes.
    """
    u = request.user
    data = request.data or {}

    # Extract inputs (strip whitespace)
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    address_no = (data.get("address_no") or "").strip()
    address_line1 = (data.get("address_line1") or "").strip()
    address_line2 = (data.get("address_line2") or "").strip()
    city = (data.get("city") or "").strip()
    postal_code = (data.get("postal_code") or "").strip()
    steam_username = (data.get("steam_username") or "").strip()
    steam_email = (data.get("steam_email") or "").strip()

    # Validate uniqueness when changing email/phone
    if email and email.lower() != (u.email or "").lower():
        if User.objects.filter(email__iexact=email).exclude(pk=u.pk).exists():
            return Response({"detail": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST)

    if phone and phone != (u.phone_number or ""):
        if User.objects.filter(phone_number__iexact=phone).exclude(pk=u.pk).exists():
            return Response({"detail": "Phone number already in use."}, status=status.HTTP_400_BAD_REQUEST)

    # Apply changes (username/password are intentionally ignored here)
    with transaction.atomic():
        changed = []

        # name → split into first/last (simple heuristic)
        if name:
            parts = name.split()
            first = " ".join(parts[:-1]) if len(parts) > 1 else name
            last = parts[-1] if len(parts) > 1 else ""
            if first != u.first_name:
                u.first_name = first
                changed.append("first_name")
            if last != u.last_name:
                u.last_name = last
                changed.append("last_name")

        if email and email != u.email:
            u.email = email
            changed.append("email")
        if phone and phone != (u.phone_number or ""):
            u.phone_number = phone
            changed.append("phone_number")

        # addresses
        if address_no != (u.address_no or ""):
            u.address_no = address_no
            changed.append("address_no")
        if address_line1 != (u.address_line1 or ""):
            u.address_line1 = address_line1
            changed.append("address_line1")
        if address_line2 != (u.address_line2 or ""):
            u.address_line2 = address_line2
            changed.append("address_line2")
        if city != (u.city or ""):
            u.city = city
            changed.append("city")
        if postal_code != (u.postal_code or ""):
            u.postal_code = postal_code
            changed.append("postal_code")

        if steam_username != (u.steam_username or ""):
            u.steam_username = steam_username
            changed.append("steam_username")
        if steam_email != (u.steam_email or ""):
            u.steam_email = steam_email
            changed.append("steam_email")

        if changed:
            u.save(update_fields=list(set(changed)))  # dedupe for safety

    return Response(_serialize_me(u), status=status.HTTP_200_OK)


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
    PER_PAGE = 20

    # 1. ADDED .order_by() TO PRIORITIZE NON-CRACKED GAMES
    qs = Product.objects.filter(is_active=True, is_addon_only=False).prefetch_related(
        "images").order_by('is_cracked')

    q = (request.query_params.get("q") or "").strip()
    if q:
        qs = qs.filter(title__icontains=q)

    genre = (request.query_params.get("genre") or "").strip()
    if genre:
        qs = qs.filter(models.Q(genres__slug__iexact=genre) |
                       models.Q(genres__name__iexact=genre)).distinct()

    paginator = Paginator(qs, PER_PAGE)
    try:
        page_number = int(request.query_params.get("page") or 1)
    except ValueError:
        page_number = 1
    page_obj = paginator.get_page(page_number)

    def product_image_url(p):
        img = p.images.filter(is_primary=True).first() or p.images.first()
        if not img:
            return None
        return request.build_absolute_uri(img.image.url)

    def product_url(p):
        try:
            return request.build_absolute_uri(reverse("product_page", args=[p.slug]))
        except NoReverseMatch:
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
            "is_cracked": p.is_cracked,  # 2. ADDED THIS FIELD
        })

    return Response({
        "ok": True,
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "page": page_obj.number,
        "per_page": PER_PAGE,
        "results": results,
    })


@api_view(["GET"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_genres(request):
    """
    Returns a simple JSON list of all unique genre names.
    """
    genres = Genre.objects.order_by('name').values_list(
        'name', flat=True).distinct()
    return Response(list(genres))


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

    game_box_product = p.addons.filter(is_active=True).first()
    game_box_data = None
    if game_box_product:
        game_box_data = {
            "id": game_box_product.id,
            "title": game_box_product.title,
            "price": float(game_box_product.price),
            "currency": game_box_product.currency,
            "cover_url": _product_primary_image_url(game_box_product, request)
        }

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
        "is_cracked": bool(getattr(p, "is_cracked", True)),
        "images": images,
        "cover_url": images[0]["url"] if images else None,
        "url": f"/products/{p.slug}/",
        "game_box": game_box_data,
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


@api_view(["GET"])  # Steam_support
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def steam_support_page(request):
    """this renders the Home HTML page"""
    user_initial = None
    if request.user.is_authenticated:
        name = request.user.get_username() or getattr(request.user, "email", "") or ""
        if name:
            user_initial = name[0].upper()
    return Response({"user": request.user, "user_initial": user_initial}, template_name="steam_support.html")


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


@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def orders_page(request):
    """
    Render the Orders HTML page (requires login).
    """
    if not request.user.is_authenticated:
        return _redirect_to_login(request)

    name = request.user.get_username() or getattr(request.user, "email", "") or ""
    user_initial = name[0].upper() if name else None
    return Response({"user": request.user, "user_initial": user_initial}, template_name="orders.html")


@api_view(["GET"])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def api_orders_me(request):
    """
    Return current user's orders in the shape required by orders.html:
    - direct_items: from OrderItem
    - storage_bundle: { device_name, items } from OrderStorageItem (+ device name if available)
    Supports: ?page=1&per_page=5&status=processing|shipped|delivered|cancelled
              &q=<order id or product title>&from=YYYY-MM-DD&to=YYYY-MM-DD
    """

    # --- base queryset: only this user's orders ---
    qs = (
        Order.objects
        .filter(users=request.user)
        .prefetch_related(
            Prefetch(
                "orderitem_set",
                queryset=OrderItem.objects.select_related("product")
                .prefetch_related("product__images"),
            ),
            Prefetch(
                # OrderStorageItem FK -> Order(related_name="storage_items")
                "storage_items",
                queryset=OrderStorageItem.objects.select_related("product")
                .prefetch_related("product__images"),
            ),
        )
        .order_by("-ordered_at")
    )

    # --- filters ---
    q = (request.query_params.get("q") or "").strip()
    if q:
        cond = (
            Q(payment_reference__icontains=q)
            | Q(orderitem__product__title__icontains=q)
            | Q(storage_items__product__title__icontains=q)
        )
        if q.isdigit():
            cond |= Q(id=int(q))
        qs = qs.filter(cond).distinct()

    from_str = (request.query_params.get("from") or "").strip()
    to_str = (request.query_params.get("to") or "").strip()
    if from_str:
        qs = qs.filter(ordered_at__date__gte=parse_date(from_str))
    if to_str:
        qs = qs.filter(ordered_at__date__lte=parse_date(to_str))

    # UI → model status mapping
    ui_to_model = {
        "processing": [Order.OrderStatus.PAYMENT_INITIATED, Order.OrderStatus.PAYMENT_SUCCESS],
        "shipped":    [Order.OrderStatus.ORDER_SENT],
        "delivered":  [Order.OrderStatus.ORDER_DELIVERED],
        "cancelled":  [Order.OrderStatus.CANCELLED],
    }
    ui_status = (request.query_params.get("status") or "").strip().lower()
    if ui_status in ui_to_model:
        qs = qs.filter(status__in=ui_to_model[ui_status])

    # --- pagination ---
    try:
        per_page = max(1, int(request.query_params.get("per_page") or 5))
    except ValueError:
        per_page = 5
    try:
        page_number = max(1, int(request.query_params.get("page") or 1))
    except ValueError:
        page_number = 1

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page_number)

    # helpers
    def map_status(o: Order) -> str:
        if o.status == Order.OrderStatus.ORDER_DELIVERED:
            return "delivered"
        if o.status == Order.OrderStatus.ORDER_SENT:
            return "shipped"
        if o.status == Order.OrderStatus.CANCELLED:
            return "cancelled"
        return "processing"

    def payment_label(o: Order) -> str:
        return {"CARD": "Card", "BANK_TRANSFER": "Bank transfer"}.get(o.payment_method, o.payment_method)

    # Try to provide a device name for the storage bundle when possible.
    # If you later add Order.storage_device (FK) or Order.storage_device_name (CharField),
    # this will automatically pick it up.
    def infer_device_name(o: Order) -> str:
        # Preferred future fields if you add them:
        name = getattr(o, "storage_device_name", None)
        if name:
            return name
        sd = getattr(o, "storage_device", None)
        if getattr(sd, "name", None):
            return sd.name
        # Fallback label if unknown but we do have storage items:
        if getattr(o, "storage_items", None) and o.storage_items.exists():
            return "Selected storage device"
        return ""

    u = request.user

    def serialize(o: Order) -> dict:
        # --- direct items (left side)
        direct_items = []
        for it in o.orderitem_set.all():
            p = it.product
            direct_items.append({
                "title": p.title,
                "quantity": it.quantity,
                "cover_url": _product_primary_image_url(p, request),
            })

        # --- storage bundle (right side)
        storage_items_payload = []
        for si in o.storage_items.all():
            p = si.product
            storage_items_payload.append({
                "title": p.title,
                "quantity": si.quantity,
                "cover_url": _product_primary_image_url(p, request),
            })
        storage_bundle = None
        if storage_items_payload:
            storage_bundle = {
                "device_name": infer_device_name(o) or "",
                "items": storage_items_payload,
            }

        # Friendly reference: prefer payment_reference; else synthesize "VL-00001"
        reference = o.payment_reference or (f"VL-{o.id:05d}" if o.id else None)

        delivered_at = (
            o.updated_at.isoformat()
            if (o.status == Order.OrderStatus.ORDER_DELIVERED and o.updated_at)
            else None
        )

        return {
            "id": o.id,
            "reference": reference,
            "status": map_status(o),
            # string keeps cents exact; frontend casts as Number
            "total": str(o.total),
            "currency": o.currency,
            "placed_at": o.ordered_at.isoformat(),
            "delivered_at": delivered_at,

            "direct_items": direct_items,
            "storage_bundle": storage_bundle,  # null if no storage items

            "recipient_name": (f"{u.first_name} {u.last_name}".strip() or u.username or u.email),
            "address_line1": getattr(u, "address_line1", "") or "",
            "address_line2": getattr(u, "address_line2", "") or "",
            "city": getattr(u, "city", "") or "",
            "postal_code": getattr(u, "postal_code", "") or "",

            "payment_method": payment_label(o),
            "delivery_method": "Standard",
        }

    results = [serialize(o) for o in page_obj.object_list]
    return Response({
        "results": results,
        "total_pages": paginator.num_pages,
        "page": page_obj.number,
        "per_page": per_page,
    })


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def api_genie_start(request):
    """
    Create a Genie transaction for the current user and return the checkout URL.

    Request JSON:
      {
        "amount": 1000,              # required; numeric (LKR, no cents)
        "currency": "LKR",           # optional, defaults to LKR
        "webhook": "https://..."     # optional; falls back to settings.GENIE_WEBHOOK_URL
      }

    Response JSON:
      { "url": "https://..." }
    """
    u = request.user
    data = request.data or {}

    # --- validate amount ---
    amount = data.get("amount", None)
    try:
        if amount is None:
            raise ValueError("Amount is required.")
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Amount must be > 0.")
        # Genie (LKR) typically expects whole value; send as int
        amount_to_send = int(amount)
    except (InvalidOperation, ValueError) as e:
        return Response({"detail": f"Invalid amount: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    currency = (data.get("currency") or "LKR").upper()
    webhook = GENIE_WEBHOOK_URL
    redirect_url = "https://virtuallabgames.com/payment-done/"

    # --- build payload from logged-in user's profile ---
    full_name = (f"{u.first_name} {u.last_name}".strip()
                 or u.get_username() or getattr(u, "email", ""))
    payload = {
        "amount": amount_to_send,
        "currency": currency,
        "customer": {
            "name": full_name,
            "email": getattr(u, "email", "") or "",
            "billingEmail": getattr(u, "email", "") or "",
            "billingAddress1": getattr(u, "address_line1", "") or "",
            "billingAddress2": getattr(u, "address_line2", "") or "",
            "billingCity": getattr(u, "city", "") or "",
            "billingCountry": "LK",
            "billingPostCode": getattr(u, "postal_code", "") or "",
        },
    }
    if webhook:
        payload["webhook"] = webhook

    if redirect_url:
        payload["redirectUrl"] = redirect_url

    # --- call Genie ---
    api_key = GENIE_API_KEY
    if not api_key:
        return Response({"detail": "Missing GENIE_API_KEY in settings."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    url = GENIE_API_URL

    headers = {
        # if your account uses Bearer, change to: f"Bearer {api_key}"
        "Authorization": f"{api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
    except requests.RequestException as e:
        return Response({"detail": f"Upstream request failed: {e}"},
                        status=status.HTTP_502_BAD_GATEWAY)

    # bubble up provider errors clearly
    if r.status_code >= 400:
        try:
            provider = r.json()
        except Exception:
            provider = r.text
        return Response({
            "detail": "Genie error",
            "provider_status": r.status_code,
            "provider_response": provider
        }, status=status.HTTP_502_BAD_GATEWAY)

    try:
        body = r.json()
    except ValueError:
        return Response({"detail": "Genie returned non-JSON response."},
                        status=status.HTTP_502_BAD_GATEWAY)

    checkout_url = body.get("url")
    if not checkout_url:
        return Response({"detail": "No 'url' in Genie response.", "provider_response": body},
                        status=status.HTTP_502_BAD_GATEWAY)

    customer_id = body.get("customerId") or body.get("customer_id")

    # Save on the logged-in user
    if customer_id:
        customer_id = str(customer_id)
        if getattr(request.user, "customer_id", "") != customer_id:
            request.user.customer_id = customer_id
            request.user.save(update_fields=["customer_id"])

        else:
            return Response({"detail": "No 'CustomerID' in Genie response.", "provider_response": body},
                            status=status.HTTP_502_BAD_GATEWAY)

    return Response({"url": checkout_url})


@csrf_exempt
def genie_webhook(request):
    # 1) Only accept POST
    if request.method != "POST":
        return HttpResponse(status=405)  # Method Not Allowed

    # 2) Read raw body
    raw_body = request.body
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    # 3) Signature headers
    nonce = request.META.get("HTTP_X_SIGNATURE_NONCE", "")
    timestamp = request.META.get("HTTP_X_SIGNATURE_TIMESTAMP", "")
    signature = request.META.get("HTTP_X_SIGNATURE", "")

    # 4) Recompute signature and compare
    sign_string = f"{nonce}{timestamp}{GENIE_API_KEY}".encode()
    computed_sig = hashlib.sha256(sign_string).hexdigest()
    if not hmac.compare_digest(computed_sig, signature):
        return HttpResponseForbidden("Invalid signature")

    # 5) PRINT the incoming webhook payload
    print("🔔 Received Genie webhook payload:")

    # ====== Begin additional logic ======

    event_type = payload.get("eventType")

    # Handle NOTIFY_TRANSACTION_CHANGE with state CONFIRMED
    if event_type == "NOTIFY_TRANSACTION_CHANGE":
        state = payload.get("state")
        if state == "CONFIRMED":
            transaction_id = payload.get("transactionId")
            customer_id = payload.get("customerId")
            amount = payload.get("amountFractional")

            if transaction_id and customer_id:
                post_url = "https://www.virtuallabgames.com/api/orders/finalize/"
                post_data = {
                    "transaction_id": str(transaction_id),
                    "customer_id": str(customer_id),
                    "amount": int(amount)
                }
                try:
                    response = requests.post(
                        post_url, json=post_data, timeout=10)
                    print(f"✅ Booking POST status: {response.status_code}")
                    print(f"Response: {response.text}")
                    print(payload)
                    print(str(transaction_id), customer_id)
                except requests.RequestException as e:
                    print(f"❌ Failed to post booking: {e}")
                    print(str(transaction_id), customer_id)
                    print(payload)

    # ====== End additional logic ======

    # 6) Respond with the exact webhook body
    return JsonResponse(payload, status=200)


@api_view(["POST"])
@renderer_classes([JSONRenderer])
# if this is a payment webhook caller, keep AllowAny; otherwise tighten it
@permission_classes([AllowAny])
def api_finalize_order_from_customer(request):
    """
    Body: { "customer_id": "<string>", "transaction_id": "<string>" }
    1) Find the user by `customer_id`
    2) Take the user's most recent non-empty cart
    3) Create an Order:
       - status = PAYMENT_SUCCESS
       - payment_method = CARD
       - payment_reference = transaction_id
       - order_value = cart.grand_total  (covers both sides)
    4) Copy LEFT items to OrderItem and RIGHT (on-device) items to OrderStorageItem
    5) Clear the user's cart (remove items + clear storage_device)
    6) Return the created (or existing) order basics
    """
    data = request.data or {}
    customer_id = str(data.get("customer_id") or "").strip()
    transaction_id = str(data.get("transaction_id")
                         or data.get("payment_reference") or "").strip()
    amount = int(data.get("amount"))

    if not customer_id or not transaction_id:
        return Response(
            {"detail": "Both 'customer_id' and 'transaction_id' are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1) Find user by customer_id (User model exposes `customer_id`)
    user = get_object_or_404(User, customer_id=customer_id)

    # Idempotency: if we already created an order for this payment_reference & user, return it.
    existing = (
        Order.objects.filter(payment_reference=transaction_id, users=user)
        .order_by("-ordered_at")
        .first()
    )
    if existing:
        return Response(
            {"ok": True, "order_id": existing.id,
                "reference": existing.payment_reference, "total": str(existing.total)},
            status=status.HTTP_200_OK,
        )

    # 2) Locate the user's most-recent non-empty cart
    carts = (
        Cart.objects.filter(users=user)
        .select_related("storage_device")
        .prefetch_related(
            Prefetch("cartitem_set",
                     queryset=CartItem.objects.select_related("product")),
            Prefetch("cartstorageitem_set",
                     queryset=CartStorageItem.objects.select_related("product")),
        )
        .order_by("-updated_at", "-created_at")
    )

    cart = None
    for c in carts:
        if c.cartitem_set.exists() or c.cartstorageitem_set.exists() or c.storage_device_id:
            cart = c
            break

    if not cart:
        return Response(
            {"detail": "No non-empty cart found for this customer."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 3–5) Create order from cart & clear cart atomically
    with transaction.atomic():
        # Lock the cart row to prevent concurrent mutations while we copy & clear
        cart_locked = Cart.objects.select_for_update().get(pk=cart.pk)

        device = cart_locked.storage_device
        device_name = getattr(device, "name", "") or ""
        device_price = getattr(
            device, "price", Decimal("0.00")) or Decimal("0.00")

        order = Order.objects.create(
            status=Order.OrderStatus.PAYMENT_SUCCESS,
            payment_method=Order.PaymentMethod.CARD,
            payment_reference=transaction_id,
            order_value=amount,
            currency="LKR",
            storage_device_name=device_name,
            storage_device_price=device_price,
        )
        order.users.add(user)

        # LEFT: direct purchases -> OrderItem
        for ci in cart_locked.cartitem_set.select_related("product"):
            OrderItem.objects.create(
                order=order,
                product=ci.product,
                quantity=ci.quantity,
                unit_price=ci.unit_price,
            )

        # RIGHT: on-device games -> OrderStorageItem
        for si in cart_locked.cartstorageitem_set.select_related("product"):
            OrderStorageItem.objects.create(
                order=order,
                product=si.product,
                quantity=si.quantity,
                unit_price=si.unit_price,
            )

        # Clear cart (items + right side + device)
        CartItem.objects.filter(cart=cart_locked).delete()
        CartStorageItem.objects.filter(cart=cart_locked).delete()
        if cart_locked.storage_device_id:
            cart_locked.storage_device = None
            cart_locked.save(update_fields=["storage_device"])

    return Response(
        {
            "ok": True,
            "order_id": order.id,
            "reference": order.payment_reference,
            "status": order.status,
            "payment_method": order.payment_method,
            "total": str(order.total),
            "currency": order.currency,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])  # Authenticated users only
def api_finalize_cod_order_for_user(request):
    """
    Finalizes a Cash On Delivery (COD) order for the currently authenticated user.
    Body: { "amount": <integer> }
    1) Use the authenticated user from the request session.
    2) Take the user's most recent non-empty cart.
    3) Create an Order:
       - status = PAYMENT_SUCCESS
       - payment_method = COD
       - payment_reference = generated unique COD reference
       - order_value = amount from request
    4) Copy LEFT items to OrderItem and RIGHT (on-device) items to OrderStorageItem.
    5) Clear the user's cart (remove items + clear storage_device).
    6) Return the created order basics.
    """
    data = request.data or {}
    # The user is taken directly from the request, not an ID in the body
    user = request.user

    try:
        amount = int(data.get("amount"))
    except (ValueError, TypeError):
        return Response(
            {"detail": "A valid 'amount' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 2) Locate the user's most-recent non-empty cart
    carts = (
        Cart.objects.filter(users=user)
        .select_related("storage_device")
        .prefetch_related(
            Prefetch("cartitem_set",
                     queryset=CartItem.objects.select_related("product")),
            Prefetch("cartstorageitem_set",
                     queryset=CartStorageItem.objects.select_related("product")),
        )
        .order_by("-updated_at", "-created_at")
    )

    cart = None
    for c in carts:
        if c.cartitem_set.exists() or c.cartstorageitem_set.exists() or c.storage_device_id:
            cart = c
            break

    if not cart:
        return Response(
            {"detail": "No non-empty cart found for this user."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 3–5) Create order from cart & clear cart atomically
    with transaction.atomic():
        # Lock the cart row to prevent concurrent mutations while we copy & clear
        cart_locked = Cart.objects.select_for_update().get(pk=cart.pk)

        device = cart_locked.storage_device
        device_name = getattr(device, "name", "") or ""
        device_price = getattr(
            device, "price", Decimal("0.00")) or Decimal("0.00")

        # For COD, we generate a unique reference instead of taking it as input
        cod_reference = f"cod_{uuid.uuid4().hex}"

        order = Order.objects.create(
            status=Order.OrderStatus.PAYMENT_SUCCESS,
            # Assuming a 'COD' choice exists in your Order model's PaymentMethod
            payment_method=Order.PaymentMethod.COD,
            payment_reference=cod_reference,
            order_value=amount,
            currency="LKR",
            storage_device_name=device_name,
            storage_device_price=device_price,
        )
        order.users.add(user)

        # LEFT: direct purchases -> OrderItem
        for ci in cart_locked.cartitem_set.select_related("product"):
            OrderItem.objects.create(
                order=order,
                product=ci.product,
                quantity=ci.quantity,
                unit_price=ci.unit_price,
            )

        # RIGHT: on-device games -> OrderStorageItem
        for si in cart_locked.cartstorageitem_set.select_related("product"):
            OrderStorageItem.objects.create(
                order=order,
                product=si.product,
                quantity=si.quantity,
                unit_price=si.unit_price,
            )

        # Clear cart (items + right side + device)
        CartItem.objects.filter(cart=cart_locked).delete()
        CartStorageItem.objects.filter(cart=cart_locked).delete()
        if cart_locked.storage_device_id:
            cart_locked.storage_device = None
            cart_locked.save(update_fields=["storage_device"])

    return Response(
        {
            "ok": True,
            "order_id": order.id,
            "reference": order.payment_reference,
            "status": order.status,
            "payment_method": order.payment_method,
            "total": str(order.total),
            "currency": order.currency,
        },
        status=status.HTTP_201_CREATED,
    )


# --- Activation Page -----------------------------------------------------------

@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def activation_page(request):
    """
    Renders the game Activation HTML page.
    This page is only for authenticated users.
    """
    if not request.user.is_authenticated:
        return _redirect_to_login(request)

    user = request.user
    name = user.get_username() or getattr(user, "email", "") or ""
    user_initial = name[0].upper() if name else None

    # Get all of this user's relevant activation tickets in one query
    # Get all of this user's NON-EXPIRED activation tickets, ordered by oldest first for each game
    user_tickets = ActivationTicket.objects.filter(
        user=user,
        offline_game__product__is_active=True
    ).exclude(
        status=ActivationTicket.TicketStatus.EXPIRED
    ).select_related('offline_game').order_by('offline_game_id', 'created_at')

    # Create a lookup map that only keeps the FIRST (oldest) ticket for each game
    user_ticket_map = {}
    for t in user_tickets:
        if t.offline_game_id not in user_ticket_map:
            user_ticket_map[t.offline_game_id] = t

    # Get all active offline games
    all_games = OfflineGames.objects.filter(
        product__is_active=True
    ).select_related(
        'product'
    ).prefetch_related(
        'product__images'
    ).order_by('product__title')

    games_with_status = []
    for game in all_games:
        ticket = user_ticket_map.get(game.id)
        status_info = {
            "user_status": "not_owned",
            "ticket": None,
        }

        if ticket and ticket.remaining_attempts > 0:
            status_info["ticket"] = ticket
            if ticket.status == ActivationTicket.TicketStatus.ACTIVATED:
                status_info["user_status"] = "owned"
            elif ticket.status == ActivationTicket.TicketStatus.COD_PAYMENT_PENDING:
                status_info["user_status"] = "cod_pending"
            elif ticket.status == ActivationTicket.TicketStatus.PAYMENT_PENDING:
                status_info["user_status"] = "payment_pending"

        # Find the primary image for the product
        primary_image = None
        if game.product.images.exists():
            primary_image_obj = game.product.images.filter(
                is_primary=True).first() or game.product.images.first()
            if primary_image_obj:
                primary_image = request.build_absolute_uri(
                    primary_image_obj.image.url)

        games_with_status.append({
            "game": game,
            "product": game.product,
            "primary_image": primary_image,
            **status_info
        })

    return Response({
        "user": user,
        "user_initial": user_initial,
        "games_with_status": games_with_status,
    }, template_name="activation.html")


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def api_verify_activation_code(request):
    """
    Verifies an activation code for the logged-in user.

    Expects JSON body: { "code": "XXXX-XXXX-XXXX-XXXX" }

    - Finds a ticket matching the code with a status of 'PAYMENT_PENDING' or 'COD_PAYMENT_PENDING'.
    - If not found, returns 404.
    - If found but belongs to another user, returns 401.
    - On success, updates the ticket status to 'ACTIVATED' and returns 200.
    """
    user = request.user
    code = request.data.get("code")

    if not code:
        return Response(
            {"detail": "Activation code is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Find the ticket by code, but only if its status is one of the valid pending types.
        ticket = ActivationTicket.objects.get(
            activation_code__iexact=code,
            status__in=[
                ActivationTicket.TicketStatus.PAYMENT_PENDING,
                ActivationTicket.TicketStatus.COD_PAYMENT_PENDING
            ]
        )
    except ActivationTicket.DoesNotExist:
        # If no ticket matches the code AND the status filter, it's considered not found.
        return Response(
            {"detail": "Activation code not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if the found ticket belongs to the user making the request.
    if ticket.user != user:
        return Response(
            {"detail": "Unauthorized. This activation code does not belong to you."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # If all checks pass, activate the ticket.
    with transaction.atomic():
        ticket.status = ActivationTicket.TicketStatus.ACTIVATED
        ticket.activation_date = timezone.now()
        ticket.save(update_fields=['status', 'activation_date'])

    return Response(
        {"detail": "Code activated successfully."},
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])  # Important for file uploads
def activation_upload_slip_api(request):
    """
    Creates an ActivationTicket by uploading a payment slip.

    Expects multipart/form-data with:
    - 'game_id': The ID of the OfflineGames instance being purchased.
    - 'slip_image': The image file of the payment slip.
    """
    user = request.user
    game_id = request.data.get("game_id")
    slip_image = request.FILES.get("slip_image")

    if not game_id:
        return Response(
            {"detail": "Game ID is required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    if not slip_image:
        return Response(
            {"detail": "Payment slip image is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get the OfflineGames instance the user wants to buy
    offline_game = get_object_or_404(OfflineGames, id=game_id)

    # Create the new ActivationTicket
    try:
        with transaction.atomic():
            ticket = ActivationTicket.objects.create(
                user=user,
                offline_game=offline_game,
                payment_slip=slip_image,
                status=ActivationTicket.TicketStatus.PAYMENT_PENDING
            )
    except Exception as e:
        # Handle potential database errors
        return Response(
            {"detail": f"An error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        {
            "detail": "Slip submitted successfully. Please wait for verification.",
            "ticket": {
                "id": ticket.id,
                "status": ticket.status
            }
        },
        status=status.HTTP_201_CREATED
    )


def _excerpt(text: str, n: int = 220) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]  # don’t mid-word cut
    return cut + "…"


def serialize_blog_card(b: Blog, request) -> dict:
    """Smaller payload for grids/cards (blog.html uses date + 'min read' + title + short text)."""
    try:
        cover = _abs(request, b.main_image.url) if b.main_image else None
    except Exception:
        cover = None
    return {
        "id": b.id,
        "slug": b.slug,
        "title": b.title,
        "created_at": b.created_at.isoformat(),
        "category": b.category,
        "category_label": b.get_category_display(),
        "reading_time_minutes": b.reading_time_minutes,  # e.g. "3 min read"
        "cover_url": cover,
        "content_en_excerpt": _excerpt(b.content_en),
        "content_si_excerpt": _excerpt(b.content_si),
        "url": f"/blog/{b.slug}/",
    }


def serialize_blog_full(b: Blog, request) -> dict:
    """Richer payload for the featured/hero block (includes sub images)."""
    data = serialize_blog_card(b, request)
    # include full content + sub images for the featured section
    data.update({
        "is_featured": b.is_featured,
        "content_en": b.content_en or "",
        "content_si": b.content_si or "",
        "photos": [{
            "id": p.id,
            "url": _abs(request, p.image.url) if p.image else None,
            "alt_text": p.alt_text or "",
            "order": p.order,
        } for p in b.photos.all().order_by("order", "id")],
    })
    return data


@api_view(["GET"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_blog_home(request):
    """
    Returns:
    {
      "featured": { ... } | null,
      "latest": [ { ... up to 3 items ... } ]
    }
    """
    qs = (
        Blog.objects
        .prefetch_related(
            Prefetch("photos", queryset=BlogPhoto.objects.order_by("order", "id"))
        )
        .order_by("-created_at")
    )

    featured = qs.filter(is_featured=True).first()
    latest_qs = qs.exclude(pk=featured.pk) if featured else qs
    latest = list(latest_qs[:3])

    payload = {
        "featured": serialize_blog_full(featured, request) if featured else None,
        "latest": [serialize_blog_card(b, request) for b in latest],
    }
    return Response(payload)


@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
@ensure_csrf_cookie
def blog_page(request):
    """Renders the HTML that lets the user choose a storage device."""
    user_initial = None
    if request.user.is_authenticated:
        name = request.user.get_username() or getattr(request.user, "email", "") or ""
        if name:
            user_initial = name[0].upper()
    return Response({"user": request.user, "user_initial": user_initial}, template_name="blog.html")


def _split_paragraphs(text: str) -> list[str]:
    """
    Split long content into logical paragraphs.
    - Primary split on blank lines (two or more newlines)
    - Fallback: single newlines if no blank lines present
    """
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in text.split("\n") if p.strip()]
    return parts


def _serialize_blog_detail(b: Blog, request) -> dict:
    """
    Shape for a single blog detail, including an interleaved 'blocks' structure
    for Sinhala and English. Photo order determines where images appear.
    """
    # Base card info (reuse your card shape)
    base = serialize_blog_card(b, request)

    # Main fields
    base.update({
        "is_featured": b.is_featured,
        "cover_url": base.get("cover_url"),
    })

    # Photos sorted by (order, id)
    photos = list(b.photos.all().order_by("order", "id"))
    photos_by_order = {}
    for p in photos:
        photos_by_order.setdefault(p.order, []).append(p)

    def build_blocks(body_text: str) -> list[dict]:
        paras = _split_paragraphs(body_text)
        blocks = []
        # Determine how far to iterate:
        # at least as many steps as we have paragraphs or the highest image order
        max_order = max([p.order for p in photos], default=0)
        steps = max(len(paras), max_order)
        for i in range(1, steps + 1):
            # paragraph i
            if i <= len(paras):
                blocks.append({
                    "type": "paragraph",
                    "index": i,                # paragraph number
                    "text": paras[i - 1],
                })
            # image with order i (could be multiple if duplicates)
            for ph in photos_by_order.get(i, []):
                try:
                    url = request.build_absolute_uri(
                        ph.image.url) if ph.image else None
                except Exception:
                    url = None
                blocks.append({
                    "type": "image",
                    "index": ph.order,        # image number from 'order'
                    "url": url,
                    "alt_text": ph.alt_text or "",
                    "id": ph.id,
                })
        # Any remaining images with order > steps (unlikely) appended at end:
        for ph in photos:
            if ph.order > steps:
                try:
                    url = request.build_absolute_uri(
                        ph.image.url) if ph.image else None
                except Exception:
                    url = None
                blocks.append({
                    "type": "image",
                    "index": ph.order,
                    "url": url,
                    "alt_text": ph.alt_text or "",
                    "id": ph.id,
                })
        return blocks

    # Full bilingual blocks
    data = {
        **base,
        "content": {
            "en": {
                "full": b.content_en or "",
                "blocks": build_blocks(b.content_en or ""),
            },
            "si": {
                "full": b.content_si or "",
                "blocks": build_blocks(b.content_si or ""),
            },
        },
        "photos": [{
            "id": ph.id,
            "url": request.build_absolute_uri(ph.image.url) if ph.image else None,
            "alt_text": ph.alt_text or "",
            "order": ph.order,
        } for ph in photos],
    }
    return data


@api_view(["GET"])
@renderer_classes([JSONRenderer])
@permission_classes([AllowAny])
def api_blog_detail(request, slug: str):
    """
    Return one blog post with interleaved blocks:
    {
      "id": ..., "slug": ..., "title": ...,
      "created_at": "...",
      "category": "news",
      "category_label": "Gaming News",
      "reading_time_minutes": 5,
      "cover_url": "...",
      "is_featured": false,
      "content": {
        "en": {
          "full": "<full English>",
          "blocks": [
            {"type":"paragraph","index":1,"text":"..."},
            {"type":"image","index":1,"url":"...","alt_text":"..."},
            {"type":"paragraph","index":2,"text":"..."},
            {"type":"image","index":2,"url":"...","alt_text":"..."}
          ]
        },
        "si": { ... same structure for Sinhala ... }
      },
      "photos": [{ "id":..., "order":1, "url":"...", "alt_text":"" }, ...]
    }
    """
    qs = (
        Blog.objects
        .prefetch_related(
            Prefetch("photos", queryset=BlogPhoto.objects.order_by("order", "id"))
        )
    )
    b = get_object_or_404(qs, slug=slug)
    return Response(_serialize_blog_detail(b, request))


def blog_detail_page(request, slug: str):
    return render(request, "view_blog.html", {"slug": slug})


@api_view(["GET"])  # Register page (renders form)
@renderer_classes([TemplateHTMLRenderer])
def payment_done_page(request):
    """this renders the register HTML page"""
    return Response({}, template_name="payment_done.html")


def calculator_view(request):
    """
    This view renders the calculator HTML page.

    The render function takes the request object and the path to the template
    and returns an HttpResponse with the rendered template.
    """
    # Django automatically looks inside the 'templates' folder.
    # The path 'calculator_app/calculator.html' corresponds to the folder structure we created.
    return render(request, 'calculator.html')
# --------------------------------------------------------------------------
# --- 🧩 Quiz System (NEWLY ADDED) ------------------------------------------
# --------------------------------------------------------------------------


# We remove the DRF decorators and use standard Django ones
@login_required
@ensure_csrf_cookie
def quiz_dashboard_page(request):
    """
    Renders the Quiz Dashboard HTML page.
    Requires login.
    """
    # @login_required handles the auth check, so no need for:
    # if not request.user.is_authenticated: ...

    user_initial = None
    name = request.user.get_username() or getattr(request.user, "email", "") or ""
    if name:
        user_initial = name[0].upper()

    # Get all available quizzes
    available_quizzes = Quiz.objects.all().order_by('quiz_number')

    # Get this user's past attempts
    user_attempts = QuizAttempt.objects.filter(
        user=request.user
    ).select_related('quiz').order_by('-start_time')

    # This is the context dictionary
    context = {
        "user": request.user,
        "user_initial": user_initial,
        "available_quizzes": available_quizzes,
        "user_attempts": user_attempts,
    }

    # Use the standard Django 'render' function, not 'Response'
    return render(request, "quiz_dashboard.html", context)


@login_required
@ensure_csrf_cookie
def quiz_attempt_page(request, quiz_id):
    """
    Renders the HTML shell for taking a quiz.
    The actual quiz data is loaded via API.
    Requires login.
    """
    quiz = get_object_or_404(Quiz, id=quiz_id)

    user_initial = None
    name = request.user.get_username() or getattr(request.user, "email", "") or ""
    if name:
        user_initial = name[0].upper()

    context = {
        "user": request.user,
        "user_initial": user_initial,
        "quiz": quiz,  # Pass quiz object for ID, title, etc.
    }

    # Use the standard Django 'render' function
    return render(request, "quiz_attempt.html", context)


@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def api_start_quiz_attempt(request):
    """
    Starts a new quiz attempt for the user.
    Creates the QuizAttempt and returns the questions.
    Expects: { "quiz_id": <int> }
    """
    quiz_id = request.data.get("quiz_id")
    if not quiz_id:
        return Response({"detail": "quiz_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    quiz = get_object_or_404(Quiz, id=quiz_id)
    user = request.user

    # Create the new attempt. The model's save() method handles attempt_number.
    try:
        attempt = QuizAttempt.objects.create(
            user=user,
            quiz=quiz
        )
    except Exception as e:
        return Response({"detail": f"Could not create attempt: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Serialize questions and choices
    questions_data = []
    questions = Question.objects.filter(
        quiz=quiz
    ).prefetch_related('choices').order_by('order')

    for q in questions:
        choices_data = []
        for c in q.choices.all():
            choices_data.append({
                "id": c.id,
                "choice_text": c.choice_text,
            })

        questions_data.append({
            "id": q.id,
            "question_text": q.question_text,
            "order": q.order,
            "choices": choices_data,
        })

    return Response({
        "attempt_id": attempt.id,
        "quiz_title": quiz.title,
        "time_limit_minutes": quiz.time_limit_minutes,
        "questions": questions_data,
    }, status=status.HTTP_201_CREATED)


# In your views.py file:

@api_view(["POST"])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
@transaction.atomic  # Keep the transaction for safety
def api_submit_quiz_attempt(request):
    """
    Submits answers for a quiz attempt.
    Expects: { "attempt_id": <int>, "answers": { <question_id_str>: <choice_id_str>, ... } }
    """
    attempt_id = request.data.get("attempt_id")
    answers = request.data.get("answers", {})

    if not attempt_id:
        return Response({"detail": "attempt_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Ensure the user owns this attempt
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)

    # Prevent re-submission
    if attempt.end_time:
        return Response({"detail": "This quiz has already been submitted."}, status=status.HTTP_400_BAD_REQUEST)

    # Set the end time
    attempt.end_time = timezone.now()
    attempt.save(update_fields=['end_time'])

    # --- THIS IS THE FIX ---
    # We must create each answer one by one using .create()
    # so that the custom .save() method on the UserAnswer model is called.
    # Using bulk_create() bypasses the .save() method.

    for q_id, c_id in answers.items():
        try:
            question_id = int(q_id)
            choice_id = int(c_id)

            # .create() will call .save() automatically
            UserAnswer.objects.create(
                quiz_attempt=attempt,
                question_id=question_id,
                selected_choice_id=choice_id
            )
        except (ValueError, TypeError):
            # Log this error but continue processing other answers
            print(
                f"Invalid answer format for attempt {attempt_id}: Q={q_id}, C={c_id}")
    # --- END OF FIX ---

    # Force a refresh from the DB to get the calculated score
    attempt.refresh_from_db()

    return Response({
        "ok": True,
        "attempt_id": attempt.id,
        "score": attempt.score,
        "total_questions": attempt.total_questions,
        "percentage": round(attempt.percentage_score, 2),
    }, status=status.HTTP_200_OK)
