from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.conf import settings
from io import BytesIO
from xhtml2pdf import pisa
import time

from apps.finance.models import Invoice

@shared_task
def send_invoice_email_task(invoice_id, recipient_email):
    """
    Generates an Invoice PDF and emails it to the customer.
    Runs entirely in the background worker queue.
    """
    time.sleep(3) 
    
    invoice = Invoice.objects.get(invoice_id=invoice_id)
    template_path = 'finance/invoice_pdf.html'
    subject = f"Invoice {invoice.invoice_id} from NexusHQ"


    template = get_template(template_path)
    html = template.render({'invoice': invoice}) 
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, encoding='UTF-8')

    if not pdf.err:

        email = EmailMessage(
            subject=subject,
            body=f"Dear Partner,\n\nPlease find attached the invoice {invoice_id} for your review.\n\nThank you,\nNexusERP System",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )

        email.attach(f"{invoice_id}.pdf", result.getvalue(), 'application/pdf')
        email.send()
        
    return f"Invoice {invoice_id} successfully emailed to {recipient_email}"