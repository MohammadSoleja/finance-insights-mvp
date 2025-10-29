# app_web/views.py
import base64, io

# pandas is not used in this module; removed unused import
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render
from .forms import UploadFileForm
from app_core.ingest import validate_and_preview, _read_any, _coerce_types, dataframe_to_transactions
from django.db import transaction as dbtxn
from decimal import Decimal

from django.utils import timezone
from django.db.models import Q
from app_core.models import Transaction
from app_core.metrics import queryset_to_df, kpis as kpi_calc, timeseries, by_category

import math
import json
import datetime
from django.utils.safestring import mark_safe

from app_core.insights import generate_insights

from django.http import HttpResponse, JsonResponse

from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect
from django.contrib.auth import login
from django.core.paginator import Paginator

@login_required
def upload_view(request):
    context = {"title": "Upload Transactions"}

    if request.method == "POST" and request.POST.get("action") == "save":
        # Second step: decode the file content and persist to DB
        b64 = request.POST.get("file_b64", "")
        filename = request.POST.get("filename", "upload.csv")
        if not b64:
            context["errors"] = ["No file data to save. Please upload again."]
            context["form"] = UploadFileForm()
            return render(request, "app_web/upload.html", context, status=400)

        raw = base64.b64decode(b64.encode("utf-8"))
        fobj = io.BytesIO(raw)

        # Re-validate and coerce using the same pipeline
        result = validate_and_preview(fobj, filename)
        if not result["ok"]:
            context["errors"] = result["errors"]
            context["form"] = UploadFileForm()
            return render(request, "app_web/upload.html", context, status=400)

        # Build the DataFrame again from raw and save
        fobj.seek(0)
        df = _read_any(fobj, filename)
        df, _ = _coerce_types(df)

        # dataframe_to_transactions signature is (df, user)
        rows = dataframe_to_transactions(df, request.user)  # pass the User instance
        with dbtxn.atomic():
            Transaction.objects.bulk_create(rows, batch_size=1000)

        context.update({
            "saved": True,
            "saved_count": len(rows),
            "form": UploadFileForm(),
        })
        return render(request, "app_web/upload.html", context, status=200)

    if request.method == "POST" and request.POST.get("action") == "add_tx":
        # Manual add single transaction
        add_errors = []
        date_str = request.POST.get("date", "").strip()
        description = request.POST.get("description", "").strip()
        amount_raw = request.POST.get("amount", "").strip()
        direction = request.POST.get("direction")
        category = request.POST.get("category", "").strip()
        subcategory = request.POST.get("subcategory", "").strip()
        account = request.POST.get("account", "").strip()
        source = request.POST.get("source", "manual").strip()

        # if no account provided, default to the logged-in user's username
        if not account:
            try:
                account = request.user.username or ""  # fallback to empty string
            except Exception:
                account = ""

        # validate date
        tx_date = None
        if not date_str:
            add_errors.append("Date is required for a transaction.")
        else:
            try:
                # accept ISO format YYYY-MM-DD
                tx_date = datetime.date.fromisoformat(date_str)
            except Exception:
                try:
                    tx_date = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
                except Exception:
                    add_errors.append("Invalid date format — use YYYY-MM-DD.")

        # validate description
        if not description:
            add_errors.append("Description is required.")

        # validate amount
        tx_amount = None
        if not amount_raw:
            add_errors.append("Amount is required.")
        else:
            try:
                amt_s = str(amount_raw).replace(",", "").replace("£", "").strip()
                tx_amount = Decimal(amt_s)
            except Exception:
                add_errors.append("Invalid amount value.")

        # infer/validate direction
        if not direction:
            if tx_amount is not None:
                direction = Transaction.INFLOW if tx_amount >= 0 else Transaction.OUTFLOW
            else:
                direction = Transaction.INFLOW
        else:
            if direction not in {Transaction.INFLOW, Transaction.OUTFLOW}:
                add_errors.append("Invalid direction selected.")

        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        # If errors, return JSON for AJAX or render template with errors
        if add_errors:
            if is_ajax:
                return JsonResponse({"ok": False, "errors": add_errors}, status=400)
            context["add_errors"] = add_errors
            context["form"] = UploadFileForm()
            return render(request, "app_web/upload.html", context, status=400)

        # create transaction
        try:
            tx = Transaction.objects.create(
                user=request.user,
                date=tx_date,
                description=description[:512],
                amount=abs(tx_amount),
                direction=direction,
                category=category,
                subcategory=subcategory,
                account=account,
                source=source or "manual",
            )
            tx_data = {
                "id": tx.id,
                "date": str(tx.date),
                "description": tx.description,
                "amount": str(tx.amount),
                "direction": tx.direction,
                "category": tx.category,
            }
            if is_ajax:
                return JsonResponse({"ok": True, "tx": tx_data})

            context["add_success"] = True
            context["added_tx"] = tx
            context["form"] = UploadFileForm()
        except Exception as e:
            if is_ajax:
                return JsonResponse({"ok": False, "errors": [f"Failed to save transaction: {e}"]}, status=500)
            context["add_errors"] = ["Failed to save transaction: %s" % e]
            context["form"] = UploadFileForm()
        return render(request, "app_web/upload.html", context)

    if request.method == "POST":
        # First step: validate + preview
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            result = validate_and_preview(f, f.name)

            context["form"] = UploadFileForm()  # reset form
            context["result"] = result
            if result["ok"]:
                # Read raw bytes again for base64 embedding (MVP-friendly)
                f.seek(0)
                raw = f.read()
                context.update({
                    "success": True,
                    "uploaded_name": f.name,
                    "uploaded_size": f.size,
                    "row_count": result["row_count"],
                    "preview_html": mark_safe(result["preview_html"]),
                    "file_b64": base64.b64encode(raw).decode("utf-8"),
                    "filename": f.name,
                })
            else:
                context["errors"] = result["errors"]
            context["warnings"] = result.get("warnings", [])
            return render(request, "app_web/upload.html", context, status=200 if result["ok"] else 400)

        # Invalid file type/size
        context["form"] = form
        return render(request, "app_web/upload.html", context, status=400)

    # GET
    context["form"] = UploadFileForm()
    return render(request, "app_web/upload.html", context)

@login_required
def dashboard_view(request):
    """
    Simple dashboard for user_id=1 (MVP). Supports optional ?freq=D|W|M
    """
    user= request.user
    freq = request.GET.get("freq", "D").upper()
    if freq not in {"D", "W", "M"}:
        freq = "D"

    # Optional quick date filters (?days=30)
    days = request.GET.get("days")
    q = Q(user=user)
    if days and str(days).isdigit():
        since = timezone.now().date() - datetime.timedelta(days=int(days))
        q &= Q(date__gte=since)

    qs = Transaction.objects.filter(q).order_by("date")
    df = queryset_to_df(qs)

    # KPIs
    kpi = kpi_calc(df)

    # ---- Time series (NaN-safe) ----
    ts = timeseries(df, freq=freq)

    ts_labels = [str(d) for d in ts.get("date", []).tolist()] if not ts.empty else []
    def _clean_nums(seq):
        out = []
        for x in seq:
            try:
                v = float(x)
                if math.isnan(v):
                    v = 0.0
            except Exception:
                v = 0.0
            out.append(round(v, 2))
        return out

    ts_in  = _clean_nums(ts.get("inflow", []).tolist()  if not ts.empty else [])
    ts_out = _clean_nums(ts.get("outflow", []).tolist() if not ts.empty else [])
    ts_net = _clean_nums(ts.get("net", []).tolist()     if not ts.empty else [])

    # ---- Categories (NaN-safe) ----
    bc = by_category(df).head(10)   # <-- this was missing
    cat_labels = [str(x) for x in (bc["category"].tolist() if not bc.empty else [])]
    cat_vals   = _clean_nums(bc["amount"].tolist() if not bc.empty else [])

    insights = generate_insights(df,ts,bc)
    payload = {
        "ts_labels": ts_labels,
        "ts_in": ts_in,
        "ts_out": ts_out,
        "ts_net": ts_net,
        "cat_labels": cat_labels,
        "cat_vals": cat_vals,
    }

    # Ensure no NaN reaches the browser (JSON doesn’t allow it)
    chart_payload = json.dumps(payload, allow_nan=False)

    context = {
        "title": "Dashboard",
        "kpi": kpi,
        "freq": freq,
        "tx_count": kpi["tx_count"],
        "chart_payload": mark_safe(chart_payload),
        "insights": insights,
    }
    return render(request, "app_web/dashboard.html", context)


def health_view(request):
    return HttpResponse("ok", content_type="text/plain")

def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()                     # creates the new user
            login(request, user)
            return redirect("app_web:dashboard")        # built-in auth route
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})

def home_view(request):
    """Public landing page."""
    return render(request, "app_web/home.html")

@login_required
def profile_view(request):
    return render(request, "app_web/profile.html", {"title": "Profile"})

@login_required
def settings_view(request):
    if request.method == "POST":
        first = request.POST.get("first_name", "").strip()
        email = request.POST.get("email", "").strip()
        user = request.user
        if first:
            user.first_name = first
        if email:
            user.email = email
        user.save()
        messages.success(request, "Profile updated")
        return redirect("app_web:settings")
    return render(request, "app_web/settings.html", {"title": "Settings"})

@login_required
def transactions_view(request):
    """List transactions with search (description/category), sort, and pagination.
    Query params:
      q=text search
      sort= date or amount (prefix - for desc)
      page=page number
      direction= inflow|outflow (optional)
    """
    qs = Transaction.objects.filter(user=request.user).order_by('-date')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(description__icontains=q) | Q(category__icontains=q))

    # direction filter
    direction = request.GET.get('direction', '').strip()
    if direction in {Transaction.INFLOW, Transaction.OUTFLOW}:
        qs = qs.filter(direction=direction)

    sort = request.GET.get('sort', '')
    if sort:
        # allow 'date' or 'amount' with optional '-' prefix
        if sort.lstrip('-') in {'date', 'amount'}:
            qs = qs.order_by(sort)

    # pagination
    paginator = Paginator(qs, 20)
    page_num = request.GET.get('page', '1')
    try:
        page = paginator.get_page(page_num)
    except Exception:
        page = paginator.get_page(1)

    # preserve params for pagination links
    params = request.GET.copy()
    if 'page' in params:
        params.pop('page')

    context = {
        'title': 'Transactions',
        'page': page,
        'q': q,
        'sort': sort,
        'direction': direction,
        'params': params.urlencode(),
    }
    return render(request, 'app_web/transactions.html', context)
