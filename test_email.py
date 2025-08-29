#!/usr/bin/env python
"""
Test email configuration for AMS Fusion
Run this script to verify email settings are working correctly.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, '/var/www/fusion')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fusion.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from datetime import datetime

def test_simple_email(recipient_email):
    """Send a simple test email."""
    try:
        print(f"Sending test email to {recipient_email}...")
        
        result = send_mail(
            subject='AMS Fusion - Test Email',
            message='This is a test email from AMS Fusion to verify email configuration is working correctly.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        if result:
            print("✓ Simple test email sent successfully!")
            return True
        else:
            print("✗ Failed to send simple test email")
            return False
            
    except Exception as e:
        print(f"✗ Error sending email: {str(e)}")
        return False

def test_template_email(recipient_email, dentist_name="Test Dentist"):
    """Send a test email using the new dentist credentials template."""
    try:
        print(f"Sending template email to {recipient_email}...")
        
        # Prepare test context
        context = {
            'dentist_name': dentist_name,
            'username': 'testuser123',
            'password': 'TempPass123!',
            'lab_name': 'Test Lab',
            'login_url': f"{settings.SITE_URL}/accounts/login/" if hasattr(settings, 'SITE_URL') else 'http://your-domain.com/accounts/login/',
            'current_year': datetime.now().year,
        }
        
        # Render templates
        html_message = render_to_string('mgmt/email/new_dentist_credentials.html', context)
        plain_message = render_to_string('mgmt/email/new_dentist_credentials.txt', context)
        
        result = send_mail(
            subject='AMS Fusion - Test Account Credentials',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if result:
            print("✓ Template email sent successfully!")
            return True
        else:
            print("✗ Failed to send template email")
            return False
            
    except Exception as e:
        print(f"✗ Error sending template email: {str(e)}")
        return False

def check_email_settings():
    """Display current email configuration."""
    print("\n" + "="*50)
    print("Current Email Configuration:")
    print("="*50)
    
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER if settings.EMAIL_HOST_USER else '(not set)'}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else '(not set)'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"SITE_URL: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else '(not set)'}")
    
    if 'console' in settings.EMAIL_BACKEND.lower():
        print("\n⚠️  WARNING: Using console backend - emails will be printed to console, not sent!")
    elif not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        print("\n⚠️  WARNING: Email credentials not configured! Emails will not send.")
    
    print("="*50 + "\n")

def main():
    """Main test function."""
    print("\nAMS Fusion Email Configuration Test")
    print("====================================\n")
    
    # Check current settings
    check_email_settings()
    
    # Get recipient email
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = input("Enter recipient email address for test (or press Enter to skip): ").strip()
    
    if not recipient:
        print("\nNo recipient provided. Showing configuration only.")
        print("\nTo test email sending, run:")
        print("  python test_email.py your-email@example.com")
        return
    
    print(f"\nTesting email to: {recipient}\n")
    
    # Test simple email
    simple_success = test_simple_email(recipient)
    
    # Test template email
    if simple_success:
        print("\nTesting template email...")
        template_success = test_template_email(recipient)
        
        if template_success:
            print("\n✓ All email tests passed successfully!")
            print(f"Check {recipient} for test emails.")
    else:
        print("\n✗ Email testing failed. Please check your configuration.")
        print("Common issues:")
        print("1. EMAIL_HOST_USER and EMAIL_HOST_PASSWORD not set")
        print("2. Incorrect SMTP server settings")
        print("3. Firewall blocking port 587")
        print("4. For Gmail: Need app-specific password")

if __name__ == "__main__":
    main()