from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import OVNotification


def send_ov_notification(notification_type, recipient, client=None, title='', message='',
                         send_email=True, email_template=None, email_context=None):
    """Create an in-portal notification and optionally send email."""
    notif = OVNotification.objects.create(
        notification_type=notification_type,
        recipient=recipient,
        client=client,
        title=title,
        message=message,
    )

    if send_email and recipient.email:
        try:
            if email_template and email_context:
                html_message = render_to_string(email_template, email_context)
                send_mail(
                    subject=title,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    html_message=html_message,
                    fail_silently=True,
                )
            else:
                send_mail(
                    subject=title,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=True,
                )
            notif.email_sent = True
            notif.save(update_fields=['email_sent'])
        except Exception:
            pass

    return notif
