from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q, F
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator  
from django.contrib import messages

from apps.core.models import Material, ProductCategory  


from .models import (
    StockMove, InventoryAdjustment, InventoryAdjustmentLine, 
    StockQuant, StorageLocation, StockPicking
)


from .forms import (
    MaterialForm, InventoryAdjustmentForm, AdjustmentLineForm, 
    StorageLocationForm
)


import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from apps.core.utils import render_to_pdf

# ==========================
#  PRODUCT VIEWS
# ==========================

@login_required
@permission_required('core.view_material', raise_exception=True)
def product_list(request):

    query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'name') 


    products_qs = Material.objects.annotate(
        total_qty=Sum(
            'stockquant__quantity_on_hand', 
            filter=Q(stockquant__location__type='internal')
        )
    )


    if query:
        products_qs = products_qs.filter(
            Q(name__icontains=query) | 
            Q(sku__icontains=query)
        )


    if category_filter:
        products_qs = products_qs.filter(category_id=category_filter)


    valid_sorts = [
        'name', '-name', 'sku', '-sku', 'category__name', '-category__name', 
        'cost_price', '-cost_price', 'sales_price', '-sales_price', 'total_qty', '-total_qty'
    ]
    if sort_by in valid_sorts:
        products_qs = products_qs.order_by(sort_by)
    else:
        products_qs = products_qs.order_by('name')


    paginator = Paginator(products_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    

    categories = ProductCategory.objects.all().order_by('name')

    return render(request, 'inventory/product_list.html', {
        'products': page_obj,
        'query': query,
        'category_filter': category_filter,
        'sort_by': sort_by,
        'categories': categories
    })

@login_required
@permission_required('core.view_material', raise_exception=True)
def product_detail(request, sku):
    product = get_object_or_404(Material, sku=sku)
    

    product.update_analytics()
    

    quants = StockQuant.objects.filter(material=product, location__type='internal')
    
    totals = quants.aggregate(
        total_hand=Sum('quantity_on_hand'), 
        total_reserved=Sum('quantity_reserved')
    )
    
    on_hand = totals['total_hand'] or 0
    reserved = totals['total_reserved'] or 0
    available = on_hand - reserved

    context = {
        'product': product,
        'quants': quants,
        'on_hand': on_hand,
        'reserved': reserved,
        'available': available
    }
    return render(request, 'inventory/product_detail.html', context)

@login_required
@permission_required('core.add_material', raise_exception=True)
def product_create(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventory_list')
    else:
        form = MaterialForm()
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Create New Product'})

@login_required
@permission_required('core.change_material', raise_exception=True)
def product_edit(request, sku):
    product = get_object_or_404(Material, sku=sku)
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_detail', sku=product.sku)
    else:
        form = MaterialForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form, 'title': f'Edit {product.sku}'})

@login_required
@permission_required('core.view_material', raise_exception=True)
def product_label_pdf(request, sku):
    product = get_object_or_404(Material, sku=sku)
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(product.sku, writer=ImageWriter())
    buffer = BytesIO()
    ean.write(buffer)
    barcode_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    context = {'product': product, 'barcode_image': barcode_image}
    return render_to_pdf('inventory/product_label_pdf.html', context)

# ==========================
#  STOCK MOVES & AUDIT
# ==========================

@login_required
@permission_required('inventory.view_stockmove', raise_exception=True)
def stock_moves(request):
    moves = StockMove.objects.all().order_by('-date')
    return render(request, 'inventory/stock_moves.html', {'moves': moves})

@login_required
@permission_required('inventory.view_inventoryadjustment', raise_exception=True)
def adjustment_list(request):
    adjustments = InventoryAdjustment.objects.all().order_by('-date')
    return render(request, 'inventory/adjustment_list.html', {'adjustments': adjustments})

@login_required
@permission_required('inventory.add_inventoryadjustment', raise_exception=True)
def adjustment_create(request):
    if request.method == 'POST':
        form = InventoryAdjustmentForm(request.POST)
        if form.is_valid():
            adj = form.save()
            return redirect('adjustment_detail', ref=adj.ref)
    else:
        form = InventoryAdjustmentForm()
    return render(request, 'inventory/adjustment_form.html', {'form': form})

@login_required
@permission_required('inventory.view_inventoryadjustment', raise_exception=True)
def adjustment_detail(request, ref):
    adj = get_object_or_404(InventoryAdjustment, ref=ref)
    
    if request.method == 'POST':
        if not request.user.has_perm('inventory.change_inventoryadjustment'):
            messages.error(request, "Permission Denied: You cannot modify Inventory Adjustments.")
            return redirect('adjustment_detail', ref=ref)

        if 'validate' in request.POST or 'confirm_adjustment' in request.POST:
            adj.apply_adjustment()
            return redirect('adjustment_detail', ref=adj.ref)
        
        line_form = AdjustmentLineForm(request.POST)
        if line_form.is_valid():
            line = line_form.save(commit=False)
            line.adjustment = adj
            line.save()
            return redirect('adjustment_detail', ref=adj.ref)
    else:
        line_form = AdjustmentLineForm()

    return render(request, 'inventory/adjustment_detail.html', {
        'adjustment': adj, 
        'line_form': line_form
    })

# ==========================
#  WAREHOUSE MANAGEMENT
# ==========================

@login_required
@permission_required('inventory.view_storagelocation', raise_exception=True)
def location_list(request):
    locations = StorageLocation.objects.filter(type='internal')
    for loc in locations:
        qty_data = StockQuant.objects.filter(location=loc).aggregate(total=Sum('quantity_on_hand'))
        loc.total_qty = qty_data['total'] or 0
        quants = StockQuant.objects.filter(location=loc).select_related('material')
        loc.total_value = sum(q.quantity_on_hand * q.material.cost_price for q in quants)

    return render(request, 'inventory/location_list.html', {'locations': locations})

@login_required
@permission_required('inventory.add_storagelocation', raise_exception=True)
def location_create(request):
    if request.method == 'POST':
        form = StorageLocationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('location_list')
    else:
        form = StorageLocationForm()
    return render(request, 'inventory/location_form.html', {'form': form, 'title': 'Add New Warehouse'})

@login_required
@permission_required('inventory.view_storagelocation', raise_exception=True)
def location_detail(request, location_id):
    location = get_object_or_404(StorageLocation, location_id=location_id)
    quants = StockQuant.objects.filter(location=location).exclude(quantity_on_hand=0).select_related('material')
    
    return render(request, 'inventory/location_detail.html', {
        'location': location,
        'quants': quants
    })

# ==========================
#  OPERATIONS (PICKING)
# ==========================

@login_required
@permission_required('inventory.view_stockpicking', raise_exception=True)
def picking_list(request):
    pickings = StockPicking.objects.filter(state__in=['assigned', 'draft']).order_by('-picking_id')
    return render(request, 'inventory/picking_list.html', {'pickings': pickings})

@login_required
@permission_required('inventory.change_stockpicking', raise_exception=True)
def picking_validate(request, picking_id):
    picking = get_object_or_404(StockPicking, picking_id=picking_id)
    picking.validate_picking()
    return redirect('picking_list')