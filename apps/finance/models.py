from django.db import models
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from simple_history.models import HistoricalRecords


from apps.core.models import TenantAwareModel

class Account(TenantAwareModel):
    TYPE_CHOICES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class JournalEntry(TenantAwareModel):
    entry_id = models.CharField(max_length=50, primary_key=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=200)
    

    history = HistoricalRecords()
    
    def save(self, *args, **kwargs):
        if not self.entry_id:
            from apps.core.models import SystemSequence
            self.entry_id = SystemSequence.get_next('finance.journal.entry', 'JE-', 5, "Journal Entries")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date.date()} - {self.reference}"

class JournalItem(TenantAwareModel):
    entry = models.ForeignKey(JournalEntry, related_name='items', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, null=True, blank=True)
    debit = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.account.code} | Dr: {self.debit} Cr: {self.credit}"

# ==========================================
# INVOICING & BILLING ENGINE
# ==========================================

class Invoice(TenantAwareModel):
    TYPE_CHOICES = [
        ('out_invoice', 'Customer Invoice (Sales)'),
        ('in_invoice', 'Vendor Bill (Purchases)'),
    ]
    STATE_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
    ]

    invoice_id = models.CharField(max_length=50, primary_key=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    partner = models.ForeignKey('core.Partner', on_delete=models.PROTECT)
    source_document = models.CharField(max_length=100, blank=True, help_text="e.g., SO-1234")
    
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='draft')


    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            from apps.core.models import SystemSequence
            prefix = "INV-" if self.type == 'out_invoice' else "BILL-"
            seq_code = 'finance.invoice' if self.type == 'out_invoice' else 'finance.bill'
            seq_name = 'Customer Invoices' if self.type == 'out_invoice' else 'Vendor Bills'
            self.invoice_id = SystemSequence.get_next(seq_code, prefix, 4, seq_name)
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        return sum(line.subtotal for line in self.lines.all())

    @property
    def amount_due(self):
        paid = sum(p.amount for p in self.payments.all())
        return self.total_amount - paid

    def post(self):
        if self.state != 'draft':
            return

        with transaction.atomic():
            self.state = 'posted'
            self.save()

            je = JournalEntry.objects.create(
                date=self.date,
                reference=f"{self.get_type_display()}: {self.invoice_id} ({self.source_document})"
            )

            def create_line(account_code, account_name, acc_type, debit, credit, desc):
                acc, _ = Account.objects.get_or_create(
                    code=account_code, 
                    defaults={'name': account_name, 'type': acc_type}
                )
                if debit > 0 or credit > 0:
                    JournalItem.objects.create(
                        entry=je, account=acc, description=desc, debit=debit, credit=credit
                    )

            total = self.total_amount

            if self.type == 'out_invoice':
                create_line('12000', 'Accounts Receivable', 'asset', total, 0, f"Owed by {self.partner.name}")
                create_line('40000', 'Sales Revenue', 'income', 0, total, f"Revenue from {self.invoice_id}")
            
            elif self.type == 'in_invoice':
                create_line('20100', 'Goods Received Not Invoiced', 'liability', total, 0, f"Clearing GRNI for {self.invoice_id}")
                create_line('21000', 'Accounts Payable', 'liability', 0, total, f"Owed to {self.partner.name}")

class InvoiceLine(TenantAwareModel):
    invoice = models.ForeignKey(Invoice, related_name='lines', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1.0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

# ==========================================
# PAYMENTS ENGINE
# ==========================================

class Payment(TenantAwareModel):
    METHOD_CHOICES = [
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]

    payment_id = models.CharField(max_length=50, primary_key=True, blank=True)
    invoice = models.ForeignKey(Invoice, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='bank')


    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.payment_id:
            from apps.core.models import SystemSequence
            self.payment_id = SystemSequence.get_next('finance.payment', 'PAY-', 4, "Payments")
        super().save(*args, **kwargs)

    def post(self):
        with transaction.atomic():
            je = JournalEntry.objects.create(
                date=self.date,
                reference=f"Payment for {self.invoice.invoice_id}"
            )

            def create_line(code, name, acc_type, debit, credit, desc):
                acc, _ = Account.objects.get_or_create(code=code, defaults={'name': name, 'type': acc_type})
                if debit > 0 or credit > 0:
                    JournalItem.objects.create(entry=je, account=acc, description=desc, debit=debit, credit=credit)

            bank_code = '11000' if self.method == 'bank' else '11100'
            bank_name = 'Bank Account' if self.method == 'bank' else 'Cash'

            if self.invoice.type == 'out_invoice':
                create_line(bank_code, bank_name, 'asset', self.amount, 0, f"Received from {self.invoice.partner.name}")
                create_line('12000', 'Accounts Receivable', 'asset', 0, self.amount, f"Payment clearing {self.invoice.invoice_id}")
            
            elif self.invoice.type == 'in_invoice':
                create_line('21000', 'Accounts Payable', 'liability', self.amount, 0, f"Payment to {self.invoice.partner.name}")
                create_line(bank_code, bank_name, 'asset', 0, self.amount, f"Payment clearing {self.invoice.invoice_id}")

            total_paid = sum(p.amount for p in self.invoice.payments.all())
            
            if total_paid >= (self.invoice.total_amount - Decimal('0.01')):
                self.invoice.state = 'paid'
                self.invoice.save()