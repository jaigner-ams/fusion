from django.core.management.base import BaseCommand
from mgmt.models import CustomUser
from onevoice.models import OVPostcardInventory
from onevoice.notifications import send_ov_notification


class Command(BaseCommand):
    help = 'Check postcard inventory levels and alert admins when below threshold'

    def handle(self, *args, **options):
        all_inventory = OVPostcardInventory.objects.select_related('client', 'design')
        low_items = [inv for inv in all_inventory if inv.is_below_threshold()]

        admins = CustomUser.objects.filter(roles__role__in=['ov_admin', 'superadmin']).distinct()

        for inv in low_items:
            for admin in admins:
                send_ov_notification(
                    'inventory_low', admin, client=inv.client,
                    title=f'Low Inventory: {inv.design.name}',
                    message=f'{inv.client.lab_name} has {inv.quantity_on_hand} postcards on hand (threshold: {inv.reorder_threshold}).',
                )
            self.stdout.write(f'Low inventory alert: {inv.client.lab_name} - {inv.design.name} ({inv.quantity_on_hand})')

        self.stdout.write(self.style.SUCCESS(f'Inventory check complete. {len(low_items)} alerts.'))
