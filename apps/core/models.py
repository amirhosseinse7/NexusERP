import threading
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from django.contrib.auth.models import User, Permission
from simple_history.models import HistoricalRecords

# ==========================================
# SAAS ENGINE: MULTI-TENANCY (THREAD LOCAL)
# ==========================================
_thread_locals = threading.local()

def get_current_company():
    """Fetches the company for the current request thread."""
    return getattr(_thread_locals, 'company', None)

class Company(models.Model):
    """The root SaaS Tenant model."""
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name

class TenantManager(models.Manager):
    """Automatically filters all database queries to the current Company."""
    def get_queryset(self):
        company = get_current_company()
        if company:
            return super().get_queryset().filter(company=company)
        return super().get_queryset()

class TenantAwareModel(models.Model):
    """Abstract base class. Makes models Multi-Tenant."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, editable=False)
    objects = TenantManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.pk and not hasattr(self, 'company_id') or not self.company_id:
            company = get_current_company()
            if company:
                self.company = company
            else:
                raise ValueError("Cannot save a TenantAwareModel without a current company in context.")
        super().save(*args, **kwargs)

# ==========================================
# RBAC: GRANULAR ROLES & PERMISSIONS
# ==========================================
class WorkspaceRole(TenantAwareModel):
    """ 
    Custom roles created by Tenant Admins (e.g., 'Sales Manager', 'Picker').
    Locked to the specific Tenant Workspace.
    """
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, help_text="Django native permissions linked to this role.")

    def __str__(self):
        return f"[{self.company.name}] {self.name}"

class UserProfile(models.Model):
    """Links the default Django User to a specific Company and Role."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users')
    

    role = models.ForeignKey(WorkspaceRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    
    def __str__(self):
        return f"{self.user.username} - {self.company.name}"

    def sync_permissions(self):
        """ Instantly applies the WorkspaceRole's permissions to the Django User in the DB """
        if self.user.is_superuser:
            return 
            

        self.user.user_permissions.clear()
        if self.role:
            self.user.user_permissions.set(self.role.permissions.all())

# ==========================================
# THE AUTOMATED SEQUENCE ENGINE
# ==========================================
class SystemSequence(TenantAwareModel):
    name = models.CharField(max_length=100, help_text="e.g., Sales Orders")
    code = models.CharField(max_length=50, help_text="e.g., sales.order")
    prefix = models.CharField(max_length=20, blank=True, help_text="e.g., SO-")
    padding = models.IntegerField(default=4, help_text="Number of digits (e.g., 4 -> 0001)")
    next_number = models.IntegerField(default=1)

    class Meta:
        unique_together = ('company', 'code')

    def __str__(self):
        return f"[{self.company.name}] {self.name} ({self.prefix})"

    @classmethod
    def get_next(cls, code, default_prefix="", default_padding=4, default_name=""):
        company = get_current_company()
        if not company: return "SYS-ERR"

        with transaction.atomic():
            seq, created = cls.objects.select_for_update().get_or_create(
                company=company,
                code=code,
                defaults={
                    'name': default_name or f"Sequence {code}",
                    'prefix': default_prefix,
                    'padding': default_padding,
                    'next_number': 1
                }
            )
            number_str = str(seq.next_number).zfill(seq.padding)
            result = f"{seq.prefix}{number_str}"
            seq.next_number += 1
            seq.save()
            return result

# ==========================================
# CORE MODELS
# ==========================================
class ProductCategory(TenantAwareModel):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = "Product Categories"

    def __str__(self):
        return self.name

class UoM(TenantAwareModel):
    name = models.CharField(max_length=50) 
    ratio = models.DecimalField(max_digits=10, decimal_places=4, default=1.0) 

    def __str__(self):
        return self.name

class Pricelist(TenantAwareModel):
    name = models.CharField(max_length=50)
    currency = models.CharField(max_length=10, default='USD')
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_price(self, material):
        item = self.items.filter(material=material).first()
        if item: return item.fixed_price
        return material.sales_price

class Material(TenantAwareModel):
    sku = models.CharField(max_length=50, primary_key=True, help_text="Unique Stock Keeping Unit", blank=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True)
    uom = models.ForeignKey(UoM, on_delete=models.SET_NULL, null=True)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    volume_m3 = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    min_stock_level = models.IntegerField(default=10)
    max_stock_level = models.IntegerField(default=100)
    lead_time_days = models.IntegerField(default=1)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    sales_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    auto_reorder = models.BooleanField(default=False)
    custom_reorder_qty = models.IntegerField(null=True, blank=True)
    preferred_supplier = models.ForeignKey('Partner', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'is_supplier': True})

    abc_class = models.CharField(max_length=1, choices=[('A','A'), ('B','B'), ('C','C')], default='C')
    forecast_30d = models.FloatField(default=0)
    churn_rate = models.FloatField(default=0)
    supplier_perf = models.FloatField(default=0)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = SystemSequence.get_next('material.sku', 'SKU-', 5, "Products")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.sku}] {self.name}"

    def update_analytics(self):
        from apps.inventory.models import StockMove, StockQuant
        from apps.logistics.models import PurchaseOrderLine

        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_sales = StockMove.objects.filter(
            material=self, location_dest__type='customer', state='done', date__gte=thirty_days_ago
        ).aggregate(total=Sum('qty'))['total'] or 0
        
        self.forecast_30d = float(recent_sales)

        quants = StockQuant.objects.filter(material=self, location__type='internal')
        totals = quants.aggregate(total_hand=Sum('quantity_on_hand'), total_reserved=Sum('quantity_reserved'))
        available = (totals['total_hand'] or 0) - (totals['total_reserved'] or 0)

        self.churn_rate = float((recent_sales / available) * 100) if available > 0 else 0.0

        po_lines = PurchaseOrderLine.objects.filter(material=self)
        ordered = sum(l.qty_requested for l in po_lines)
        received = sum(l.qty_received for l in po_lines)
        
        self.supplier_perf = float((received / ordered) * 100) if ordered > 0 else 100.0
        self.abc_class = 'A' if recent_sales > 50 else 'B' if recent_sales > 10 else 'C'

        self.save(update_fields=['forecast_30d', 'churn_rate', 'supplier_perf', 'abc_class'])

class PricelistItem(TenantAwareModel):
    pricelist = models.ForeignKey(Pricelist, related_name='items', on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    fixed_price = models.DecimalField(max_digits=10, decimal_places=2)
    min_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0) 

class Partner(TenantAwareModel):
    partner_id = models.CharField(max_length=50, primary_key=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(blank=True)
    is_customer = models.BooleanField(default=False)
    is_supplier = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    pricelist = models.ForeignKey(Pricelist, on_delete=models.SET_NULL, null=True, blank=True)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.partner_id:
            prefix = "CUST-" if self.is_customer else "VEND-" if self.is_supplier else "PTN-"
            self.partner_id = SystemSequence.get_next(f'partner.{prefix.lower()}', prefix, 4, "Partners")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name