from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import SalesOrder
from .serializers import SalesOrderSerializer
from apps.core.models import _thread_locals 

class SalesOrderViewSet(viewsets.ModelViewSet):
    """
    A robust, Tenant-Aware API endpoint for managing Sales Orders.
    External apps can GET, POST, PATCH, and DELETE orders here.
    """
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        """
        SaaS SECURITY OVERRIDE:
        API Token authentication happens after standard middleware. 
        We must explicitly set the active Tenant Workspace into the thread 
        so our SystemSequences and TenantManagers don't crash.
        """
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            _thread_locals.company = request.user.profile.company

    def get_queryset(self):

        return SalesOrder.objects.all().order_by('-date_order')