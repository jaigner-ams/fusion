#!/usr/bin/env python
"""Quick email verification - checks if settings are configured."""

import os
import sys
import django

sys.path.insert(0, '/var/www/fusion')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fusion.settings')
django.setup()

from django.conf import settings

print("\n✅ Email Configuration Set:")
print(f"   Email User: {settings.EMAIL_HOST_USER}")
print(f"   Email Host: {settings.EMAIL_HOST}")
print(f"   From Email: {settings.DEFAULT_FROM_EMAIL}")
print(f"   SMTP Backend: {'Enabled' if 'smtp' in settings.EMAIL_BACKEND else 'Disabled (using console)'}")

if 'smtp' in settings.EMAIL_BACKEND.lower():
    print("\n✅ Email system is configured for SMTP sending")
    print("   New dentists will receive credentials via email")
else:
    print("\n⚠️  Email system is in console mode (for testing)")
    
print("\n📧 When creating a new dentist:")
print("   - If email provided: Credentials will be sent automatically")
print("   - If no email: Credentials shown on screen only")
print("\nTo test sending an email, run:")
print("   python test_email.py recipient@example.com")