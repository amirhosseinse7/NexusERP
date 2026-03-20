from django.shortcuts import render, redirect
from apps.core.models import Material, Partner
from apps.logistics.models import SalesOrder, SalesOrderLine
from django.contrib import messages

def create_web_order(request):
    """
    Simulates a 'Checkout' process.
    Creates a SalesOrder in Logistics.
    """
    products = Material.objects.all()
    
    if request.method == 'POST':
        sku = request.POST.get('sku')
        qty = int(request.POST.get('qty'))
        mode = request.POST.get('mode') 
        

        customer = Partner.objects.filter(is_customer=True).first()
        product = Material.objects.get(sku=sku)
        

        so = SalesOrder.objects.create(
            customer=customer,
            delivery_mode=mode,
            state='draft'
        )
        

        SalesOrderLine.objects.create(
            order=so,
            material=product,
            qty_requested=qty
        )
        

        try:
            so.confirm_order()
            messages.success(request, f"Order {so.so_id} Placed & Stock Reserved!")
        except ValueError as e:

            messages.error(request, f"Order Failed: {str(e)}")
            so.delete() 
            
        return redirect('logistics_home') 

    return render(request, 'store/checkout.html', {'products': products})