from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from staffing.access import PERM_MANAGE_WEDDING, PERM_PLANNER, get_wedding_for_user

from .forms import BudgetDocumentForm, VendorDocumentForm
from .models import FinancialAuditEvent, FinancialDocument
from .services import is_planner_only, log_financial_event, visible_documents


def _finance_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    if wedding is None:
        wedding = get_wedding_for_user(request.user, PERM_PLANNER)
    if wedding is None:
        raise Http404("Financial documents are not available for your role.")
    return wedding


def _forms(wedding, user, *, data=None, files=None, active=None):
    budget_form = BudgetDocumentForm(prefix="budget", wedding=wedding, user=user)
    vendor_form = VendorDocumentForm(prefix="vendor", wedding=wedding, user=user)
    if active == "budget":
        budget_form = BudgetDocumentForm(data, files, prefix="budget", wedding=wedding, user=user)
    elif active == "vendor":
        vendor_form = VendorDocumentForm(data, files, prefix="vendor", wedding=wedding, user=user)
    return budget_form, vendor_form


@login_required
def dashboard(request):
    wedding = _finance_wedding(request)
    planner_view = is_planner_only(request.user, wedding)
    active = None

    if request.method == "POST":
        form_type = request.POST.get("form_type", "").strip()
        if form_type not in {"budget", "vendor"}:
            return HttpResponseBadRequest("Unknown document form")
        active = form_type
        budget_form, vendor_form = _forms(
            wedding,
            request.user,
            data=request.POST,
            files=request.FILES,
            active=active,
        )
        form = budget_form if active == "budget" else vendor_form
        if form.is_valid():
            document = form.save()
            log_financial_event(
                wedding=wedding,
                actor=request.user,
                action="FINANCIAL_DOCUMENT_UPLOADED",
                entity_type="FINANCIAL_DOCUMENT",
                entity_id=document.pk,
                message=f"Uploaded {document.get_document_type_display()}: {document.title}.",
            )
            messages.success(request, f"Financial document '{document.title}' uploaded.")
            return redirect("financial_docs:dashboard")
    else:
        budget_form, vendor_form = _forms(wedding, request.user)

    documents = visible_documents(request.user, wedding)
    counts = {
        "total": documents.count(),
        "receipts": documents.filter(document_type=FinancialDocument.DocumentType.RECEIPT).count(),
        "contracts": documents.filter(document_type=FinancialDocument.DocumentType.CONTRACT).count(),
        "payment_proofs": documents.filter(document_type=FinancialDocument.DocumentType.PAYMENT_PROOF).count(),
    }
    audit_events = FinancialAuditEvent.objects.none()
    if not planner_view:
        audit_events = FinancialAuditEvent.objects.filter(wedding=wedding).select_related("actor")[:30]

    return render(
        request,
        "financial_docs/dashboard.html",
        {
            "wedding": wedding,
            "budget_form": budget_form,
            "vendor_form": vendor_form,
            "active_form": active,
            "documents": documents,
            "counts": counts,
            "planner_view": planner_view,
            "audit_events": audit_events,
        },
    )


@login_required
def download(request, document_id):
    wedding = _finance_wedding(request)
    document = get_object_or_404(visible_documents(request.user, wedding), pk=document_id)
    if not document.file:
        raise Http404("Document file not found")
    try:
        handle = document.file.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("Document file not found")
    response = FileResponse(handle, as_attachment=True, filename=document.original_name or document.file.name.rsplit("/", 1)[-1])
    return response


@login_required
@require_POST
def delete(request, document_id):
    wedding = _finance_wedding(request)
    document = get_object_or_404(visible_documents(request.user, wedding), pk=document_id)
    planner_view = is_planner_only(request.user, wedding)
    if planner_view and document.created_by_id != request.user.id:
        return HttpResponseBadRequest("Planner can delete only documents they uploaded.")

    title = document.title
    document_pk = document.pk
    stored_file = document.file
    document.delete()
    if stored_file:
        try:
            stored_file.delete(save=False)
        except OSError:
            pass
    log_financial_event(
        wedding=wedding,
        actor=request.user,
        action="FINANCIAL_DOCUMENT_DELETED",
        entity_type="FINANCIAL_DOCUMENT",
        entity_id=document_pk,
        message=f"Deleted financial document: {title}.",
    )
    messages.success(request, f"Financial document '{title}' deleted.")
    return redirect("financial_docs:dashboard")
