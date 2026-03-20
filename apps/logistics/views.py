from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.core.utils import render_to_pdf
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q


from .models import PurchaseOrder, PurchaseOrderLine, SalesOrder, SalesOrderLine
from .forms import PurchaseOrderForm, PurchaseOrderLineForm, SalesOrderForm, SalesOrderLineForm


from apps.finance.models import Invoice


from .tasks import send_order_email_task

# ==========================================
# PURCHASE ORDERS (PROCUREMENT)
# ==========================================

@login_required
@permission_required('logistics.view_purchaseorder', raise_exception=True)
def po_list(request):
    query = request.GET.get('q', '')
    state_filter = request.GET.get('state', '')
    sort_by = request.GET.get('sort', '-date_order')

    orders = PurchaseOrder.objects.all()

    if query:
        orders = orders.filter(
            Q(po_id__icontains=query) | 
            Q(supplier__name__icontains=query)
        )

    if state_filter:
        orders = orders.filter(state=state_filter)

    valid_sorts = ['po_id', '-po_id', 'date_order', '-date_order', 'state', '-state']
    if sort_by in valid_sorts:
        orders = orders.order_by(sort_by)
    else:
        orders = orders.order_by('-date_order')

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'logistics/po_list.html', {
        'orders': page_obj,
        'query': query,
        'state_filter': state_filter,
        'sort_by': sort_by,
    })

@login_required
@permission_required('logistics.add_purchaseorder', raise_exception=True)
def po_create(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            po = form.save()
            return redirect('po_list') 
    else:
        form = PurchaseOrderForm()
    return render(request, 'logistics/po_form.html', {'form': form})

@login_required
@permission_required('logistics.view_purchaseorder', raise_exception=True)
def po_detail(request, po_id):
    po = get_object_or_404(PurchaseOrder, po_id=po_id)

    if request.method == 'POST':
        if not request.user.has_perm('logistics.change_purchaseorder'):
            messages.error(request, "Permission Denied: You cannot modify Purchase Orders.")
            return redirect('po_detail', po_id=po_id)
            
        if 'add_line' in request.POST:
            form = PurchaseOrderLineForm(request.POST)
            if form.is_valid():
                line = form.save(commit=False)
                line.order = po
                line.save()
                return redirect('po_detail', po_id=po_id)
        elif 'confirm_order' in request.POST:
            po.confirm_order()
            messages.success(request, "Purchase Order confirmed. Awaiting delivery.")
            return redirect('po_detail', po_id=po_id)
        elif 'receive_goods' in request.POST:
            po.receive_gap()
            messages.success(request, "Goods successfully received into inventory.")
            return redirect('po_detail', po_id=po_id)
        elif 'create_bill' in request.POST:
            po.create_bill()
            messages.success(request, "Vendor Bill created and posted to Ledger.")
            return redirect('po_detail', po_id=po_id)
            

        elif 'email_order' in request.POST:
            if po.supplier and po.supplier.email:
                send_order_email_task.delay(po.po_id, 'PO', po.supplier.email)
                messages.success(request, f"Task Queued: Order is being generated and emailed to {po.supplier.email} in the background.")
            else:
                messages.error(request, "Supplier does not have a valid email address set in their profile.")
            return redirect('po_detail', po_id=po_id)

    line_form = PurchaseOrderLineForm()
    has_bill = Invoice.objects.filter(source_document=po_id, type='in_invoice').exists()
    history_records = po.history.all().order_by('-history_date')

    return render(request, 'logistics/po_detail.html', {
        'po': po,
        'line_form': line_form,
        'has_bill': has_bill,
        'history_records': history_records
    })

@login_required
@permission_required('logistics.view_purchaseorder', raise_exception=True)
def po_pdf(request, po_id):
    order = get_object_or_404(PurchaseOrder, po_id=po_id)
    context = {'order': order, 'type': 'PURCHASE ORDER'}
    return render_to_pdf('logistics/po_pdf.html', context)

# ==========================================
# SALES ORDERS (LOGISTICS)
# ==========================================

@login_required
@permission_required('logistics.view_salesorder', raise_exception=True)
def so_list(request):
    query = request.GET.get('q', '')
    state_filter = request.GET.get('state', '')
    sort_by = request.GET.get('sort', '-date_order')

    orders = SalesOrder.objects.all()

    if query:
        orders = orders.filter(
            Q(so_id__icontains=query) | 
            Q(customer__name__icontains=query)
        )

    if state_filter:
        orders = orders.filter(state=state_filter)

    valid_sorts = ['so_id', '-so_id', 'date_order', '-date_order', 'state', '-state']
    if sort_by in valid_sorts:
        orders = orders.order_by(sort_by)
    else:
        orders = orders.order_by('-date_order')

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'logistics/so_list.html', {
        'orders': page_obj,
        'query': query,
        'state_filter': state_filter,
        'sort_by': sort_by,
    })


@login_required
@permission_required('logistics.add_salesorder', raise_exception=True)
def so_create(request):
    if request.method == 'POST':
        form = SalesOrderForm(request.POST)
        if form.is_valid():
            so = form.save()
            return redirect('so_detail', so_id=so.so_id)
    else:
        form = SalesOrderForm()
    return render(request, 'logistics/so_form.html', {'form': form})

@login_required
@permission_required('logistics.view_salesorder', raise_exception=True)
def so_detail(request, so_id):
    so = get_object_or_404(SalesOrder, so_id=so_id)

    if request.method == 'POST':
        if not request.user.has_perm('logistics.change_salesorder'):
            messages.error(request, "Permission Denied: You cannot modify Sales Orders.")
            return redirect('so_detail', so_id=so_id)
            
        if 'add_line' in request.POST:
            form = SalesOrderLineForm(request.POST)
            if form.is_valid():
                line = form.save(commit=False)
                line.order = so
                if so.customer.pricelist:
                    line.price_unit = so.customer.pricelist.get_price(line.material)
                else:
                    line.price_unit = line.material.sales_price
                line.save()
                return redirect('so_detail', so_id=so_id)
        elif 'confirm_order' in request.POST:
            try:
                so.confirm_order() 
                messages.success(request, "Sales Order confirmed and stock reserved.")
            except ValueError as e:
                messages.error(request, str(e))
            return redirect('so_detail', so_id=so_id)
        elif 'ship_goods' in request.POST:
            so.ship_gap()
            messages.success(request, "Goods successfully shipped to customer.")
            return redirect('so_detail', so_id=so_id)
        elif 'return_goods' in request.POST:
            so.return_order()
            messages.success(request, "Return Merchandise Authorization (RMA) created.")
            return redirect('so_detail', so_id=so_id)
        elif 'create_invoice' in request.POST:
            so.create_invoice()
            messages.success(request, "Customer Invoice created and posted to Ledger.")
            return redirect('so_detail', so_id=so_id)
            

        elif 'email_order' in request.POST:
            if so.customer and so.customer.email:
                send_order_email_task.delay(so.so_id, 'SO', so.customer.email)
                messages.success(request, f"Task Queued: Order is being generated and emailed to {so.customer.email} in the background.")
            else:
                messages.error(request, "Customer does not have a valid email address set in their profile.")
            return redirect('so_detail', so_id=so_id)

    line_form = SalesOrderLineForm()
    has_invoice = Invoice.objects.filter(source_document=so_id, type='out_invoice').exists()
    history_records = so.history.all().order_by('-history_date')
    
    return render(request, 'logistics/so_detail.html', {
        'so': so, 
        'line_form': line_form,
        'has_invoice': has_invoice,
        'history_records': history_records
    })

@login_required
@permission_required('logistics.view_salesorder', raise_exception=True)
def so_pdf(request, so_id):
    so = get_object_or_404(SalesOrder, so_id=so_id)
    return render_to_pdf('logistics/so_pdf.html', {'so': so})

@login_required
@permission_required('logistics.change_salesorder', raise_exception=True)
def so_line_delete(request, so_id, line_id):
    order = get_object_or_404(SalesOrder, so_id=so_id)
    if request.method == 'POST' and order.state == 'draft':
        line = get_object_or_404(SalesOrderLine, id=line_id, order=order)
        line.delete()
    return redirect('so_detail', so_id=so_id)