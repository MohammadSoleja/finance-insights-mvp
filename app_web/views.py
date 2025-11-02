# app_web/views.py
import base64, io

# pandas is not used in this module; removed unused import
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from .forms import UploadFileForm, TransactionForm
from app_core.ingest import validate_and_preview, _read_any, _coerce_types, dataframe_to_transactions
from django.db import transaction as dbtxn
from decimal import Decimal

from django.utils import timezone
from django.db.models import Q
from app_core.models import Transaction
from app_core.metrics import queryset_to_df, kpis as kpi_calc, timeseries, by_category
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from .models import UserTableSetting

import math
import json
import datetime
import logging
from django.utils.safestring import mark_safe

from app_core.insights import generate_insights

from django.http import HttpResponse, JsonResponse

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.paginator import Paginator

# Allowed columns and default order
ALLOWED_COLUMNS = [
    'date', 'description', 'category', 'subcategory', 'amount', 'direction', 'account', 'source', 'created_at', 'updated_at'
]
DEFAULT_COLUMNS = ['date', 'description', 'category', 'amount', 'direction']

# module logger for server-side debugging
logger = logging.getLogger(__name__)

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
            logger.exception('Failed to save transaction in upload_view')
            if is_ajax:
                return JsonResponse({'ok': False, 'errors': [f'Failed to save transaction: {e}']}, status=500)
            messages.error(request, 'Failed to save transaction: %s' % e)
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
    if freq not in {"D", "W", "M", "Y"}:
        freq = "D"

    # Optional quick date filters (?days=30) + new start/end and category filters
    days = request.GET.get("days")
    q = Q(user=user)
    if days and str(days).isdigit():
        since = timezone.now().date() - datetime.timedelta(days=int(days))
        q &= Q(date__gte=since)

    # New: explicit start/end date range and category filter from query params
    # Accept either 'start'/'end' (dashboard form) or fallback to 'start_date'/'end_date' (if present)
    start_raw = (request.GET.get('start', '') or request.GET.get('start_date', '')) or ''
    end_raw = (request.GET.get('end', '') or request.GET.get('end_date', '')) or ''
    start = start_raw.strip()
    end = end_raw.strip()

    # Also read category filter
    category = request.GET.get('category', '').strip()

    # If no explicit start/end provided, choose sensible defaults per frequency for CHARTS
    sd = None
    ed = None
    today = timezone.now().date()
    # ensure KPI window label always defined
    kpi_window_label = ''
    def monday_of(d):
        return d - datetime.timedelta(days=d.weekday())
    def sunday_of(d):
        return monday_of(d) + datetime.timedelta(days=6)

    if not start and not end:
        # Chart defaults per user's request:
        # D -> current week (Mon-Sun)
        # W -> last 4 weeks (calendar weeks Mon-Sun anchored to current week)
        # M -> last 12 months (month-aligned, include current month up to today)
        # Y -> Year-to-date (Jan 1 -> today)
        if freq == 'D':
            week_start = monday_of(today)
            week_end = sunday_of(today)
            start = week_start.isoformat()
            end = week_end.isoformat()
        elif freq == 'W':
            # last 4 weeks including current week
            curr_monday = monday_of(today)
            start_dt = curr_monday - datetime.timedelta(weeks=3)
            end_dt = sunday_of(today)
            start = start_dt.isoformat()
            end = end_dt.isoformat()
        elif freq == 'M':
            # last 12 months: start = first day of month 11 months ago; end = today
            month = today.month
            year = today.year
            # compute year/month for 11 months ago
            m_back = month - 11
            y_back = year
            if m_back <= 0:
                m_back += 12
                y_back -= 1
            start_dt = datetime.date(y_back, m_back, 1)
            start = start_dt.isoformat()
            end = today.isoformat()
        elif freq == 'Y':
            # Year-to-date
            start_dt = datetime.date(today.year, 1, 1)
            start = start_dt.isoformat()
            end = today.isoformat()

    # Apply start/end (support both YYYY-MM-DD strings)
    if start:
        try:
            sd = datetime.date.fromisoformat(start)
            q &= Q(date__gte=sd)
        except Exception:
            sd = None
    if end:
        try:
            ed = datetime.date.fromisoformat(end)
            q &= Q(date__lte=ed)
        except Exception:
            ed = None

    # Apply category
    if category:
        q &= Q(category=category)

    qs = Transaction.objects.filter(q).order_by("date")

    # collect distinct categories for dropdown (exclude empty)
    categories_qs = Transaction.objects.filter(user=user).exclude(category__isnull=True).exclude(category__exact='').values_list('category', flat=True).distinct().order_by('category')
    categories = list(categories_qs)

    # DataFrame used for charts (respects the chart start/end defaults or explicit range)
    df = queryset_to_df(qs)

    # Compute KPI range: if the user supplied explicit start/end, KPIs use that range as well.
    # Otherwise compute KPI ranges depending on freq:
    #  - D: today only
    #  - W: week-to-date (Mon -> today)
    #  - M: month-to-date
    #  - Y: last 365 days
    explicit_range = bool(start_raw or end_raw)
    kpi_q = Q(user=user)
    if explicit_range:
        # reuse sd/ed parsed above
        if sd:
            kpi_q &= Q(date__gte=sd)
        if ed:
            kpi_q &= Q(date__lte=ed)
        # label for explicit range
        try:
            if sd and ed:
                kpi_window_label = f"{sd.strftime('%b %d, %Y')} – {ed.strftime('%b %d, %Y')}"
            elif sd:
                kpi_window_label = f"From {sd.strftime('%b %d, %Y')}"
            elif ed:
                kpi_window_label = f"Until {ed.strftime('%b %d, %Y')}"
            else:
                kpi_window_label = 'Custom range'
        except Exception:
            kpi_window_label = 'Custom range'
    else:
        # choose kpi window based on freq
        if freq == 'D':
            # KPI for current week (Mon-Sun)
            ksd = monday_of(today)
            ked = sunday_of(today)
            kpi_window_label = 'Current week'
        elif freq == 'W':
            # KPI for last 4 weeks (including current week)
            curr_monday = monday_of(today)
            ksd = curr_monday - datetime.timedelta(weeks=3)
            ked = sunday_of(today)
            kpi_window_label = 'Last 4 weeks'
        elif freq == 'M':
            # KPI for last 12 months (month-aligned)
            month = today.month
            year = today.year
            m_back = month - 11
            y_back = year
            if m_back <= 0:
                m_back += 12
                y_back -= 1
            ksd = datetime.date(y_back, m_back, 1)
            ked = today
            kpi_window_label = 'Last 12 months'
        elif freq == 'Y':
            # Year-to-date
            ksd = datetime.date(today.year, 1, 1)
            ked = today
            kpi_window_label = 'Year to date'
        else:
            ksd = None
            ked = None
        if ksd:
            kpi_q &= Q(date__gte=ksd)
        if ked:
            kpi_q &= Q(date__lte=ked)

    qs_kpi = Transaction.objects.filter(kpi_q).order_by('date')
    df_kpi = queryset_to_df(qs_kpi)
    kpi = kpi_calc(df_kpi)

    # ---- Time series (NaN-safe) ----
    # pass parsed start/end (sd, ed) so timeseries covers the full requested range
    ts = timeseries(df, freq=freq, start=sd, end=ed)

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
    # Compute signed sums per category so frontend can color inflow vs outflow
    if df.empty:
        cat_labels = []
        cat_vals = []
        cat_signs = []
        bc = by_category(df).head(10)
    else:
        # group by category and sum signed amounts (signed_amount already has sign)
        signed = df.groupby(df["category"].fillna("Uncategorised"))["signed_amount"].sum()
        # Order by absolute value descending and take top 10
        signed_abs = signed.abs().sort_values(ascending=False).head(10)
        # labels in display order
        cat_labels = [str(x) for x in signed_abs.index.tolist()]
        # absolute amounts for display
        cat_vals = _clean_nums(signed_abs.tolist())
        # derive sign per displayed label from the original signed series (preserve sign)
        cat_signs = []
        for lab in signed_abs.index.tolist():
             v = signed.get(lab, 0.0)
             try:
                 fv = float(v)
             except Exception:
                 fv = 0.0
             if fv > 0:
                 cat_signs.append(1)
             elif fv < 0:
                 cat_signs.append(-1)
             else:
                 cat_signs.append(0)
        # build bc DataFrame expected by insights (category, amount)
        try:
            bc = signed_abs.reset_index(name='amount')
            # ensure column name for category
            bc.rename(columns={bc.columns[0]: 'category'}, inplace=True)
        except Exception:
            bc = by_category(df).head(10)

    insights = generate_insights(df,ts,bc)
    payload = {
        "ts_labels": ts_labels,
        "ts_in": ts_in,
        "ts_out": ts_out,
        "ts_net": ts_net,
        "cat_labels": cat_labels,
        "cat_vals": cat_vals,
        "cat_signs": cat_signs,
    }

    # Ensure no NaN reaches the browser (JSON doesn’t allow it)
    chart_payload = json.dumps(payload, allow_nan=False)

    # flag when no transactions match filters
    no_results = (df.empty if hasattr(df, 'empty') else (len(df) == 0))

    # build base querystring (preserve all GET except freq and page) for frequency links
    params_copy = request.GET.copy()
    if 'freq' in params_copy:
        params_copy.pop('freq')
    if 'page' in params_copy:
        params_copy.pop('page')
    base_qs = params_copy.urlencode()

    context = {
        "title": "Dashboard",
        "kpi": kpi,
        "freq": freq,
        "tx_count": kpi.get("tx_count", 0),
        "chart_payload": mark_safe(chart_payload),
        "insights": insights,
        # filters
        'start': start,
        'end': end,
        'start_parsed': sd,
        'end_parsed': ed,
        'category': category,
        'categories': categories,
        'no_results': no_results,
        'base_qs': base_qs,
        'kpi_window_label': kpi_window_label,  # <-- add to context
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

def pricing_view(request):
    """Public pricing placeholder page."""
    context = {"title": "Pricing"}
    return render(request, "app_web/pricing.html", context)

def demo_view(request):
    """Public demo request placeholder page."""
    context = {"title": "Demo"}
    return render(request, "app_web/demo.html", context)

def about_view(request):
    """Public about page placeholder."""
    context = {"title": "About"}
    return render(request, "app_web/about.html", context)

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
      start_date, end_date = optional YYYY-MM-DD bounds
    """
    # Handle Add Transaction POST (modal submits via AJAX to this same URL)
    if request.method == 'POST' and request.POST.get('action') == 'add_tx':
        try:
            # Log incoming form keys for debugging (do not log raw CSRF token)
            pdata = {k: (v if k != 'csrfmiddlewaretoken' else '***') for k, v in request.POST.items()}
            logger.debug('Received add_tx POST: %s', pdata)
        except Exception:
            logger.debug('Received add_tx POST but failed to serialize POST data')
        add_errors = []
        date_str = request.POST.get("date", "").strip()
        description = request.POST.get("description", "").strip()
        amount_raw = request.POST.get("amount", "").strip()
        direction = request.POST.get("direction")
        category = request.POST.get("category", "").strip()
        subcategory = request.POST.get("subcategory", "").strip()
        account = request.POST.get("account", "").strip() if request.POST.get("account") is not None else ""
        source = request.POST.get("source", "manual").strip()

        # default account to username if not provided
        if not account:
            try:
                account = request.user.username or ""
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
        if add_errors:
            if is_ajax:
                return JsonResponse({"ok": False, "errors": add_errors}, status=400)
            # non-AJAX: re-render transactions page showing errors (fall through to render with context)
            messages.error(request, "Please fix the errors below")
        else:
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
                if is_ajax:
                    return JsonResponse({"ok": True, "tx": {"id": tx.id, "date": str(tx.date), "description": tx.description, "amount": str(tx.amount), "direction": tx.direction, "category": tx.category}})
                messages.success(request, "Transaction added")
            except Exception as e:
                logger.exception('Failed to save transaction in transactions_view')
                if is_ajax:
                    return JsonResponse({'ok': False, 'errors': [f'Failed to save transaction: {e}']}, status=500)
                messages.error(request, 'Failed to save transaction: %s' % e)

    qs = Transaction.objects.filter(user=request.user).order_by('-date')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(description__icontains=q) | Q(category__icontains=q))

    # direction filter
    direction = request.GET.get('direction', '').strip()
    if direction in {Transaction.INFLOW, Transaction.OUTFLOW}:
        qs = qs.filter(direction=direction)

    # date range filters (optional)
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    try:
        if start_date:
            sd = datetime.date.fromisoformat(start_date)
            qs = qs.filter(date__gte=sd)
    except Exception:
        sd = None
    try:
        if end_date:
            ed = datetime.date.fromisoformat(end_date)
            qs = qs.filter(date__lte=ed)
    except Exception:
        ed = None

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

    # Load user's column settings (server-side persisted)
    try:
        setting, _ = UserTableSetting.objects.get_or_create(user=request.user)
        columns = setting.columns or DEFAULT_COLUMNS
        columns = [c for c in columns if c in ALLOWED_COLUMNS]
        if not columns:
            columns = DEFAULT_COLUMNS
    except Exception:
        columns = DEFAULT_COLUMNS

    # Human readable labels for columns
    column_labels = {
        'date': 'Date', 'description': 'Description', 'category': 'Category', 'subcategory': 'Subcategory',
        'amount': 'Amount', 'direction': 'Direction', 'account': 'Account', 'source': 'Source',
        'created_at': 'Created', 'updated_at': 'Updated'
    }

    context = {
        'title': 'Transactions',
        'page': page,
        'q': q,
        'sort': sort,
        'direction': direction,
        'params': params.urlencode(),
        'start_date': start_date,
        'end_date': end_date,
        'columns': columns,
        'column_labels': column_labels,
        'all_columns': ALLOWED_COLUMNS,
    }
    return render(request, 'app_web/transactions.html', context)


@login_required
def transaction_edit_view(request, tx_id):
    tx = get_object_or_404(Transaction, id=tx_id, user=request.user)
    # Determine redirect params: prefer POST.next (modal submit) else GET params
    if request.method == 'POST':
        next_params = request.POST.get('next', '')
        form = TransactionForm(request.POST, instance=tx)
        if form.is_valid():
            form.save()
            # If this is an AJAX request (modal), return JSON so the frontend can update in-place
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                tx.refresh_from_db()
                return JsonResponse({
                    'ok': True,
                    'tx': {
                        'id': tx.id,
                        'date': str(tx.date),
                        'description': tx.description,
                        'amount': str(tx.amount),
                        'direction': tx.direction,
                        'category': tx.category,
                        'subcategory': tx.subcategory,
                    }
                })
            messages.success(request, 'Transaction updated')
            url = '/transactions/' + (f'?{next_params}' if next_params else '')
            return redirect(url)
        else:
            # If AJAX, return field errors as JSON so the modal can show them inline
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                # Convert form.errors (ErrorDict) to a simple dict of lists
                errors = {k: [str(vv) for vv in v] for k, v in form.errors.items()}
                return JsonResponse({'ok': False, 'errors': errors}, status=400)
            messages.error(request, 'Please fix the errors below')
        params = next_params
    else:
        params = request.GET.urlencode()
        form = TransactionForm(instance=tx)
    return render(request, 'app_web/transaction_form.html', {'form': form, 'tx': tx, 'params': params})


@login_required
def transaction_delete_view(request, tx_id):
    # deletion should come as POST (csrf-protected). Accepts optional 'next' params to redirect back
    tx = get_object_or_404(Transaction, id=tx_id, user=request.user)
    next_params = request.POST.get('next', '') if request.method == 'POST' else request.GET.urlencode()
    if request.method == 'POST':
        # confirm deletion
        try:
            tx.delete()
            messages.success(request, 'Transaction deleted')
        except Exception as e:
            messages.error(request, f'Failed to delete transaction: {e}')
        url = '/transactions/' + (f'?{next_params}' if next_params else '')
        return redirect(url)
    # For GET, render a small confirm page (not usually used because we'll use modal)
    return render(request, 'app_web/transaction_confirm_delete.html', {'tx': tx, 'params': next_params})

@login_required
def transaction_bulk_edit_view(request):
    """Apply bulk edits to selected transactions. Expects POST with 'ids' (comma-separated) and optional fields to update: date, description, amount, direction, category, subcategory. Only non-empty fields will be applied."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request')
        return redirect('/transactions/')

    ids_raw = request.POST.get('ids', '')
    next_params = request.POST.get('next', '')
    if not ids_raw:
        messages.error(request, 'No transactions selected for bulk edit')
        return redirect('/transactions/' + (f'?{next_params}' if next_params else ''))

    ids = [int(x) for x in ids_raw.split(',') if x.strip().isdigit()]
    if not ids:
        messages.error(request, 'No valid transactions selected')
        return redirect('/transactions/' + (f'?{next_params}' if next_params else ''))

    # Collect fields
    updates = {}
    date = request.POST.get('date','').strip()
    if date:
        try:
            updates['date'] = datetime.date.fromisoformat(date)
        except Exception:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'errors': {'date': ['Invalid date format']}}, status=400)
            messages.error(request, 'Invalid date format for bulk edit')
            return redirect('/transactions/' + (f'?{next_params}' if next_params else ''))
    desc = request.POST.get('description','').strip()
    if desc:
        updates['description'] = desc[:512]
    amount = request.POST.get('amount','').strip()
    if amount:
        try:
            amt = Decimal(str(amount).replace(',','').replace('£','').strip())
            updates['amount'] = abs(amt)
        except Exception:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'errors': {'amount': ['Invalid amount format']}}, status=400)
            messages.error(request, 'Invalid amount for bulk edit')
            return redirect('/transactions/' + (f'?{next_params}' if next_params else ''))
    direction = request.POST.get('direction','').strip()
    if direction in {Transaction.INFLOW, Transaction.OUTFLOW}:
        updates['direction'] = direction
    category = request.POST.get('category','').strip()
    if category:
        updates['category'] = category
    subcategory = request.POST.get('subcategory','').strip()
    if subcategory:
        updates['subcategory'] = subcategory

    if not updates:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'errors': {'__all__': ['No fields provided to update']}}, status=400)
        messages.error(request, 'No fields provided to update')
        return redirect('/transactions/' + (f'?{next_params}' if next_params else ''))

    # Apply updates only to transactions owned by the user
    qs = Transaction.objects.filter(id__in=ids, user=request.user)
    # Ensure updated_at is updated for bulk operations
    updates['updated_at'] = timezone.now()
    count = qs.update(**updates)
    # For AJAX requests, return JSON with list of affected ids and applied updates so the frontend can update rows
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Make applied values JSON-serializable (dates/decimals -> strings)
        applied_safe = {}
        for k, v in updates.items():
            try:
                # handle date/time
                if isinstance(v, (datetime.date, datetime.datetime)):
                    applied_safe[k] = str(v)
                # handle Decimal
                elif isinstance(v, Decimal):
                    applied_safe[k] = str(v)
                else:
                    applied_safe[k] = v
            except Exception:
                applied_safe[k] = str(v)
        return JsonResponse({'ok': True, 'updated_count': count, 'updated_ids': ids, 'applied': applied_safe})
    messages.success(request, f'Updated {count} transaction(s)')
    return redirect('/transactions/' + (f'?{next_params}' if next_params else ''))

@login_required
@require_http_methods(['GET', 'POST'])
def transaction_columns_view(request):
    """GET returns current columns (JSON). POST accepts JSON {columns: [...]}, validates and saves for the user."""
    if request.method == 'GET':
        setting, _ = UserTableSetting.objects.get_or_create(user=request.user)
        cols = setting.columns or DEFAULT_COLUMNS
        # sanitize unknown columns
        cols = [c for c in cols if c in ALLOWED_COLUMNS]
        if not cols:
            cols = DEFAULT_COLUMNS
        return JsonResponse({'columns': cols})

    # POST: accept JSON or form-encoded
    payload = {}
    try:
        if request.content_type and 'application/json' in request.content_type:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        else:
            # form-encoded: repeated fields or comma-separated
            if 'columns' in request.POST:
                # allow comma-separated string
                payload['columns'] = [x.strip() for x in request.POST.get('columns','').split(',') if x.strip()]
            else:
                # collect columns[] style
                payload['columns'] = request.POST.getlist('columns')
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid payload'}, status=400)

    cols = payload.get('columns', []) or []
    if not isinstance(cols, list):
        return JsonResponse({'ok': False, 'error': 'columns must be a list'}, status=400)

    # sanitize and keep order
    final = [c for c in cols if c in ALLOWED_COLUMNS]
    if not final:
        return JsonResponse({'ok': False, 'error': 'No valid columns provided'}, status=400)

    setting, _ = UserTableSetting.objects.get_or_create(user=request.user)
    setting.columns = final
    setting.save()
    return JsonResponse({'ok': True, 'columns': final})
