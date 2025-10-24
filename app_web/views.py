# app_web/views.py
import base64, io

import pandas as pd
from django.shortcuts import render
from .forms import UploadFileForm
from app_core.ingest import validate_and_preview, _read_any, _coerce_types, dataframe_to_transactions
from django.db import transaction as dbtxn

from django.utils import timezone
from django.db.models import Q
from app_core.models import Transaction
from app_core.metrics import queryset_to_df, kpis as kpi_calc, timeseries, by_category

import math
import json
from django.utils.safestring import mark_safe


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

        rows = dataframe_to_transactions(df, user_id=1)  # TODO: replace with real user later
        with dbtxn.atomic():
            Transaction.objects.bulk_create(rows, batch_size=1000)

        context.update({
            "saved": True,
            "saved_count": len(rows),
            "form": UploadFileForm(),
        })
        return render(request, "app_web/upload.html", context, status=200)

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

def dashboard_view(request):
    """
    Simple dashboard for user_id=1 (MVP). Supports optional ?freq=D|W|M
    """
    user_id = 1  # TODO: replace with real auth later
    freq = request.GET.get("freq", "D").upper()
    if freq not in {"D", "W", "M"}:
        freq = "D"

    # Optional quick date filters (?days=30)
    days = request.GET.get("days")
    q = Q(user_id=user_id)
    if days and str(days).isdigit():
        since = timezone.now().date() - timezone.timedelta(days=int(days))
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
    }
    return render(request, "app_web/dashboard.html", context)