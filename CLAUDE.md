# Fusion Project - Development Guide

## Project Overview
This is a Django-based dental lab management system that handles pricing, credit management, and file sharing between dentists and labs.

## Environment Setup

### IMPORTANT: Virtual Environment
**Always activate the virtual environment before running any Python/Django commands:**
```bash
source /var/www/fusion/venv/bin/activate
```

### Project Structure
- **Main app**: `mgmt/` - Contains all business logic, models, views, and templates
- **Project root**: `/var/www/fusion/`
- **Database**: MySQL (configured in `fusion/settings.py`)
- **Python version**: Uses Python 3 with Django

## Key Features

### User Types
1. **Admin** - Full system access
2. **Lab** - Can manage dentists, prices, and download files
3. **Dentist** - Can purchase credits and upload files

### Core Models (`mgmt/models.py`)
- `CustomUser` - Extended Django user with user_type and credits
- `Dentist` - Dentist profiles linked to labs
- `DefaultPriceList` - Default pricing tiers for labs
- `PriceList` - Custom pricing for specific dentists
- `CreditPurchase` - Credit purchase tracking
- `CreditTransaction` - Credit transaction history
- `FileUpload` - File sharing between dentists and labs

### Main Features
1. **Price Management** - Tiered pricing system with economy/premium options
2. **Credit System** - Purchase, deduction, and transaction tracking
3. **File Upload System** - Dentists upload files, labs download them
4. **User Management** - Create and manage dentist accounts with optional login credentials

## Common Commands

### Run Development Server
```bash
source /var/www/fusion/venv/bin/activate
python manage.py runserver
```

### Database Migrations
```bash
source /var/www/fusion/venv/bin/activate
python manage.py makemigrations
python manage.py migrate
```

### Create Superuser
```bash
source /var/www/fusion/venv/bin/activate
python manage.py createsuperuser
```

### Collect Static Files
```bash
source /var/www/fusion/venv/bin/activate
python manage.py collectstatic
```

## URL Structure
- `/admin/` - Django admin interface
- `/prices/` - Main application (redirects from root)
- `/accounts/login/` - Login page
- `/prices/upload-file/` - File upload (dentists)
- `/prices/lab-files/` - File downloads (labs)
- `/prices/credit-management/` - Credit management interface

## File Upload Configuration
- **Max file size**: 50MB
- **Upload directory**: `/var/www/fusion/media/dentist_uploads/`
- **Media URL**: `/media/`

## Development Notes

### Testing
When testing file uploads or other features:
1. Always use the venv: `source /var/www/fusion/venv/bin/activate`
2. Check user permissions using decorators (@lab_required, @dentist_required)
3. Files are stored in `media/dentist_uploads/YYYY/MM/DD/`

### Common Issues
1. **MySQL connection errors**: Ensure venv is activated
2. **Permission denied**: Check user_type and decorators
3. **File upload errors**: Verify media directory permissions and settings

### Security Considerations
- File uploads are restricted to authenticated dentists
- Downloads require lab or admin privileges
- All credit transactions are immutable (no editing/deletion)
- Password changes are logged and restricted to lab users

## Decorators (`mgmt/decorators.py`)
- `@lab_required` - Restricts view to lab users
- `@lab_or_admin_required` - Allows lab or admin users
- `@dentist_required` - Restricts view to dentist users

## Templates Location
All templates are in `mgmt/templates/mgmt/` and extend `base.html`

## Static Files
- Development: Served by Django
- Production: Should be served by web server from `/var/www/fusion/static/`

## Important Files to Review
1. `mgmt/models.py` - All data models
2. `mgmt/views.py` - Business logic and request handling
3. `mgmt/forms.py` - Form definitions and validation
4. `mgmt/urls.py` - URL routing
5. `fusion/settings.py` - Django configuration