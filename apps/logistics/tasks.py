from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.conf import settings
from io import BytesIO
from xhtml2pdf import pisa
import time

from apps.logistics.models import SalesOrder, PurchaseOrder

@shared_task
def send_order_email_task(order_id, order_type, recipient_email):

    time.sleep(3) 
    
    if order_type == 'SO':
        order = SalesOrder.objects.get(so_id=order_id)
        template_path = 'logistics/so_pdf.html'
        subject = f"Sales Order {order.so_id} from NexusHQ"
    else:
        order = PurchaseOrder.objects.get(po_id=order_id)
        template_path = 'logistics/po_pdf.html'
        subject = f"Purchase Order {order.po_id} from NexusHQ"


    template = get_template(template_path)

    html = template.render({'so': order, 'order': order, 'type': 'DOCUMENT'}) 
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, encoding='UTF-8')

    if not pdf.err:

        email = EmailMessage(
            subject=subject,
            body=f"Dear Partner,\n\nPlease find attached the document {order_id} for your review.\n\nThank you,\nNexusERP System",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        

        email.attach(f"{order_id}.pdf", result.getvalue(), 'application/pdf')
        

        email.send()
        
    return f"Email successfully generated and sent to {recipient_email} for {order_id}"