#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, '/var/www/fusion')

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fusion.settings')
django.setup()

from mgmt.forms import CreditPurchaseForm

# Test form validation with quantity less than 5
print("Testing CreditPurchaseForm with new 5 credit minimum:\n")
print("="*50)

# Test 1: quantity < 5 (should fail)
form_data = {'quantity': 3, 'quality_type': 'economy'}
form = CreditPurchaseForm(data=form_data)
print("Test 1: quantity=3")
print(f"  Valid: {form.is_valid()}")
if not form.is_valid() and 'quantity' in form.errors:
    print(f"  Error: {form.errors['quantity'][0]}")
print()

# Test 2: quantity = 5 (should pass)
form_data = {'quantity': 5, 'quality_type': 'economy'}
form = CreditPurchaseForm(data=form_data)
print("Test 2: quantity=5")
print(f"  Valid: {form.is_valid()}")
if not form.is_valid():
    print(f"  Errors: {form.errors}")
print()

# Test 3: quantity > 5 (should pass)
form_data = {'quantity': 10, 'quality_type': 'economy'}
form = CreditPurchaseForm(data=form_data)
print("Test 3: quantity=10")
print(f"  Valid: {form.is_valid()}")
if not form.is_valid():
    print(f"  Errors: {form.errors}")
print()

# Test 4: Check HTML widget attributes
form = CreditPurchaseForm()
print("Test 4: HTML widget attributes")
print(f"  min attribute: {form.fields['quantity'].widget.attrs.get('min', 'Not set')}")
print(f"  placeholder: {form.fields['quantity'].widget.attrs.get('placeholder', 'Not set')}")