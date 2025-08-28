#!/usr/bin/env python
"""Test script to verify automatic user creation for dentists"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fusion.settings')
sys.path.insert(0, '/var/www/fusion')
django.setup()

from mgmt.models import Dentist, CustomUser

def test_auto_user_creation():
    """Test that creating a dentist automatically creates a user account"""
    
    # Get a lab user for testing (or create one if needed)
    lab_user = CustomUser.objects.filter(user_type='lab').first()
    if not lab_user:
        lab_user = CustomUser.objects.create_user(
            username='testlab',
            email='lab@test.com',
            password='testpass123',
            user_type='lab'
        )
        print(f"Created test lab user: {lab_user.username}")
    
    # Create a new dentist
    print("\nCreating new dentist...")
    dentist = Dentist.objects.create(
        name="Test Dentist Auto User",
        lab=lab_user
    )
    
    # Verify user was created
    assert dentist.user is not None, "User account was not created!"
    assert dentist.user.user_type == 'dentist', "User type is not 'dentist'"
    assert dentist.user.first_name == dentist.name, "User first name doesn't match dentist name"
    
    # Check for generated credentials
    if hasattr(dentist, '_generated_username') and hasattr(dentist, '_generated_password'):
        print(f"\n✓ Dentist created successfully!")
        print(f"  Dentist Name: {dentist.name}")
        print(f"  Username: {dentist._generated_username}")
        print(f"  Password: {dentist._generated_password}")
        print(f"  Email: {dentist.user.email}")
        print(f"  User ID: {dentist.user.id}")
        print(f"  User Type: {dentist.user.user_type}")
    else:
        print(f"\n✓ Dentist created with user account!")
        print(f"  Dentist Name: {dentist.name}")
        print(f"  Username: {dentist.user.username}")
        print(f"  Email: {dentist.user.email}")
    
    # Clean up test data
    print("\nCleaning up test data...")
    dentist.user.delete()  # This will also delete the dentist due to CASCADE
    print("✓ Test data cleaned up")
    
    print("\n✅ Test passed! Dentists now automatically have user accounts created.")

if __name__ == '__main__':
    test_auto_user_creation()