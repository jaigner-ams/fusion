#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, '/var/www/fusion')

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fusion.settings')
django.setup()

from mgmt.models import CustomUser

def create_lab_user(username, password='test123'):
    """Create a lab user with the specified username and password."""
    try:
        # Check if user already exists
        if CustomUser.objects.filter(username=username).exists():
            print(f"User '{username}' already exists - skipping")
            return False
        
        # Create the lab user
        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            user_type='lab',
            email=f'{username}@lab.local'  # Default email
        )
        user.first_name = username.capitalize()
        user.save()
        
        print(f"✓ Created lab user '{username}' with password 'test123'")
        return True
    except Exception as e:
        print(f"✗ Error creating user '{username}': {str(e)}")
        return False

# Create the three lab users
print("Creating lab users...")
print("-" * 40)

users_to_create = ['keith', 'john', 'brandon']
created_count = 0

for username in users_to_create:
    if create_lab_user(username):
        created_count += 1

print("-" * 40)
print(f"Summary: Created {created_count} out of {len(users_to_create)} users")

# Display all lab users
print("\nCurrent lab users in the system:")
print("-" * 40)
lab_users = CustomUser.objects.filter(user_type='lab')
for user in lab_users:
    print(f"- {user.username} ({user.email})")