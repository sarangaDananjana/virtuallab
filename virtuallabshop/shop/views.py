from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import quote
from .models import Order, ReservedSlot, Ticket, TicketPhoto, ReservedSlot, GameRequest
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
