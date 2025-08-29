# AMS Fusion Email Configuration Guide

## Overview
AMS Fusion automatically sends email notifications to new dentists with their login credentials when their accounts are created.

## Email Configuration Steps

### 1. Edit Email Settings
Open `/var/www/fusion/fusion/settings.py` and update the following settings:

```python
# Email Configuration (around line 166-179)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'  # Your email address
EMAIL_HOST_PASSWORD = 'your-app-password'  # Your email password
DEFAULT_FROM_EMAIL = 'AMS Fusion <your-email@domain.com>'
SERVER_EMAIL = 'AMS Fusion <your-email@domain.com>'

# Site URL for email links
SITE_URL = 'https://your-domain.com'  # Your actual domain
```

### 2. Email Provider Settings

#### Gmail Configuration
1. Use `smtp.gmail.com` as EMAIL_HOST
2. Create an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
   - Use this password as EMAIL_HOST_PASSWORD

#### SendGrid Configuration
```python
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'apikey'  # Always 'apikey' for SendGrid
EMAIL_HOST_PASSWORD = 'your-sendgrid-api-key'
```

#### Amazon SES Configuration
```python
EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'  # Use your region
EMAIL_PORT = 587
EMAIL_HOST_USER = 'your-smtp-username'
EMAIL_HOST_PASSWORD = 'your-smtp-password'
```

### 3. Testing Email Configuration

#### Test with Console Backend (Development)
To test without actually sending emails, use the console backend:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```
This will print emails to the terminal instead of sending them.

#### Test Email Script
Create and run this test script:
```bash
source /var/www/fusion/venv/bin/activate
python manage.py shell
```

Then in the Python shell:
```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'Test Email from AMS Fusion',
    'This is a test email to verify email configuration.',
    settings.DEFAULT_FROM_EMAIL,
    ['test@example.com'],  # Replace with your email
    fail_silently=False,
)
```

### 4. Restart Apache After Configuration
```bash
sudo systemctl restart apache2
```

## Email Features

### New Dentist Account Email
When a new dentist is created, they automatically receive:
- Username
- Temporary password
- Login URL
- Instructions for first login

### Email Templates
Located in `/var/www/fusion/mgmt/templates/mgmt/email/`:
- `new_dentist_credentials.html` - HTML version
- `new_dentist_credentials.txt` - Plain text version

### Conditions for Sending
Emails are sent when:
1. A new dentist account is created
2. An email address is provided (not using default)
3. Email settings are properly configured

### Troubleshooting

#### Emails Not Sending
1. Check Apache error logs: `sudo tail -f /var/log/apache2/error.log`
2. Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are set
3. Check firewall allows outbound connections on port 587
4. For Gmail, ensure "Less secure app access" or use App Password

#### Test Without Sending
Set `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` to see emails in logs without sending.

## Security Notes
- Never commit email passwords to git
- Use environment variables for production:
  ```python
  import os
  EMAIL_HOST_USER = os.environ.get('EMAIL_USER')
  EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD')
  ```
- Use app-specific passwords when available
- Consider using dedicated transactional email services (SendGrid, Amazon SES, Mailgun)

## Manual Email Sending
To manually send credentials to a dentist:
```python
from mgmt.models import Dentist
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

dentist = Dentist.objects.get(id=1)  # Get specific dentist
context = {
    'dentist_name': dentist.name,
    'username': dentist.user.username,
    'password': 'temporary_password',  # Set a new password first
    'lab_name': dentist.lab.first_name or dentist.lab.username,
    'login_url': f"{settings.SITE_URL}/accounts/login/",
    'current_year': 2024,
}

html_message = render_to_string('mgmt/email/new_dentist_credentials.html', context)
plain_message = render_to_string('mgmt/email/new_dentist_credentials.txt', context)

send_mail(
    'Your AMS Fusion Account',
    plain_message,
    settings.DEFAULT_FROM_EMAIL,
    [dentist.user.email],
    html_message=html_message,
)
```