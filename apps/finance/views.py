import csv
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Sum, Q  
from django.core.paginator import Paginator  
from apps.core.utils import render_to_pdf
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages

from .models import JournalItem, Invoice, Payment, Account
from .tasks import send_invoice_email_task

# ==========================================
# INVOICES & PAYMENTS
# ==========================================

@login_required
@permission_required('finance.view_invoice', raise_exception=True)
def invoice_list(request):
    query = request.GET.get('q', '')
    state_filter = request.GET.get('state', '')
    type_filter = request.GET.get('type', '')
    sort_by = request.GET.get('sort', '-date')

    invoices = Invoice.objects.all()

    if query:
        invoices = invoices.filter(
            Q(invoice_id__icontains=query) | 
            Q(partner__name__icontains=query) |
            Q(source_document__icontains=query)
        )

    if state_filter:
        invoices = invoices.filter(state=state_filter)
    if type_filter:
        invoices = invoices.filter(type=type_filter)

    valid_sorts = ['invoice_id', '-invoice_id', 'date', '-date', 'total_amount', '-total_amount', 'state', '-state']
    if sort_by in valid_sorts:
        invoices = invoices.order_by(sort_by)
    else:
        invoices = invoices.order_by('-date', '-invoice_id')

    paginator = Paginator(invoices, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'finance/invoice_list.html', {
        'invoices': page_obj,
        'query': query,
        'state_filter': state_filter,
        'type_filter': type_filter,
        'sort_by': sort_by,
    })

@login_required
@permission_required('finance.view_invoice', raise_exception=True)
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id)
    history_records = invoice.history.all().order_by('-history_date')
    
    if request.method == 'POST':
        if 'post_invoice' in request.POST:
            if not request.user.has_perm('finance.change_invoice'):
                return HttpResponse('Forbidden: Cannot Post Invoices', status=403)
            invoice.post()
            return redirect('invoice_detail', invoice_id=invoice.invoice_id)
            
        elif 'register_payment' in request.POST:
            if not request.user.has_perm('finance.add_payment'):
                return HttpResponse('Forbidden: Cannot Register Payments', status=403)
                
            amount_str = request.POST.get('amount')
            method = request.POST.get('method', 'bank')
            
            if amount_str:
                try:
                    amount = Decimal(amount_str)
                    if amount > 0 and amount <= invoice.amount_due:
                        payment = Payment.objects.create(
                            invoice=invoice,
                            amount=amount,
                            method=method
                        )
                        payment.post()
                except ValueError:
                    pass
            return redirect('invoice_detail', invoice_id=invoice.invoice_id)

        elif 'email_invoice' in request.POST:
            if invoice.partner and invoice.partner.email:
                send_invoice_email_task.delay(invoice.invoice_id, invoice.partner.email)
                messages.success(request, f"Task Queued: Invoice is being generated and emailed to {invoice.partner.email} in the background.")
            else:
                messages.error(request, "Partner does not have a valid email address set in their profile.")
            return redirect('invoice_detail', invoice_id=invoice.invoice_id)

    return render(request, 'finance/invoice_detail.html', {'invoice': invoice, 'history_records': history_records})

@login_required
@permission_required('finance.view_invoice', raise_exception=True)
def invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id)
    return render_to_pdf('finance/invoice_pdf.html', {'invoice': invoice})

# ==========================================
# GENERAL LEDGER & EXPORTS
# ==========================================

@login_required
@permission_required('finance.view_journalitem', raise_exception=True)
def general_ledger(request):
    items = JournalItem.objects.select_related('entry', 'account').order_by('-entry__date', '-id')

    totals = items.aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))
    total_debit = totals['total_debit'] or 0
    total_credit = totals['total_credit'] or 0
    balance = total_debit - total_credit


    paginator = Paginator(items, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'finance/general_ledger.html', {
        'items': page_obj,  
        'total_debit': total_debit,
        'total_credit': total_credit,
        'balance': balance
    })

@login_required
@permission_required('finance.view_journalitem', raise_exception=True)
def general_ledger_export(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="general_ledger.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Reference', 'Account', 'Debit', 'Credit'])

    items = JournalItem.objects.select_related('entry', 'account').order_by('-entry__date', '-id')
    
    for item in items:
        writer.writerow([item.entry.date, item.entry.reference, item.account.name, item.debit, item.credit])
    
    return response

@login_required
@permission_required('finance.view_journalitem', raise_exception=True)
def general_ledger_pdf(request):
    items = JournalItem.objects.select_related('entry', 'account').order_by('-entry__date', '-id')
    totals = items.aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))
    
    context = {
        'items': items,
        'total_debit': totals['total_debit'] or 0,
        'total_credit': totals['total_credit'] or 0
    }
    return render_to_pdf('finance/general_ledger_pdf.html', context)


# ==========================================
# FINANCIAL REPORTS (P&L AND BALANCE SHEET)
# ==========================================

@login_required
@permission_required('finance.view_account', raise_exception=True)
def financial_reports(request):
    """ Calculates the Income Statement and the Balance Sheet with Date Filtering. """
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    def get_account_balances(acc_type, normal_balance='debit', is_balance_sheet=False):
        accounts = Account.objects.filter(type=acc_type)
        balances = []
        total = Decimal('0.00')
        
        for acc in accounts:
            items = JournalItem.objects.filter(account=acc)
            

            if not is_balance_sheet and start_date:
                items = items.filter(entry__date__gte=start_date)
            if end_date:
                items = items.filter(entry__date__lte=end_date)
                
            dr = items.aggregate(t=Sum('debit'))['t'] or Decimal('0.00')
            cr = items.aggregate(t=Sum('credit'))['t'] or Decimal('0.00')
            
            bal = (dr - cr) if normal_balance == 'debit' else (cr - dr)
            if bal != 0:
                balances.append({'code': acc.code, 'name': acc.name, 'balance': bal})
                total += bal
                
        return balances, total


    income_accounts, total_income = get_account_balances('income', 'credit', is_balance_sheet=False)
    expense_accounts, total_expense = get_account_balances('expense', 'debit', is_balance_sheet=False)
    net_profit = total_income - total_expense


    asset_accounts, total_assets = get_account_balances('asset', 'debit', is_balance_sheet=True)
    liability_accounts, total_liabilities = get_account_balances('liability', 'credit', is_balance_sheet=True)
    equity_accounts, total_equity_base = get_account_balances('equity', 'credit', is_balance_sheet=True)

    total_equity_and_liabilities = total_liabilities + total_equity_base + net_profit

    context = {
        'income_accounts': income_accounts,
        'total_income': total_income,
        'expense_accounts': expense_accounts,
        'total_expense': total_expense,
        'net_profit': net_profit,
        
        'asset_accounts': asset_accounts,
        'total_assets': total_assets,
        'liability_accounts': liability_accounts,
        'total_liabilities': total_liabilities,
        'equity_accounts': equity_accounts,
        'total_equity_base': total_equity_base,
        'total_equity_and_liabilities': total_equity_and_liabilities,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'finance/financial_reports.html', context)