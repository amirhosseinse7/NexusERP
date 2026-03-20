from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q  

from .models import Opportunity, OpportunityLine
from .forms import OpportunityForm, OpportunityLineForm

@login_required
@permission_required('crm.view_opportunity', raise_exception=True)
def opportunity_board(request):

    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-date_created')

    opps = Opportunity.objects.all()


    if query:
        opps = opps.filter(
            Q(opp_id__icontains=query) | 
            Q(title__icontains=query) |
            Q(customer__name__icontains=query)
        )


    valid_sorts = ['date_created', '-date_created', 'expected_revenue', '-expected_revenue', 'probability', '-probability']
    if sort_by in valid_sorts:
        opps = opps.order_by(sort_by)
    else:
        opps = opps.order_by('-date_created')


    context = {
        'new_opps': opps.filter(state='new'),
        'qual_opps': opps.filter(state='qualified'),
        'won_opps': opps.filter(state='won'),
        'lost_opps': opps.filter(state='lost'),
        'query': query,
        'sort_by': sort_by,
    }
    return render(request, 'crm/opportunity_board.html', context)

@login_required
@permission_required('crm.add_opportunity', raise_exception=True)
def opportunity_create(request):
    if request.method == 'POST':
        form = OpportunityForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Opportunity logged successfully.")
            return redirect('opportunity_board')
    else:
        form = OpportunityForm()
    return render(request, 'crm/opportunity_form.html', {'form': form})

@login_required
@permission_required('crm.view_opportunity', raise_exception=True)
def opportunity_detail(request, opp_id):
    opp = get_object_or_404(Opportunity, opp_id=opp_id)
    history_records = opp.history.all().order_by('-history_date')
    
    if request.method == 'POST':
        if not request.user.has_perm('crm.change_opportunity'):
            messages.error(request, "Permission Denied: You cannot modify CRM records.")
            return redirect('opportunity_detail', opp_id=opp_id)


        if 'add_line' in request.POST:
            line_form = OpportunityLineForm(request.POST)
            if line_form.is_valid():
                line = line_form.save(commit=False)
                line.opportunity = opp
                

                if opp.customer.pricelist:
                    line.price_unit = opp.customer.pricelist.get_price(line.material)
                else:
                    line.price_unit = line.material.sales_price
                line.save()
                

                opp.expected_revenue = sum(l.subtotal for l in opp.lines.all())
                opp.save()
                
                messages.success(request, f"{line.material.name} added to quote.")
                return redirect('opportunity_detail', opp_id=opp.opp_id)


        elif 'change_state' in request.POST:
            new_state = request.POST.get('state')
            if new_state in dict(Opportunity.STATE_CHOICES).keys():
                opp.state = new_state
                opp.save()
                messages.success(request, f"Opportunity moved to {new_state.title()}.")
            return redirect('opportunity_detail', opp_id=opp.opp_id)
            

        elif 'convert_to_so' in request.POST:
            try:
                new_so = opp.convert_to_sales_order()
                messages.success(request, "Opportunity won! Draft Sales Order generated with all items.")
                return redirect('so_detail', so_id=new_so.so_id)
            except Exception as e:
                messages.error(request, str(e))
                return redirect('opportunity_detail', opp_id=opp.opp_id)

    line_form = OpportunityLineForm()
    return render(request, 'crm/opportunity_detail.html', {
        'opp': opp, 
        'line_form': line_form,
        'history_records': history_records
    })