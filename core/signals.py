from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User

@receiver(post_save, sender=User)
def send_credentials_on_create(sender, instance, created, **kwargs):
    """
    Triggers when a new User is created.
    Checks for '_plain_password' attribute to send raw credentials via email.
    """
    if created and hasattr(instance, '_plain_password'):        
        if instance.role == 'OWNER':
            role_display = "Society Owner"
            sender_title = "Society Administrator"
        elif instance.role == 'TENANT':
            role_display = "Tenant"
            sender_title = "Flat Owner"
        else:
            role_display = "User"
            sender_title = "Administrator"

        subject = f'Welcome to Society Management - Your {role_display} Account'
        
        message = (
            f"Hello {instance.first_name} {instance.last_name},\n\n"
            f"Your account has been successfully created by the {sender_title}.\n\n"
            f"Here are your login credentials:\n"
            f"--------------------------------\n"
            f"Email: {instance.email}\n"
            f"Password: {instance._plain_password}\n"
            f"--------------------------------\n\n"
            f"Best regards,\n"
            f"Society Management Team"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                fail_silently=False,
            )
            print(f"Credentials sent to {instance.email}")
        except Exception as e:
            # In production, use a logger instead of print
            print(f"Failed to send email to {instance.email}: {str(e)}")