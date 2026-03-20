from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q

from .models import BillOfMaterial, BomComponent, ManufacturingOrder
from .forms import BillOfMaterialForm, BomComponentForm, ManufacturingOrderForm

# ==========================================
# BILL OF MATERIALS VIEWS
# ==========================================

@login_required
@permission_required('mrp.view_billofmaterial', raise_exception=True)
def bom_list(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-bom_id')

    boms = BillOfMaterial.objects.all()

    if query:
        boms = boms.filter(
            Q(bom_id__icontains=query) | 
            Q(product__name__icontains=query)
        )

    valid_sorts = ['bom_id', '-bom_id', 'product__name', '-product__name', 'quantity', '-quantity']
    if sort_by in valid_sorts:
        boms = boms.order_by(sort_by)
    else:
        boms = boms.order_by('-bom_id')

    paginator = Paginator(boms, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'mrp/bom_list.html', {
        'boms': page_obj,
        'query': query,
        'sort_by': sort_by,
    })

@login_required
@permission_required('mrp.add_billofmaterial', raise_exception=True)
def bom_create(request):
    if request.method == 'POST':
        form = BillOfMaterialForm(request.POST)
        if form.is_valid():
            bom = form.save()
            messages.success(request, "Bill of Material created. Add components next.")
            return redirect('bom_detail', bom_id=bom.bom_id)
    else:
        form = BillOfMaterialForm()
    return render(request, 'mrp/bom_form.html', {'form': form, 'title': 'Create Bill of Material'})

@login_required
@permission_required('mrp.view_billofmaterial', raise_exception=True)
def bom_detail(request, bom_id):
    bom = get_object_or_404(BillOfMaterial, bom_id=bom_id)
    
    if request.method == 'POST':
        if not request.user.has_perm('mrp.change_billofmaterial'):
            messages.error(request, "Permission Denied: You cannot modify Bills of Material.")
            return redirect('bom_detail', bom_id=bom_id)

        if 'add_component' in request.POST:
            form = BomComponentForm(request.POST)
            if form.is_valid():
                comp = form.save(commit=False)
                comp.bom = bom
                comp.save()
                messages.success(request, f"{comp.component.name} added to BOM.")
                return redirect('bom_detail', bom_id=bom.bom_id)
            
    form = BomComponentForm()
    return render(request, 'mrp/bom_detail.html', {'bom': bom, 'form': form})

# ==========================================
# MANUFACTURING ORDER VIEWS
# ==========================================

@login_required
@permission_required('mrp.view_manufacturingorder', raise_exception=True)
def mo_list(request):
    query = request.GET.get('q', '')
    state_filter = request.GET.get('state', '')
    sort_by = request.GET.get('sort', '-date_created')

    mos = ManufacturingOrder.objects.all()

    if query:
        mos = mos.filter(
            Q(mo_id__icontains=query) | 
            Q(product__name__icontains=query)
        )

    if state_filter:
        mos = mos.filter(state=state_filter)

    valid_sorts = ['mo_id', '-mo_id', 'product__name', '-product__name', 'qty_to_produce', '-qty_to_produce', 'state', '-state', 'date_created', '-date_created']
    if sort_by in valid_sorts:
        mos = mos.order_by(sort_by)
    else:
        mos = mos.order_by('-date_created')

    paginator = Paginator(mos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'mrp/mo_list.html', {
        'mos': page_obj,
        'query': query,
        'state_filter': state_filter,
        'sort_by': sort_by,
    })

@login_required
@permission_required('mrp.add_manufacturingorder', raise_exception=True)
def mo_create(request):
    if request.method == 'POST':
        form = ManufacturingOrderForm(request.POST)
        if form.is_valid():
            mo = form.save()
            messages.success(request, "Manufacturing Order created.")
            return redirect('mo_detail', mo_id=mo.mo_id)
    else:
        form = ManufacturingOrderForm()
    return render(request, 'mrp/mo_form.html', {'form': form, 'title': 'Create Manufacturing Order'})

@login_required
@permission_required('mrp.view_manufacturingorder', raise_exception=True)
def mo_detail(request, mo_id):
    mo = get_object_or_404(ManufacturingOrder, mo_id=mo_id)
    history_records = mo.history.all().order_by('-history_date')
    
    if request.method == 'POST':
        if not request.user.has_perm('mrp.change_manufacturingorder'):
            messages.error(request, "Permission Denied: You cannot modify Manufacturing Orders.")
            return redirect('mo_detail', mo_id=mo.mo_id)

        if 'confirm' in request.POST:
            mo.state = 'confirmed'
            mo.save()
            messages.success(request, "Manufacturing Order confirmed and sent to factory floor.")
        elif 'produce' in request.POST:
            try:
                mo.produce()
                messages.success(request, f"Successfully produced {mo.qty_to_produce} units of {mo.product.name}!")
            except ValueError as e:
                messages.error(request, str(e))
        return redirect('mo_detail', mo_id=mo.mo_id)
        
    return render(request, 'mrp/mo_detail.html', {'mo': mo, 'history_records': history_records})