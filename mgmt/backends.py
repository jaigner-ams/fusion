from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db import connections
import hashlib

User = get_user_model()

class LabProfileBackend(BaseBackend):
    """
    Authenticate against the dentallabprofile.labprofile table
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Connect to the external database
        cursor = connections['labprofile'].cursor()
        
        try:
            # Query the labprofile table for matching credentials
            cursor.execute("""
                SELECT labID, labName, labEmail 
                FROM labprofile 
                WHERE labLogin = %s AND labPassword = %s AND enabled = 'Y'
            """, [username, password])
            
            row = cursor.fetchone()
            
            if row:
                lab_id, lab_name, lab_email = row
                
                # Try to get existing user or create new one
                try:
                    user = User.objects.get(lab_profile_id=lab_id)
                except User.DoesNotExist:
                    # Create new user
                    user = User.objects.create_user(
                        username=username,
                        email=lab_email or f'{username}@lab.local',
                        first_name=lab_name.split()[0] if lab_name else '',
                        last_name=' '.join(lab_name.split()[1:]) if lab_name and len(lab_name.split()) > 1 else '',
                        user_type='lab',
                        lab_profile_id=lab_id
                    )
                    # Set unusable password since we authenticate externally
                    user.set_unusable_password()
                    user.save()
                
                return user
                
        finally:
            cursor.close()
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None