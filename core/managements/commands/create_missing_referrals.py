from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Referral

class Command(BaseCommand):
    help = 'Create missing Referral instances for existing users'

    def handle(self, *args, **kwargs):
        users_without_referrals = User.objects.filter(referral__isnull=True)
        count = 0
        for user in users_without_referrals:
            Referral.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(f'Created Referral for user: {user.username}'))
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Total Referrals created: {count}'))