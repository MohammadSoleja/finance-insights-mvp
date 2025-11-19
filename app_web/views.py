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
from .models import UserTableSetting
from django.db.models import Sum

import math
import json
import datetime
import calendar
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
    ksd = None
    ked = None
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
        # set KPI bounds so previous-period comparison can be computed for explicit ranges
        # only set when both start and end are present (we need a full window)
        if sd and ed:
            ksd = sd
            ked = ed
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

    # ---- Prior period KPIs (for delta/compare) ----
    # Compute previous period range with same length as kpi range
    kpi_prev = None
    kpi_delta = {}
    prev_start = None
    prev_end = None
    try:
        if ksd and ked:
            period_len = (ked - ksd).days + 1
            # If the selected window is exactly a calendar month, compare with previous calendar month
            is_full_month = False
            try:
                if ksd.day == 1 and ksd.month == ked.month and ksd.year == ked.year:
                    last_day = calendar.monthrange(ksd.year, ksd.month)[1]
                    if ked.day == last_day:
                        is_full_month = True
            except Exception:
                is_full_month = False

            if is_full_month:
                # previous calendar month
                prev_month = ksd.month - 1
                prev_year = ksd.year
                if prev_month == 0:
                    prev_month = 12
                    prev_year -= 1
                prev_start = datetime.date(prev_year, prev_month, 1)
                prev_end = datetime.date(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1])
            else:
                # previous continuous window of same length immediately before ksd
                prev_end = ksd - datetime.timedelta(days=1)
                prev_start = prev_end - datetime.timedelta(days=period_len - 1)

        prev_q = Q(user=user)
        # Apply same category filter to prior period so KPIs compare apples-to-apples
        if category:
            prev_q &= Q(category=category)
        prev_q &= Q(date__gte=prev_start)
        prev_q &= Q(date__lte=prev_end)
        qs_prev = Transaction.objects.filter(prev_q).order_by('date')
        df_prev = queryset_to_df(qs_prev)
        prev_kpi = kpi_calc(df_prev)
        kpi_prev = prev_kpi
        # compute deltas for inflow/outflow/net
        def _delta(cur, prev):
            abs_delta = round(cur - prev, 2)
            pct = None
            try:
                if prev != 0:
                    pct = round((abs_delta / abs(prev)) * 100.0, 1)
            except Exception:
                pct = None
            return {"abs": abs_delta, "pct": pct}
        kpi_delta = {
            'inflow': _delta(kpi.get('inflow', 0.0), prev_kpi.get('inflow', 0.0)),
            'outflow': _delta(kpi.get('outflow', 0.0), prev_kpi.get('outflow', 0.0)),
            'net': _delta(kpi.get('net', 0.0), prev_kpi.get('net', 0.0)),
        }
    except Exception:
        kpi_prev = None
        kpi_delta = {}

    # ---- Top Category Share ----
    # Compute top 3 outflow categories and top 3 inflow categories for the KPI window
    top_outflows = []
    top_inflows = []
    try:
        cat_q = Q(user=user)
        if ksd:
            cat_q &= Q(date__gte=ksd)
        if ked:
            cat_q &= Q(date__lte=ked)
        if category:
            cat_q &= Q(category=category)

        # Outflows
        out_totals_qs = Transaction.objects.filter(cat_q & Q(direction=Transaction.OUTFLOW))
        total_out = float(out_totals_qs.aggregate(total=Sum('amount')).get('total') or 0.0)
        out_totals = out_totals_qs.values('category').annotate(total=Sum('amount')).order_by('-total')[:3]

        # Prepare previous-period totals for change calculation
        prev_out_map = {}
        prev_total_out = 0.0
        if ksd is not None and ked is not None:
            period_len = (ked - ksd).days + 1
            prev_end = ksd - datetime.timedelta(days=1)
            prev_start = prev_end - datetime.timedelta(days=period_len - 1)
            prev_q = Q(user=user, date__gte=prev_start, date__lte=prev_end)
            if category:
                prev_q &= Q(category=category)
            prev_out_qs = Transaction.objects.filter(prev_q & Q(direction=Transaction.OUTFLOW))
            prev_total_out = float(prev_out_qs.aggregate(total=Sum('amount')).get('total') or 0.0)
            for r in prev_out_qs.values('category').annotate(total=Sum('amount')):
                prev_out_map[r.get('category') or 'Uncategorised'] = float(r.get('total') or 0.0)

        for t in out_totals:
            name = t.get('category') or 'Uncategorised'
            value = float(t.get('total') or 0.0)
            pct = round((value / total_out) * 100.0, 1) if total_out > 0 else None
            # compute change in share compared to prev period (percentage points)
            change = None
            if name in prev_out_map and prev_total_out > 0 and pct is not None:
                prev_pct = round((prev_out_map.get(name, 0.0) / prev_total_out) * 100.0, 1)
                change = round(pct - prev_pct, 1)
            elif prev_total_out == 0 and (prev_out_map.get(name, 0.0) == 0) and pct is not None:
                # previous period had zero total -> change defined as None (no baseline)
                change = None
            top_outflows.append({'name': name, 'value': round(value,2), 'percent': pct, 'change': change, 'change_abs': (round(abs(change),1) if change is not None else None)})

        # Inflows
        in_totals_qs = Transaction.objects.filter(cat_q & Q(direction=Transaction.INFLOW))
        total_in = float(in_totals_qs.aggregate(total=Sum('amount')).get('total') or 0.0)
        in_totals = in_totals_qs.values('category').annotate(total=Sum('amount')).order_by('-total')[:3]

        # previous-period inflow map
        prev_in_map = {}
        prev_total_in = 0.0
        if ksd is not None and ked is not None:
            period_len = (ked - ksd).days + 1
            prev_end = ksd - datetime.timedelta(days=1)
            prev_start = prev_end - datetime.timedelta(days=period_len - 1)
            prev_q = Q(user=user, date__gte=prev_start, date__lte=prev_end)
            if category:
                prev_q &= Q(category=category)
            prev_in_qs = Transaction.objects.filter(prev_q & Q(direction=Transaction.INFLOW))
            prev_total_in = float(prev_in_qs.aggregate(total=Sum('amount')).get('total') or 0.0)
            for r in prev_in_qs.values('category').annotate(total=Sum('amount')):
                prev_in_map[r.get('category') or 'Uncategorised'] = float(r.get('total') or 0.0)

        for t in in_totals:
            name = t.get('category') or 'Uncategorised'
            value = float(t.get('total') or 0.0)
            pct = round((value / total_in) * 100.0, 1) if total_in > 0 else None
            change = None
            if name in prev_in_map and prev_total_in > 0 and pct is not None:
                prev_pct = round((prev_in_map.get(name, 0.0) / prev_total_in) * 100.0, 1)
                change = round(pct - prev_pct, 1)
            top_inflows.append({'name': name, 'value': round(value,2), 'percent': pct, 'change': change, 'change_abs': (round(abs(change),1) if change is not None else None)})
    except Exception:
        top_outflows = []
        top_inflows = []

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
        "kpi_prev": kpi_prev,
        "kpi_delta": kpi_delta,
        # "top_category": top_category,
        "top_outflows": top_outflows,
        "top_inflows": top_inflows,
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

    # Get budget summary for widget (top 3 at-risk budgets)
    from app_core.budgets import get_budget_summary
    try:
        budget_summary = get_budget_summary(user, Transaction)[:3]  # Top 3 for widget
        context['budget_summary'] = budget_summary
    except Exception:
        context['budget_summary'] = []

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
        form = TransactionForm(request.POST, instance=tx, user=request.user)
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
                        'label': tx.label.name if tx.label else '',
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
        form = TransactionForm(instance=tx, user=request.user)
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


# ========================================
# Budget Views
# ========================================

@login_required
def budgets_view(request):
    """Budget management page - list, create, edit, delete budgets."""
    from app_core.models import Budget
    from app_core.budgets import get_budget_summary
    from .forms import BudgetForm

    # Get budget summary with usage
    budget_summary = get_budget_summary(request.user, Transaction)

    # Handle form submission for creating/editing budget
    form = BudgetForm(user=request.user)
    edit_budget = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            form = BudgetForm(request.POST, user=request.user)
            if form.is_valid():
                budget = form.save(commit=False)
                budget.user = request.user
                try:
                    # Convert all non-custom period budgets to custom with specific dates for consistent display
                    if budget.period != Budget.PERIOD_CUSTOM:
                        from app_core.recurring_budgets import get_period_end
                        from datetime import date
                        from dateutil.relativedelta import relativedelta
                        import uuid

                        # Generate recurring group ID for linking related budgets
                        if budget.is_recurring and budget.recurrence_count:
                            recurring_group_id = str(uuid.uuid4())
                            budget.recurring_group_id = recurring_group_id

                        # Calculate start/end dates for the current period
                        today = timezone.now().date()
                        if budget.period == Budget.PERIOD_MONTHLY:
                            # First and last day of current month
                            period_start = today.replace(day=1)
                            period_end = get_period_end(period_start, budget.period)
                        elif budget.period == Budget.PERIOD_WEEKLY:
                            # Current week (Monday to Sunday)
                            period_start = today - timezone.timedelta(days=today.weekday())
                            period_end = get_period_end(period_start, budget.period)
                        elif budget.period == Budget.PERIOD_YEARLY:
                            # Current year
                            period_start = date(today.year, 1, 1)
                            period_end = get_period_end(period_start, budget.period)
                        else:
                            period_start = budget.start_date
                            period_end = budget.end_date

                        # Store original period type before converting to custom (needed for recurring generation)
                        original_period = budget.period

                        # Convert to custom period with specific dates
                        budget.period = Budget.PERIOD_CUSTOM
                        budget.start_date = period_start
                        budget.end_date = period_end

                        budget.save()
                        form.save_m2m()  # Save many-to-many labels

                        # If recurring, generate future periods
                        if budget.is_recurring and budget.recurrence_count:
                            # Temporarily set period back for generation logic
                            budget.period = original_period
                            budget.save(update_fields=['period'])

                            from app_core.recurring_budgets import generate_recurring_budgets
                            generated_count = generate_recurring_budgets(user=request.user)

                            # Convert back to custom after generation
                            budget.period = Budget.PERIOD_CUSTOM
                            budget.save(update_fields=['period'])

                            messages.success(request, f'Recurring budget "{budget.name}" created ({generated_count} future periods generated)')
                        else:
                            messages.success(request, f'Budget "{budget.name}" created')
                    else:
                        # Custom period - save as-is
                        budget.save()
                        form.save_m2m()  # Save many-to-many labels
                        messages.success(request, f'Budget "{budget.name}" created')

                    return redirect('app_web:budgets')
                except Exception as e:
                    messages.error(request, f'Error creating budget: {str(e)}')
            else:
                messages.error(request, 'Please correct the errors below')

        elif action == 'edit':
            budget_id = request.POST.get('budget_id')
            edit_scope = request.POST.get('edit_scope', 'this')  # this, future, or all
            recurring_group_id = request.POST.get('recurring_group_id', '')

            try:
                edit_budget = Budget.objects.get(id=budget_id, user=request.user)
                form = BudgetForm(request.POST, instance=edit_budget, user=request.user)
                if form.is_valid():
                    budget = form.save()

                    # If this budget is part of a recurring group and scope is not 'this'
                    if recurring_group_id and edit_scope in ['future', 'all']:
                        budgets_to_update = Budget.objects.filter(
                            user=request.user,
                            recurring_group_id=recurring_group_id
                        ).exclude(id=budget_id)

                        # For 'future', only update budgets with start_date >= current budget's start_date
                        if edit_scope == 'future' and budget.start_date:
                            budgets_to_update = budgets_to_update.filter(start_date__gte=budget.start_date)
                        # For 'all', update all budgets in the group (no additional filter needed)

                        # Update fields for all budgets in scope
                        update_fields = {
                            'name': budget.name,
                            'amount': budget.amount,
                            'active': budget.active,
                            'updated_at': timezone.now()
                        }

                        count = budgets_to_update.update(**update_fields)

                        # Update labels for each budget (M2M relationship)
                        for b in budgets_to_update:
                            b.labels.clear()
                            for label in budget.labels.all():
                                b.labels.add(label)

                        if edit_scope == 'future':
                            messages.success(request, f'Budget "{budget.name}" updated (+ {count} future budgets)')
                        else:
                            messages.success(request, f'Budget "{budget.name}" updated (+ {count} related budgets)')
                    else:
                        messages.success(request, f'Budget "{budget.name}" updated')

                    return redirect('app_web:budgets')
                else:
                    messages.error(request, 'Please correct the errors below')
            except Budget.DoesNotExist:
                messages.error(request, 'Budget not found')

        elif action == 'delete':
            budget_id = request.POST.get('budget_id')
            try:
                budget = Budget.objects.get(id=budget_id, user=request.user)
                budget.delete()
                # Silent delete - no success message
                return redirect('app_web:budgets')
            except Budget.DoesNotExist:
                messages.error(request, 'Budget not found')

        elif action == 'bulk_delete':
            budget_ids_str = request.POST.get('budget_ids', '')
            if budget_ids_str:
                budget_ids = [int(id.strip()) for id in budget_ids_str.split(',') if id.strip().isdigit()]
                deleted_count = Budget.objects.filter(id__in=budget_ids, user=request.user).delete()[0]
                if deleted_count > 0:
                    messages.success(request, f'{deleted_count} budget(s) deleted')
                return redirect('app_web:budgets')
            else:
                messages.error(request, 'No budgets selected for deletion')

    # Handle GET request for editing (populate form)
    if request.method == 'GET' and 'edit' in request.GET:
        budget_id = request.GET.get('edit')
        try:
            edit_budget = Budget.objects.get(id=budget_id, user=request.user)
            form = BudgetForm(instance=edit_budget, user=request.user)
        except Budget.DoesNotExist:
            messages.error(request, 'Budget not found')

    # Convert budget_summary to JSON for JavaScript
    # Need to convert date objects to strings for JSON serialization
    import json
    from datetime import date, datetime
    import math

    def date_handler(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    # Sanitize budget_summary to remove NaN/Infinity values
    def sanitize_for_json(data):
        """Remove NaN and Infinity values from data structure"""
        if isinstance(data, dict):
            return {k: sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [sanitize_for_json(item) for item in data]
        elif isinstance(data, float):
            if math.isnan(data) or math.isinf(data):
                return 0
            return data
        return data

    budget_summary_sanitized = sanitize_for_json(budget_summary)
    budget_summary_json = json.dumps(budget_summary_sanitized, default=date_handler, allow_nan=False)

    context = {
        'title': 'Budget Management',
        'budget_summary': budget_summary,
        'budget_summary_json': budget_summary_json,
        'form': form,
        'edit_budget': edit_budget,
    }

    return render(request, 'app_web/budgets.html', context)


@login_required
def budget_widget_data(request):
    """AJAX endpoint to get budget widget data for dashboard."""
    from app_core.budgets import get_budget_summary

    summary = get_budget_summary(request.user, Transaction)

    # Return top 3 budgets (by percent used) for widget
    widget_data = summary[:3]

    return JsonResponse({
        'ok': True,
        'budgets': widget_data,
        'total_count': len(summary)
    })


@login_required
def budget_list_data(request):
    """AJAX endpoint to get all budget data for the budget management page."""
    from app_core.budgets import get_budget_summary

    summary = get_budget_summary(request.user, Transaction)

    return JsonResponse({
        'ok': True,
        'budgets': summary,
        'count': len(summary)
    })


@login_required
def projects_view(request):
    """Project management page - list, create, edit, delete projects with hierarchy support."""
    from app_core.models import Project, Label, ProjectMilestone, ProjectBudgetCategory
    from app_core.projects import get_project_summary, log_project_activity

    # Handle POST requests for create/edit/delete
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            try:
                # Get parent project if specified
                parent_id = request.POST.get('parent_project')
                parent_project = None
                level = 0

                if parent_id:
                    parent_project = get_object_or_404(Project, id=parent_id, user=request.user)
                    level = parent_project.level + 1

                    # Enforce max 3 levels (0, 1, 2)
                    if level > 2:
                        return JsonResponse({'ok': False, 'error': 'Maximum nesting depth (3 levels) exceeded'}, status=400)

                # Create new project
                project = Project.objects.create(
                    user=request.user,
                    name=request.POST.get('name'),
                    description=request.POST.get('description', ''),
                    budget=request.POST.get('budget') if request.POST.get('budget') else None,
                    start_date=request.POST.get('start_date') if request.POST.get('start_date') else None,
                    end_date=request.POST.get('end_date') if request.POST.get('end_date') else None,
                    status=request.POST.get('status', 'active'),
                    color=request.POST.get('color', '#3b82f6'),
                    parent_project=parent_project,
                    level=level,
                )

                # Add labels
                label_ids = request.POST.getlist('labels')
                if label_ids:
                    project.labels.set(label_ids)

                # Log activity
                log_project_activity(
                    project,
                    request.user,
                    'created',
                    f'Project "{project.name}" created'
                )

                if parent_project:
                    log_project_activity(
                        parent_project,
                        request.user,
                        'sub_project_added',
                        f'Sub-project "{project.name}" added'
                    )

                return JsonResponse({'ok': True, 'message': 'Project created successfully', 'project_id': project.id})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        elif action == 'edit':
            try:
                project_id = request.POST.get('project_id')
                project = get_object_or_404(Project, id=project_id, user=request.user)

                # Update fields
                old_budget = project.budget
                project.name = request.POST.get('name')
                project.description = request.POST.get('description', '')
                project.budget = request.POST.get('budget') if request.POST.get('budget') else None
                project.start_date = request.POST.get('start_date') if request.POST.get('start_date') else None
                project.end_date = request.POST.get('end_date') if request.POST.get('end_date') else None
                old_status = project.status
                project.status = request.POST.get('status', 'active')
                project.color = request.POST.get('color', '#3b82f6')
                project.save()

                # Update labels
                label_ids = request.POST.getlist('labels')
                project.labels.set(label_ids if label_ids else [])

                # Log activities
                log_project_activity(project, request.user, 'updated', f'Project "{project.name}" updated')

                if old_budget != project.budget:
                    log_project_activity(
                        project,
                        request.user,
                        'budget_changed',
                        f'Budget changed from £{old_budget or 0} to £{project.budget or 0}'
                    )

                if old_status != project.status:
                    log_project_activity(
                        project,
                        request.user,
                        'status_changed',
                        f'Status changed from {old_status} to {project.status}'
                    )

                return JsonResponse({'ok': True, 'message': 'Project updated successfully'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        elif action == 'delete':
            try:
                project_id = request.POST.get('project_id')
                project = get_object_or_404(Project, id=project_id, user=request.user)
                project_name = project.name
                project.delete()
                return JsonResponse({'ok': True, 'message': f'Project "{project_name}" deleted successfully'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        elif action == 'bulk_delete':
            try:
                project_ids = request.POST.getlist('project_ids[]')
                count = Project.objects.filter(id__in=project_ids, user=request.user).delete()[0]
                return JsonResponse({'ok': True, 'message': f'{count} project(s) deleted successfully'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        elif action == 'add_milestone':
            try:
                project_id = request.POST.get('project_id')
                project = get_object_or_404(Project, id=project_id, user=request.user)

                milestone = ProjectMilestone.objects.create(
                    project=project,
                    name=request.POST.get('name'),
                    description=request.POST.get('description', ''),
                    due_date=request.POST.get('due_date'),
                    status=request.POST.get('status', 'pending'),
                    budget=request.POST.get('budget') if request.POST.get('budget') else None,
                    owner=request.POST.get('owner', ''),
                    order=project.milestones.count(),
                )

                log_project_activity(
                    project,
                    request.user,
                    'milestone_added',
                    f'Milestone "{milestone.name}" added'
                )

                return JsonResponse({'ok': True, 'message': 'Milestone added successfully', 'milestone_id': milestone.id})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        elif action == 'add_budget_category':
            try:
                project_id = request.POST.get('project_id')
                project = get_object_or_404(Project, id=project_id, user=request.user)

                category = ProjectBudgetCategory.objects.create(
                    project=project,
                    name=request.POST.get('name'),
                    allocated_amount=request.POST.get('allocated_amount'),
                    color=request.POST.get('color', '#6b7280'),
                )

                # Add labels
                label_ids = request.POST.getlist('labels')
                if label_ids:
                    category.labels.set(label_ids)

                return JsonResponse({'ok': True, 'message': 'Budget category added successfully', 'category_id': category.id})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    # GET request - render page
    # Get all user labels for the label selector
    labels = Label.objects.filter(user=request.user).order_by('name')

    # Get all parent projects (for sub-project creation)
    parent_projects = Project.objects.filter(user=request.user, level__lt=2).order_by('name')

    # Get project summary with hierarchy
    projects_summary = get_project_summary(request.user, Transaction, include_sub_projects=True)

    # Convert projects to JSON for JavaScript
    import json
    from datetime import date

    def serialize_project(proj):
        """Convert project dict to JSON-serializable format"""
        result = proj.copy()
        # Convert dates to ISO format strings
        if result.get('start_date') and isinstance(result['start_date'], date):
            result['start_date'] = result['start_date'].isoformat()
        if result.get('end_date') and isinstance(result['end_date'], date):
            result['end_date'] = result['end_date'].isoformat()
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        if result.get('updated_at'):
            result['updated_at'] = result['updated_at'].isoformat()

        # Convert Decimal to float
        for key in ['budget', 'total_inflow', 'total_outflow', 'net_amount', 'budget_variance', 'budget_variance_abs']:
            if result.get(key) is not None:
                result[key] = float(result[key])

        # Convert labels to simple list
        if result.get('labels'):
            result['labels'] = [{'id': l.id, 'name': l.name, 'color': l.color} for l in result['labels']]

        # Recursively serialize sub-projects
        if result.get('sub_projects'):
            result['sub_projects'] = [serialize_project(sp) for sp in result['sub_projects']]

        # Serialize budget categories
        if result.get('budget_categories'):
            for cat in result['budget_categories']:
                for key in ['allocated', 'spent', 'remaining', 'usage_pct']:
                    if key in cat:
                        cat[key] = float(cat[key])

        return result

    serialized_projects = [serialize_project(p) for p in projects_summary]
    projects_json = json.dumps(serialized_projects)

    # Debug: Print to console
    print(f"DEBUG: Found {len(projects_summary)} projects for user {request.user.username}")
    print(f"DEBUG: JSON length: {len(projects_json)} characters")
    if projects_summary:
        print(f"DEBUG: First project: {projects_summary[0].get('name', 'Unknown')}")

    context = {
        'title': 'Projects',
        'labels': labels,
        'projects': projects_json,  # JSON string for JavaScript
        'parent_projects': parent_projects,
    }

    return render(request, 'app_web/projects.html', context)


@login_required
def project_list_data(request):
    """AJAX endpoint to get all project data."""
    from app_core.projects import get_project_summary

    summary = get_project_summary(request.user, Transaction)

    return JsonResponse({
        'ok': True,
        'projects': summary,
        'count': len(summary)
    })


@login_required
def project_detail_data(request, project_id):
    """AJAX endpoint to get detailed project data including transactions, P&L, milestones, budget categories, and activities."""
    from app_core.models import Project
    from app_core.projects import get_project_transactions, calculate_project_pl

    project = get_object_or_404(Project, id=project_id, user=request.user)

    # Get P&L calculation
    pl_data = calculate_project_pl(project, Transaction)

    # Get transactions
    transactions = get_project_transactions(project, Transaction)
    tx_list = []
    for tx in transactions[:100]:  # Limit to 100 most recent
        tx_list.append({
            'id': tx.id,
            'date': tx.date.isoformat(),
            'description': tx.description,
            'amount': float(tx.amount),
            'direction': tx.direction,
            'label': tx.label.name if tx.label else 'Uncategorized',
            'label_color': tx.label.color if tx.label else '#6b7280',
        })

    # Get milestones
    milestones_list = []
    for milestone in project.milestones.all():
        milestones_list.append({
            'id': milestone.id,
            'name': milestone.name,
            'description': milestone.description,
            'due_date': milestone.due_date.isoformat(),
            'completed_date': milestone.completed_date.isoformat() if milestone.completed_date else None,
            'status': milestone.status,
            'status_display': milestone.get_status_display(),
            'budget': float(milestone.budget) if milestone.budget else None,
            'owner': milestone.owner,
            'order': milestone.order,
        })

    # Get budget categories with spending
    budget_categories_list = []
    for category in project.budget_categories.all():
        from app_core.projects import _calculate_category_spending
        spent = _calculate_category_spending(category, Transaction)
        budget_categories_list.append({
            'id': category.id,
            'name': category.name,
            'allocated': float(category.allocated_amount),
            'spent': float(spent),
            'remaining': float(category.allocated_amount - spent),
            'usage_pct': float((spent / category.allocated_amount) * 100) if category.allocated_amount > 0 else 0,
            'color': category.color,
            'label_ids': list(category.labels.values_list('id', flat=True)),
        })

    # Get sub-projects
    sub_projects_list = []
    for sub in project.sub_projects.all():
        sub_projects_list.append({
            'id': sub.id,
            'name': sub.name,
            'status': sub.status,
            'budget': float(sub.budget) if sub.budget else None,
            'level': sub.level,
        })

    # Get recent activities
    activities_list = []
    for activity in project.activities.all()[:20]:  # Last 20 activities
        activities_list.append({
            'id': activity.id,
            'action': activity.action,
            'action_display': activity.get_action_display(),
            'description': activity.description,
            'user': activity.user.username,
            'created_at': activity.created_at.isoformat(),
        })

    return JsonResponse({
        'ok': True,
        'project': {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'budget': float(project.budget) if project.budget else None,
            'status': project.status,
            'start_date': project.start_date.isoformat() if project.start_date else None,
            'end_date': project.end_date.isoformat() if project.end_date else None,
            'color': project.color,
            'label_ids': list(project.labels.values_list('id', flat=True)),
            'level': project.level,
            'parent_project_id': project.parent_project_id if project.parent_project else None,
        },
        'pl': {
            'total_inflow': float(pl_data['total_inflow']),
            'total_outflow': float(pl_data['total_outflow']),
            'net_profit': float(pl_data['net_profit']),
            'profit_margin_pct': pl_data['profit_margin_pct'],
            'inflow_by_label': {k: float(v) for k, v in pl_data['inflow_by_label'].items()},
            'outflow_by_label': {k: float(v) for k, v in pl_data['outflow_by_label'].items()},
        },
        'transactions': tx_list,
        'transaction_count': transactions.count(),
        'milestones': milestones_list,
        'budget_categories': budget_categories_list,
        'sub_projects': sub_projects_list,
        'activities': activities_list,
    })


# ==================== INVOICING & BILLING VIEWS ====================

@login_required
def invoices_view(request):
    """Main invoices list page"""
    from app_core.models import Invoice, Client
    from app_core.invoicing import get_invoice_statistics
    from datetime import date
    from decimal import Decimal

    # Get filter parameters
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')

    # Base queryset
    invoices = Invoice.objects.filter(user=request.user).select_related('client', 'project')

    # Apply filters
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    if client_filter:
        invoices = invoices.filter(client_id=client_filter)

    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)

    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)

    if search_query:
        from django.db.models import Q
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(client__company__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    # Update overdue invoices
    today = date.today()
    overdue_invoices = invoices.filter(
        status__in=[Invoice.STATUS_SENT, Invoice.STATUS_PARTIALLY_PAID],
        due_date__lt=today
    )
    overdue_invoices.update(status=Invoice.STATUS_OVERDUE)

    # Get stats
    stats = get_invoice_statistics(request.user)

    # Get all clients for filter dropdown
    clients = Client.objects.filter(user=request.user, active=True).order_by('name')

    # Serialize invoices
    invoices_list = []
    for inv in invoices:
        invoices_list.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'client': {
                'id': inv.client.id,
                'name': inv.client.name,
                'company': inv.client.company,
            },
            'invoice_date': inv.invoice_date.isoformat(),
            'due_date': inv.due_date.isoformat(),
            'status': inv.status,
            'status_display': inv.get_status_display(),
            'total': float(inv.total),
            'paid_amount': float(inv.paid_amount),
            'balance_due': float(inv.balance_due),
            'currency': inv.currency,
            'is_overdue': inv.is_overdue,
            'project': {'id': inv.project.id, 'name': inv.project.name} if inv.project else None,
        })

    context = {
        'invoices': invoices_list,
        'clients': list(clients.values('id', 'name', 'company')),
        'stats': stats,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }

    return render(request, "app_web/invoices.html", context)


@login_required
def clients_view(request):
    """Clients management page"""
    from app_core.models import Client
    from app_core.invoicing import get_client_statistics

    clients = Client.objects.filter(user=request.user).order_by('name')

    clients_list = []
    for client in clients:
        stats = get_client_statistics(client)
        clients_list.append({
            'id': client.id,
            'name': client.name,
            'email': client.email,
            'company': client.company,
            'phone': client.phone,
            'address': client.address,
            'tax_id': client.tax_id,
            'payment_terms': client.payment_terms,
            'currency': client.currency,
            'notes': client.notes,
            'active': client.active,
            'created_at': client.created_at.isoformat(),
            'stats': stats,
        })

    return render(request, "app_web/clients.html", {'clients': clients_list})


@login_required
def clients_list_api(request):
    """API endpoint to get list of clients for dropdowns"""
    from app_core.models import Client

    clients = Client.objects.filter(user=request.user, active=True).order_by('name')

    clients_list = []
    for client in clients:
        clients_list.append({
            'id': client.id,
            'name': client.name,
            'company': client.company,
            'email': client.email,
        })

    return JsonResponse({'clients': clients_list})


@login_required
@require_http_methods(["POST"])
def invoice_create_view(request):
    """Create a new invoice"""
    from app_core.models import Invoice, InvoiceItem, Client
    from app_core.invoicing import generate_invoice_number
    from datetime import date, timedelta
    import json

    try:
        data = json.loads(request.body)

        client = Client.objects.get(id=data['client_id'], user=request.user)

        # Parse dates
        invoice_date = date.fromisoformat(data.get('invoice_date', date.today().isoformat()))
        due_date = date.fromisoformat(data.get('due_date', (date.today() + timedelta(days=30)).isoformat()))

        # Create invoice
        invoice = Invoice.objects.create(
            user=request.user,
            client=client,
            invoice_number=generate_invoice_number(request.user),
            invoice_date=invoice_date,
            due_date=due_date,
            status=data.get('status', Invoice.STATUS_DRAFT),
            tax_rate=Decimal(str(data.get('tax_rate', 0))),
            discount=Decimal(str(data.get('discount', 0))),
            currency=data.get('currency', client.currency),
            notes=data.get('notes', ''),
            terms=data.get('terms', ''),
            project_id=data.get('project_id') if data.get('project_id') else None,
        )

        # Add line items
        for item_data in data.get('items', []):
            InvoiceItem.objects.create(
                invoice=invoice,
                description=item_data['description'],
                quantity=Decimal(str(item_data.get('quantity', 1))),
                unit_price=Decimal(str(item_data['unit_price'])),
                order=item_data.get('order', 0),
            )

        # Calculate totals
        from app_core.invoicing import calculate_invoice_totals
        calculate_invoice_totals(invoice)

        return JsonResponse({
            'success': True,
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
        })

    except Client.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Client not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def invoice_edit_view(request, invoice_id):
    """Edit an existing invoice"""
    from app_core.models import Invoice, InvoiceItem
    from datetime import date
    import json

    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        data = json.loads(request.body)

        # Update invoice fields
        if 'invoice_date' in data:
            invoice.invoice_date = date.fromisoformat(data['invoice_date'])
        if 'due_date' in data:
            invoice.due_date = date.fromisoformat(data['due_date'])
        if 'status' in data:
            invoice.status = data['status']
        if 'tax_rate' in data:
            invoice.tax_rate = Decimal(str(data['tax_rate']))
        if 'discount' in data:
            invoice.discount = Decimal(str(data['discount']))
        if 'notes' in data:
            invoice.notes = data['notes']
        if 'terms' in data:
            invoice.terms = data['terms']

        invoice.save()

        # Update line items if provided
        if 'items' in data:
            # Delete existing items
            invoice.items.all().delete()

            # Add new items
            for item_data in data['items']:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=item_data['description'],
                    quantity=Decimal(str(item_data.get('quantity', 1))),
                    unit_price=Decimal(str(item_data['unit_price'])),
                    order=item_data.get('order', 0),
                )

            # Recalculate totals
            from app_core.invoicing import calculate_invoice_totals
            calculate_invoice_totals(invoice)

        return JsonResponse({'success': True})

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def invoice_delete_view(request, invoice_id):
    """Delete an invoice"""
    from app_core.models import Invoice

    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        invoice.delete()
        return JsonResponse({'success': True})
    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def invoice_send_view(request, invoice_id):
    """Send invoice email to client with PDF attachment"""
    from app_core.models import Invoice
    from app_core.invoicing import send_invoice_email
    import json

    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)

        # Get optional parameters from request body
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        custom_message = data.get('custom_message', None)
        cc_emails = data.get('cc_emails', None)
        bcc_emails = data.get('bcc_emails', None)

        # Send the email
        result = send_invoice_email(
            invoice=invoice,
            custom_message=custom_message,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails
        )

        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['message']
            }, status=400)

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def invoice_reminder_view(request, invoice_id):
    """Send payment reminder email for an invoice"""
    from app_core.models import Invoice
    from app_core.invoicing import send_payment_reminder
    import json

    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)

        # Get optional custom message from request body
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        custom_message = data.get('custom_message', None)

        # Send the reminder
        result = send_payment_reminder(
            invoice=invoice,
            custom_message=custom_message
        )

        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['message']
            }, status=400)

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def invoice_payment_view(request, invoice_id):
    """Record a payment for an invoice"""
    from app_core.models import Invoice
    from app_core.invoicing import record_payment
    from datetime import date
    import json

    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        data = json.loads(request.body)

        payment_date = date.fromisoformat(data.get('payment_date', date.today().isoformat()))
        amount = Decimal(str(data['amount']))
        payment_method = data.get('payment_method', 'bank_transfer')
        reference = data.get('reference', '')
        notes = data.get('notes', '')

        payment = record_payment(
            invoice=invoice,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference=reference,
            notes=notes,
        )

        return JsonResponse({
            'success': True,
            'payment_id': payment.id,
            'new_status': invoice.status,
        })

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def client_create_view(request):
    """Create a new client"""
    from app_core.models import Client
    import json

    try:
        data = json.loads(request.body)

        client = Client.objects.create(
            user=request.user,
            name=data['name'],
            email=data['email'],
            company=data.get('company', ''),
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            tax_id=data.get('tax_id', ''),
            payment_terms=data.get('payment_terms', 'Net 30'),
            currency=data.get('currency', 'GBP'),
            notes=data.get('notes', ''),
            active=data.get('active', True),
        )

        return JsonResponse({
            'success': True,
            'client_id': client.id,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def client_edit_view(request, client_id):
    """Edit a client"""
    from app_core.models import Client
    import json

    try:
        client = Client.objects.get(id=client_id, user=request.user)
        data = json.loads(request.body)

        client.name = data.get('name', client.name)
        client.email = data.get('email', client.email)
        client.company = data.get('company', client.company)
        client.phone = data.get('phone', client.phone)
        client.address = data.get('address', client.address)
        client.tax_id = data.get('tax_id', client.tax_id)
        client.payment_terms = data.get('payment_terms', client.payment_terms)
        client.currency = data.get('currency', client.currency)
        client.notes = data.get('notes', client.notes)
        client.active = data.get('active', client.active)

        client.save()

        return JsonResponse({'success': True})

    except Client.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Client not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def client_delete_view(request, client_id):
    """Delete a client"""
    from app_core.models import Client

    try:
        client = Client.objects.get(id=client_id, user=request.user)
        # Check if client has invoices
        if client.invoices.exists():
            return JsonResponse({
                'success': False,
                'error': 'Cannot delete client with existing invoices. Deactivate instead.'
            }, status=400)

        client.delete()
        return JsonResponse({'success': True})
    except Client.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Client not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def invoice_detail_view(request, invoice_id):
    """Get detailed invoice data"""
    from app_core.models import Invoice

    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)

        items = []
        for item in invoice.items.all():
            items.append({
                'id': item.id,
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'amount': float(item.amount),
                'order': item.order,
            })

        payments = []
        for payment in invoice.payments.all():
            payments.append({
                'id': payment.id,
                'amount': float(payment.amount),
                'payment_date': payment.payment_date.isoformat(),
                'payment_method': payment.payment_method,
                'payment_method_display': payment.get_payment_method_display(),
                'reference': payment.reference,
                'notes': payment.notes,
            })

        data = {
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'client': {
                'id': invoice.client.id,
                'name': invoice.client.name,
                'email': invoice.client.email,
                'company': invoice.client.company,
                'address': invoice.client.address,
                'phone': invoice.client.phone,
                'tax_id': invoice.client.tax_id,
            },
            'invoice_date': invoice.invoice_date.isoformat(),
            'due_date': invoice.due_date.isoformat(),
            'sent_date': invoice.sent_date.isoformat() if invoice.sent_date else None,
            'paid_date': invoice.paid_date.isoformat() if invoice.paid_date else None,
            'status': invoice.status,
            'status_display': invoice.get_status_display(),
            'subtotal': float(invoice.subtotal),
            'tax_rate': float(invoice.tax_rate),
            'tax_amount': float(invoice.tax_amount),
            'discount': float(invoice.discount),
            'total': float(invoice.total),
            'paid_amount': float(invoice.paid_amount),
            'balance_due': float(invoice.balance_due),
            'currency': invoice.currency,
            'notes': invoice.notes,
            'terms': invoice.terms,
            'internal_notes': invoice.internal_notes,
            'project': {'id': invoice.project.id, 'name': invoice.project.name} if invoice.project else None,
            'items': items,
            'payments': payments,
            'is_overdue': invoice.is_overdue,
        }

        return JsonResponse(data)

    except Invoice.DoesNotExist:
        return JsonResponse({'error': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def invoice_pdf_view(request, invoice_id):
    """Display invoice in PDF-ready format with download button"""
    from app_core.models import Invoice

    try:
        invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)

        context = {
            'invoice': invoice,
            'user': request.user,
        }

        return render(request, 'app_web/invoice_view.html', context)

    except Invoice.DoesNotExist:
        return HttpResponse('Invoice not found', status=404)


@login_required
def invoice_pdf_download(request, invoice_id):
    """Generate and download invoice as PDF using ReportLab"""
    from app_core.models import Invoice
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    from io import BytesIO
    from datetime import date

    try:
        invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)

        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)

        # Container for PDF elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=6,
            alignment=TA_LEFT
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            spaceAfter=12,
            spaceBefore=12
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#111827')
        )

        small_style = ParagraphStyle(
            'CustomSmall',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280')
        )

        # Title
        elements.append(Paragraph("INVOICE", title_style))
        elements.append(Paragraph(f"#{invoice.invoice_number}", heading_style))
        elements.append(Spacer(1, 0.2*inch))

        # Status badge text
        status_text = invoice.get_status_display()
        status_para = Paragraph(f"<b>Status:</b> {status_text}", normal_style)
        elements.append(status_para)
        elements.append(Spacer(1, 0.3*inch))

        # Bill To and Invoice Details side by side
        info_data = [
            [
                Paragraph("<b>BILL TO</b>", heading_style),
                Paragraph("<b>INVOICE DETAILS</b>", heading_style)
            ],
            [
                Paragraph(f"<b>{invoice.client.name}</b><br/>"
                         f"{invoice.client.company if invoice.client.company else ''}<br/>"
                         f"{invoice.client.email}<br/>"
                         f"{invoice.client.phone if invoice.client.phone else ''}", normal_style),
                Paragraph(f"<b>Invoice Date:</b> {invoice.invoice_date.strftime('%B %d, %Y')}<br/>"
                         f"<b>Due Date:</b> {invoice.due_date.strftime('%B %d, %Y')}<br/>"
                         f"<b>Payment Terms:</b> {invoice.client.payment_terms}", normal_style)
            ]
        ]

        info_table = Table(info_data, colWidths=[3*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.4*inch))

        # Line Items Table
        items_data = [['Description', 'Qty', 'Unit Price', 'Amount']]

        for item in invoice.items.all():
            items_data.append([
                item.description,
                str(item.quantity),
                f"{invoice.currency} {item.unit_price:.2f}",
                f"{invoice.currency} {item.amount:.2f}"
            ])

        items_table = Table(items_data, colWidths=[3*inch, 0.75*inch, 1.25*inch, 1.25*inch])
        items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),

            # Alignment
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Qty center
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),  # Price and Amount right

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.3*inch))

        # Totals
        totals_data = [
            ['Subtotal:', f"{invoice.currency} {invoice.subtotal:.2f}"],
        ]

        if invoice.tax_rate > 0:
            totals_data.append(['Tax ({:.1f}%):'.format(invoice.tax_rate), f"{invoice.currency} {invoice.tax_amount:.2f}"])

        if invoice.discount > 0:
            totals_data.append(['Discount:', f"-{invoice.currency} {invoice.discount:.2f}"])

        totals_data.append(['<b>Total:</b>', f"<b>{invoice.currency} {invoice.total:.2f}</b>"])

        if invoice.paid_amount > 0:
            totals_data.append(['Paid:', f"-{invoice.currency} {invoice.paid_amount:.2f}"])
            totals_data.append(['<b>Balance Due:</b>', f"<b>{invoice.currency} {invoice.balance_due:.2f}</b>"])

        # Convert to Paragraphs for bold support
        totals_data_formatted = []
        for label, value in totals_data:
            totals_data_formatted.append([
                Paragraph(label, normal_style if '<b>' not in label else heading_style),
                Paragraph(value, normal_style if '<b>' not in value else heading_style)
            ])

        totals_table = Table(totals_data_formatted, colWidths=[4.5*inch, 1.75*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (0, -2), (-1, -2), 1, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(totals_table)

        # Notes
        if invoice.notes:
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("<b>Notes:</b>", heading_style))
            elements.append(Paragraph(invoice.notes, normal_style))

        # Terms
        if invoice.terms:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Payment Terms & Conditions:</b>", heading_style))
            elements.append(Paragraph(invoice.terms, normal_style))

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        footer_text = f"<i>Thank you for your business!<br/>For questions about this invoice, please contact {request.user.email}</i>"
        elements.append(Paragraph(footer_text, small_style))

        # Build PDF
        doc.build(elements)

        # Get PDF from buffer
        pdf = buffer.getvalue()
        buffer.close()

        # Create response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'

        return response

    except Invoice.DoesNotExist:
        return HttpResponse('Invoice not found', status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'Error generating PDF: {str(e)}', status=500)


# ==================== INVOICE TEMPLATES VIEWS ====================

@login_required
def invoice_templates_view(request):
    """Invoice templates management page"""
    from app_core.invoicing import get_user_templates

    templates = get_user_templates(request.user)

    return render(request, 'app_web/invoice_templates.html', {
        'title': 'Invoice Templates',
        'templates': templates
    })


@login_required
@require_http_methods(["POST"])
def template_create_view(request):
    """Create invoice template from scratch or from existing invoice"""
    from app_core.models import InvoiceTemplate, InvoiceTemplateItem, Invoice
    from app_core.invoicing import save_invoice_as_template
    import json

    try:
        data = json.loads(request.body)

        # Check if creating from existing invoice
        invoice_id = data.get('invoice_id')
        if invoice_id:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
            template = save_invoice_as_template(
                invoice=invoice,
                template_name=data['name'],
                description=data.get('description', '')
            )
        else:
            # Create template from scratch
            template = InvoiceTemplate.objects.create(
                user=request.user,
                name=data['name'],
                description=data.get('description', ''),
                default_tax_rate=Decimal(str(data.get('tax_rate', 0))),
                default_payment_terms=data.get('payment_terms', 'Net 30'),
                default_notes=data.get('notes', ''),
                default_terms=data.get('terms', ''),
            )

            # Add items
            for item_data in data.get('items', []):
                InvoiceTemplateItem.objects.create(
                    template=template,
                    description=item_data['description'],
                    quantity=Decimal(str(item_data.get('quantity', 1))),
                    unit_price=Decimal(str(item_data['unit_price'])),
                    order=item_data.get('order', 0),
                )

        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'message': f'Template "{template.name}" created successfully'
        })

    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def template_edit_view(request, template_id):
    """Edit an invoice template"""
    from app_core.models import InvoiceTemplate, InvoiceTemplateItem
    import json

    try:
        template = InvoiceTemplate.objects.get(id=template_id, user=request.user)
        data = json.loads(request.body)

        # Update template
        template.name = data.get('name', template.name)
        template.description = data.get('description', template.description)
        template.default_tax_rate = Decimal(str(data.get('tax_rate', template.default_tax_rate)))
        template.default_payment_terms = data.get('payment_terms', template.default_payment_terms)
        template.default_notes = data.get('notes', template.default_notes)
        template.default_terms = data.get('terms', template.default_terms)
        template.save()

        # Update items if provided
        if 'items' in data:
            template.items.all().delete()
            for item_data in data['items']:
                InvoiceTemplateItem.objects.create(
                    template=template,
                    description=item_data['description'],
                    quantity=Decimal(str(item_data.get('quantity', 1))),
                    unit_price=Decimal(str(item_data['unit_price'])),
                    order=item_data.get('order', 0),
                )

        return JsonResponse({'success': True, 'message': 'Template updated successfully'})

    except InvoiceTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Template not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def template_delete_view(request, template_id):
    """Delete an invoice template"""
    from app_core.models import InvoiceTemplate

    try:
        template = InvoiceTemplate.objects.get(id=template_id, user=request.user)
        template_name = template.name
        template.delete()

        return JsonResponse({
            'success': True,
            'message': f'Template "{template_name}" deleted successfully'
        })

    except InvoiceTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Template not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def template_use_view(request, template_id):
    """Create a new invoice from a template"""
    from app_core.models import InvoiceTemplate, Client
    from app_core.invoicing import create_invoice_from_template
    from datetime import date, timedelta
    import json

    try:
        template = InvoiceTemplate.objects.get(id=template_id, user=request.user)
        data = json.loads(request.body)

        client = Client.objects.get(id=data['client_id'], user=request.user)

        invoice_date = date.fromisoformat(data.get('invoice_date', date.today().isoformat()))
        due_date = date.fromisoformat(data.get('due_date', (date.today() + timedelta(days=30)).isoformat()))

        invoice = create_invoice_from_template(
            template=template,
            client=client,
            user=request.user,
            invoice_date=invoice_date,
            due_date=due_date
        )

        return JsonResponse({
            'success': True,
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'message': 'Invoice created from template successfully'
        })

    except (InvoiceTemplate.DoesNotExist, Client.DoesNotExist) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def template_detail_view(request, template_id):
    """Get template details including all items"""
    from app_core.models import InvoiceTemplate

    try:
        template = InvoiceTemplate.objects.get(id=template_id, user=request.user)

        items = []
        for item in template.items.all():
            items.append({
                'id': item.id,
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'amount': float(item.quantity * item.unit_price),
                'order': item.order,
            })

        data = {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'default_tax_rate': float(template.default_tax_rate),
            'default_payment_terms': template.default_payment_terms,
            'default_notes': template.default_notes,
            'default_terms': template.default_terms,
            'items': items,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat(),
        }

        return JsonResponse(data)

    except InvoiceTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ==================== REPORTS VIEWS ====================

@login_required
def reports_view(request):
    """Reports overview page"""
    from django.shortcuts import render

    # Minimal overview page that lists available reports and quick links
    reports = [
        {'key': 'pnl', 'name': 'Profit & Loss (P&L)', 'url': '/reports/pnl/'},
        {'key': 'cashflow', 'name': 'Cash Flow Statement', 'url': '#'},
        {'key': 'expenses', 'name': 'Expense Report by Category', 'url': '#'},
        {'key': 'income', 'name': 'Income Report by Source', 'url': '#'},
        {'key': 'tax', 'name': 'Tax Summary Report', 'url': '#'},
        {'key': 'budget_perf', 'name': 'Budget Performance Report', 'url': '#'},
        {'key': 'project_perf', 'name': 'Project Performance Report', 'url': '#'},
        {'key': 'vendor', 'name': 'Vendor Spending Report', 'url': '#'},
    ]

    context = {
        'reports': reports,
        'title': 'Reports & Analytics'
    }

    return render(request, 'app_web/reports.html', context)


@login_required
def report_pnl_view(request):
    """Profit & Loss (P&L) report - aggregates transactions by labels and direction"""
    from django.shortcuts import render
    from app_core.models import Transaction, Label
    from django.db.models import Sum
    from datetime import datetime, date, timedelta

    # Parse date range filters
    start = request.GET.get('start')
    end = request.GET.get('end')

    try:
        start_date = datetime.fromisoformat(start).date() if start else None
    except Exception:
        start_date = None

    try:
        end_date = datetime.fromisoformat(end).date() if end else None
    except Exception:
        end_date = None

    today = date.today()
    # Normalize single-side inputs: if only one provided, treat as single-day range
    if start_date and not end_date:
        end_date = start_date
    if end_date and not start_date:
        start_date = end_date

    # Default range: last 12 months (month-aligned) if nothing provided
    if not start_date and not end_date:
        # last 12 months: start = first day of month 11 months ago; end = today
        m = today.month
        y = today.year
        m_back = m - 11
        y_back = y
        if m_back <= 0:
            m_back += 12
            y_back -= 1
        start_date = date(y_back, m_back, 1)
        end_date = today

    # Compute previous same-length window (month/year-aware)
    import calendar as _cal
    try:
        period_len = (end_date - start_date).days + 1
    except Exception:
        period_len = 1
    last_day_of_month = _cal.monthrange(start_date.year, start_date.month)[1]
    is_full_year = (start_date.month == 1 and start_date.day == 1 and end_date.month == 12 and end_date.day == 31 and start_date.year == end_date.year)
    is_full_month = (start_date.day == 1 and end_date.day == last_day_of_month and start_date.month == end_date.month and start_date.year == end_date.year)

    if is_full_year:
        prev_start = date(start_date.year - 1, 1, 1)
        prev_end = date(start_date.year - 1, 12, 31)
    elif is_full_month:
        prev_month = start_date.month - 1
        prev_year = start_date.year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1
        prev_start = date(prev_year, prev_month, 1)
        prev_end = date(prev_year, prev_month, _cal.monthrange(prev_year, prev_month)[1])
    else:
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_len - 1)

    # Human-friendly labels for the two columns
    def _friendly(d):
        try:
            return d.strftime('%b %d, %Y')
        except Exception:
            return ''

    # Compact label helper: if range is whole year -> '2025', if whole month -> 'Dec 25', else full range
    def _compact_label(start_d, end_d):
        try:
            # whole single year
            if start_d.month == 1 and start_d.day == 1 and end_d.month == 12 and end_d.day == 31 and start_d.year == end_d.year:
                return f"{start_d.year}"
            # whole single month
            import calendar as _cal
            last = _cal.monthrange(start_d.year, start_d.month)[1]
            if start_d.day == 1 and end_d.day == last and start_d.month == end_d.month and start_d.year == end_d.year:
                return start_d.strftime('%b %y')
        except Exception:
            pass
        return f"{_friendly(start_d)} – {_friendly(end_d)}"

    curr_label = _compact_label(start_date, end_date)
    prev_label = _compact_label(prev_start, prev_end)

    # Querysets for current and previous windows
    qs_cur = Transaction.objects.filter(user=request.user, date__gte=start_date, date__lte=end_date)
    qs_prev = Transaction.objects.filter(user=request.user, date__gte=prev_start, date__lte=prev_end)

    # Totals (inflow/outflow) for each window
    income_total = qs_cur.filter(direction=Transaction.INFLOW).aggregate(total=Sum('amount'))['total'] or 0
    expense_total = qs_cur.filter(direction=Transaction.OUTFLOW).aggregate(total=Sum('amount'))['total'] or 0

    income_total_prev = qs_prev.filter(direction=Transaction.INFLOW).aggregate(total=Sum('amount')).get('total') or 0
    expense_total_prev = qs_prev.filter(direction=Transaction.OUTFLOW).aggregate(total=Sum('amount')).get('total') or 0

    # Build revenue and expense rows separately (use inflows for revenue, outflows for expenses)
    labels = Label.objects.filter(user=request.user).order_by('name')
    revenue_rows = []
    expense_rows = []

    def _pct_change(cur, prev):
        try:
            if prev == 0:
                return None
            return (float(cur) - float(prev)) / abs(float(prev)) * 100.0
        except Exception:
            return None

    for lbl in labels:
        cur_in = qs_cur.filter(label=lbl, direction=Transaction.INFLOW).aggregate(total=Sum('amount'))['total'] or 0
        prev_in = qs_prev.filter(label=lbl, direction=Transaction.INFLOW).aggregate(total=Sum('amount')).get('total') or 0
        if cur_in or prev_in:
            change_amt = (cur_in or 0) - (prev_in or 0)
            change_pct = _pct_change(cur_in or 0, prev_in or 0)
            revenue_rows.append({
                'label': lbl.name,
                'cur': cur_in,
                'prev': prev_in,
                'change': change_amt,
                'pct': change_pct,
            })

        cur_out = qs_cur.filter(label=lbl, direction=Transaction.OUTFLOW).aggregate(total=Sum('amount'))['total'] or 0
        prev_out = qs_prev.filter(label=lbl, direction=Transaction.OUTFLOW).aggregate(total=Sum('amount')).get('total') or 0
        if cur_out or prev_out:
            change_amt = (cur_out or 0) - (prev_out or 0)
            change_pct = _pct_change(cur_out or 0, prev_out or 0)
            expense_rows.append({
                'label': lbl.name,
                'cur': cur_out,
                'prev': prev_out,
                'change': change_amt,
                'pct': change_pct,
            })

    # Uncategorized as revenue/expense if present
    unc_cur_in = qs_cur.filter(label__isnull=True, direction=Transaction.INFLOW).aggregate(total=Sum('amount'))['total'] or 0
    unc_prev_in = qs_prev.filter(label__isnull=True, direction=Transaction.INFLOW).aggregate(total=Sum('amount')).get('total') or 0
    if unc_cur_in or unc_prev_in:
        revenue_rows.append({
            'label': 'Uncategorized', 'cur': unc_cur_in, 'prev': unc_prev_in, 'change': (unc_cur_in or 0) - (unc_prev_in or 0), 'pct': _pct_change(unc_cur_in or 0, unc_prev_in or 0)
        })
    unc_cur_out = qs_cur.filter(label__isnull=True, direction=Transaction.OUTFLOW).aggregate(total=Sum('amount'))['total'] or 0
    unc_prev_out = qs_prev.filter(label__isnull=True, direction=Transaction.OUTFLOW).aggregate(total=Sum('amount')).get('total') or 0
    if unc_cur_out or unc_prev_out:
        expense_rows.append({
            'label': 'Uncategorized', 'cur': unc_cur_out, 'prev': unc_prev_out, 'change': (unc_cur_out or 0) - (unc_prev_out or 0), 'pct': _pct_change(unc_cur_out or 0, unc_prev_out or 0)
        })

    # Totals and net change
    total_revenue_cur = sum(r['cur'] for r in revenue_rows)
    total_revenue_prev = sum(r['prev'] for r in revenue_rows)
    total_expense_cur = sum(e['cur'] for e in expense_rows)
    total_expense_prev = sum(e['prev'] for e in expense_rows)

    income_before_tax = (total_revenue_cur or 0) - (total_expense_cur or 0)
    income_before_tax_prev = (total_revenue_prev or 0) - (total_expense_prev or 0)
    net_change = (income_before_tax or 0) - (income_before_tax_prev or 0)

    # For now, tax amount placeholder = 0 (we can wire tax rules later)
    tax_amount = 0.0

    # Net profit values (compute here so template doesn't do arithmetic)
    net_profit = (income_before_tax or 0) - (tax_amount or 0)
    net_profit_prev = (income_before_tax_prev or 0) - 0

    # totals change and percent
    total_revenue_change = (total_revenue_cur or 0) - (total_revenue_prev or 0)
    total_revenue_pct = _pct_change(total_revenue_cur or 0, total_revenue_prev or 0)
    total_expense_change = (total_expense_cur or 0) - (total_expense_prev or 0)
    total_expense_pct = _pct_change(total_expense_cur or 0, total_expense_prev or 0)

    context = {
        'title': 'Profit & Loss (P&L)',
        'revenue_rows': revenue_rows,
        'expense_rows': expense_rows,
        'total_revenue_cur': total_revenue_cur,
        'total_revenue_prev': total_revenue_prev,
        'total_revenue_change': total_revenue_change,
        'total_revenue_pct': total_revenue_pct,
        'total_expense_cur': total_expense_cur,
        'total_expense_prev': total_expense_prev,
        'total_expense_change': total_expense_change,
        'total_expense_pct': total_expense_pct,
        'income_before_tax': income_before_tax,
        'income_before_tax_prev': income_before_tax_prev,
        'net_profit': net_profit,
        'net_profit_prev': net_profit_prev,
        'tax_amount': tax_amount,
        'net_change': net_change,
        'start_date': start_date,
        'end_date': end_date,
        'curr_label': curr_label,
        'prev_label': prev_label,
    }

    return render(request, 'app_web/report_pnl.html', context)


@login_required
def report_pnl_download(request):
    """Generate a downloadable P&L PDF for the given date range (A4) matching the on-screen layout."""
    from app_core.models import Transaction, Label
    from django.db.models import Sum
    from datetime import datetime, date, timedelta
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT

    # Parse dates robustly (accept ISO and common human formats like 'Jan 1, 2025' or 'Jan. 1, 2025')
    def _parse_date(s):
        if not s:
            return None
        # Already a date object
        if isinstance(s, datetime):
            return s.date()
        if isinstance(s, date):
            return s
        s = str(s).strip()
        # Try ISO first
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            pass
        # Try common formats
        common = ['%b %d, %Y', '%b. %d, %Y', '%B %d, %Y', '%d %b %Y', '%Y-%m-%d']
        for fmt in common:
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                continue
        # As a last resort, try parsing numbers (e.g. '1 Jan 2025')
        try:
            return datetime.strptime(s, '%d %B %Y').date()
        except Exception:
            return None

    start = request.GET.get('start')
    end = request.GET.get('end')
    start_date = _parse_date(start)
    end_date = _parse_date(end)

    # today's date used for header and default ranges
    today = date.today()

    # Normalize single-side inputs: if only one side provided, treat as single-day range
    if start_date and not end_date:
        end_date = start_date
    if end_date and not start_date:
        start_date = end_date

    # Default range: last 12 months (month-aligned) if nothing provided
    if not start_date and not end_date:
        m = today.month
        y = today.year
        m_back = m - 11
        y_back = y
        if m_back <= 0:
            m_back += 12
            y_back -= 1
        start_date = date(y_back, m_back, 1)
        end_date = today

    # Compute previous same-length window (month/year-aware)
    import calendar as _cal
    try:
        period_len = (end_date - start_date).days + 1
    except Exception:
        period_len = 1
    last_day_of_month = _cal.monthrange(start_date.year, start_date.month)[1]
    is_full_year = (start_date.month == 1 and start_date.day == 1 and end_date.month == 12 and end_date.day == 31 and start_date.year == end_date.year)
    is_full_month = (start_date.day == 1 and end_date.day == last_day_of_month and start_date.month == end_date.month and start_date.year == end_date.year)

    if is_full_year:
        prev_start = date(start_date.year - 1, 1, 1)
        prev_end = date(start_date.year - 1, 12, 31)
    elif is_full_month:
        prev_month = start_date.month - 1
        prev_year = start_date.year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1
        prev_start = date(prev_year, prev_month, 1)
        prev_end = date(prev_year, prev_month, _cal.monthrange(prev_year, prev_month)[1])
    else:
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_len - 1)

    # Query data
    qs = Transaction.objects.filter(user=request.user, date__gte=start_date, date__lte=end_date)
    qs_prev = Transaction.objects.filter(user=request.user, date__gte=prev_start, date__lte=prev_end)

    labels = Label.objects.filter(user=request.user).order_by('name')

    revenue_rows = []
    expense_rows = []
    def _pct_change(cur, prev):
        try:
            if prev == 0:
                return None
            return (float(cur) - float(prev)) / abs(float(prev)) * 100.0
        except Exception:
            return None

    for lbl in labels:
        cur_in = qs.filter(label=lbl, direction=Transaction.INFLOW).aggregate(total=Sum('amount'))['total'] or 0
        prev_in = qs_prev.filter(label=lbl, direction=Transaction.INFLOW).aggregate(total=Sum('amount')).get('total') or 0
        if cur_in or prev_in:
            change_amt = (cur_in or 0) - (prev_in or 0)
            change_pct = _pct_change(cur_in or 0, prev_in or 0)
            revenue_rows.append((lbl.name, float(cur_in), float(prev_in), float((cur_in or 0) - (prev_in or 0)), change_pct))

        cur_out = qs.filter(label=lbl, direction=Transaction.OUTFLOW).aggregate(total=Sum('amount'))['total'] or 0
        prev_out = qs_prev.filter(label=lbl, direction=Transaction.OUTFLOW).aggregate(total=Sum('amount')).get('total') or 0
        if cur_out or prev_out:
            change_amt = (cur_out or 0) - (prev_out or 0)
            change_pct = _pct_change(cur_out or 0, prev_out or 0)
            expense_rows.append((lbl.name, float(cur_out), float(prev_out), float((cur_out or 0) - (prev_out or 0)), change_pct))

    # Uncategorized
    unc_cur_in = qs.filter(label__isnull=True, direction=Transaction.INFLOW).aggregate(total=Sum('amount'))['total'] or 0
    unc_prev_in = qs_prev.filter(label__isnull=True, direction=Transaction.INFLOW).aggregate(total=Sum('amount')).get('total') or 0
    if unc_cur_in or unc_prev_in:
        revenue_rows.append(('Uncategorized', float(unc_cur_in), float(unc_prev_in), float((unc_cur_in or 0) - (unc_prev_in or 0)), _pct_change(unc_cur_in or 0, unc_prev_in or 0)))
    unc_cur_out = qs.filter(label__isnull=True, direction=Transaction.OUTFLOW).aggregate(total=Sum('amount'))['total'] or 0
    unc_prev_out = qs_prev.filter(label__isnull=True, direction=Transaction.OUTFLOW).aggregate(total=Sum('amount')).get('total') or 0
    if unc_cur_out or unc_prev_out:
        expense_rows.append(('Uncategorized', float(unc_cur_out), float(unc_prev_out), float((unc_cur_out or 0) - (unc_prev_out or 0)), _pct_change(unc_cur_out or 0, unc_prev_out or 0)))

    total_revenue_cur = sum(r[1] for r in revenue_rows)
    total_revenue_prev = sum(r[2] for r in revenue_rows)
    total_expense_cur = sum(e[1] for e in expense_rows)
    total_expense_prev = sum(e[2] for e in expense_rows)

    income_before_tax = (total_revenue_cur or 0) - (total_expense_cur or 0)
    income_before_tax_prev = (total_revenue_prev or 0) - (total_expense_prev or 0)
    net_change = (income_before_tax or 0) - (income_before_tax_prev or 0)
    tax_amount = 0.0
    net_profit = (income_before_tax or 0) - (tax_amount or 0)
    net_profit_prev = (income_before_tax_prev or 0) - 0

    # Build PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    header_style = ParagraphStyle('header', parent=styles['Heading2'], fontSize=14, alignment=TA_LEFT, spaceAfter=6)
    title_style = ParagraphStyle('title', parent=styles['Heading1'], fontSize=18, alignment=TA_LEFT, spaceAfter=12)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#6b7280'))

    elements = []

    # Company header (left) and creation date (right)
    company_name = getattr(request.user, 'company', None) or (request.user.get_full_name() or request.user.username)
    created_str = today.strftime('%B %d, %Y')
    elements.append(Paragraph(company_name, header_style))
    elements.append(Paragraph(f'Date: {created_str}', small))
    elements.append(Spacer(1, 8))

    # Title
    elements.append(Paragraph('Profit & Loss Statement', title_style))

    # Period info
    period_label = f"{start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}"
    prev_label = f"{prev_start.strftime('%b %d, %Y')} – {prev_end.strftime('%b %d, %Y')}"
    elements.append(Paragraph(f'Period: {period_label}', small))
    elements.append(Paragraph(f'Prior: {prev_label}', small))
    elements.append(Spacer(1, 8))

    # Build table rows: header, revenue section, total revenue, spacer, expenses, total expenses, income/tax/net
    table_data = []
    table_data.append(['Category', 'Current', 'Prior', 'Change'])

    # Revenue rows
    if revenue_rows:
        # Put a revenue title row
        table_data.append(['Revenue', '', '', ''])
        for r in revenue_rows:
            table_data.append([r[0], f'£{r[1]:,.2f}', f'£{r[2]:,.2f}', f'£{r[3]:,.2f}'])

    # Total revenue
    table_data.append(['Total Revenue & Gains', f'£{total_revenue_cur:,.2f}', f'£{total_revenue_prev:,.2f}', f'£{(total_revenue_cur - total_revenue_prev):,.2f}'])
    # spacer
    table_data.append(['', '', '', ''])

    # Expenses
    if expense_rows:
        table_data.append(['Expenses', '', '', ''])
        for e in expense_rows:
            table_data.append([e[0], f'£{e[1]:,.2f}', f'£{e[2]:,.2f}', f'£{e[3]:,.2f}'])

    # Total expenses
    table_data.append(['Total Expenses', f'£{total_expense_cur:,.2f}', f'£{total_expense_prev:,.2f}', f'£{(total_expense_cur - total_expense_prev):,.2f}'])

    # Income before tax
    table_data.append(['Income before tax', f'£{income_before_tax:,.2f}', f'£{income_before_tax_prev:,.2f}', f'£{net_change:,.2f}'])
    # Income tax
    table_data.append(['Income tax expense', f'£{tax_amount:,.2f}', '', ''])
    # Net profit
    table_data.append(['Net Profit (Loss)', f'£{net_profit:,.2f}', f'£{net_profit_prev:,.2f}', f'£{(net_profit - net_profit_prev):,.2f}'])

    # Create Table
    col_widths = [3.6 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Table styling: header, section titles, totals, tax, net
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#111827')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e5e7eb')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])

    # Identify special row indices for styling
    # header row = 0
    row_idx = 1
    # After header, we iterate table_data to find indices of rows that are section titles or totals
    for i, row in enumerate(table_data[1:], start=1):
        label = (row[0] or '').strip()
        if label == 'Revenue':
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ecfdf5'))
            style.add('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#064e3b'))
            style.add('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold')
        elif label == 'Expenses':
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fff1f2'))
            style.add('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#7f1d1d'))
            style.add('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold')
        elif label.startswith('Total Revenue') or label.startswith('Total Expenses') or label == 'Income before tax' or label == 'Income tax expense':
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f3f4f6'))
            style.add('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold')
        elif label.startswith('Net Profit'):
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fff8dc'))
            style.add('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold')
            style.add('LINEABOVE', (0, i), (-1, i), 1, colors.HexColor('#d6d3a8'))

    t.setStyle(style)
    elements.append(t)

    # Build and return PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="P&L_Report.pdf"'
    return response

