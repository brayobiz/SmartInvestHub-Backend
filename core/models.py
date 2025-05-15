from django.db import models
import logging
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

class Product(models.Model):
    name = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    daily_income = models.DecimalField(max_digits=10, decimal_places=2)
    return_rate = models.DecimalField(max_digits=5, decimal_places=2)
    total_income = models.DecimalField(max_digits=10, decimal_places=2)
    cycles = models.IntegerField()

    def __str__(self):
        return self.name

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # For buying products
    income = models.DecimalField(max_digits=10, decimal_places=2, default=0)   # For profits/withdrawals
    last_income_update = models.DateTimeField(null=True, blank=True)
    has_recharged = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Wallet"

class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referral')
    referral_code = models.CharField(max_length=12, unique=True, default=uuid.uuid4().hex[:12])
    referrals_count = models.IntegerField(default=0)
    vip_level = models.CharField(max_length=4, default='VIP0')
    invitees = models.ManyToManyField(User, related_name='invited_by', blank=True)

    def __str__(self):
        return f"{self.user.username}'s Referral (Code: {self.referral_code})"

    def increment_referrals(self):
        self.referrals_count += 1
        if self.referrals_count >= 5:
            self.vip_level = 'VIP1'
        elif self.referrals_count >= 10:
            self.vip_level = 'VIP2'
        elif self.referrals_count >= 15:
            self.vip_level = 'VIP3'
        self.save()

class UserProduct(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(default=timezone.now)
    cycles_completed = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('RECHARGE', 'Recharge'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('DEPOSIT', 'Deposit'),
        ('EXCHANGE_REWARD', 'Exchange Reward'),
    )
    TRANSACTION_STATUSES = (
        ('PENDING', 'Pending'),
        ('AWAITING_VERIFICATION', 'Awaiting Verification'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Transaction amount in KES")
    phone_number = models.CharField(max_length=15, blank=True, null=True, help_text="User's phone number for recharge")
    mpesa_receipt = models.CharField(max_length=20, unique=True, blank=True, null=True)
    airtel_transaction_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="Transaction ID from Airtel Money or M-Pesa (e.g., QJ1234567890)"
    )
    checkout_request_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=25,
        choices=TRANSACTION_STATUSES,
        default='PENDING'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='RECHARGE')
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.amount} KSh - {self.status}"

class Recharge(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Failed', 'Failed')], default='Pending')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    transaction = models.OneToOneField('Transaction', on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=150, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.status == 'Completed' and self.transaction and self.transaction.airtel_transaction_id:
            try:
                wallet = Wallet.objects.get(user=self.user)
                old_balance = wallet.balance
                wallet.balance += self.amount
                wallet.has_recharged = True
                wallet.save()
                logger.info(f"Updated wallet for user {self.user.username}: Old balance {old_balance}, New balance {wallet.balance}, Recharge amount {self.amount}")
            except Wallet.DoesNotExist:
                logger.error(f"No wallet found for user {self.user.username}")
            except Exception as e:
                logger.error(f"Error updating wallet for user {self.user.username}: {str(e)}")
        super().save(*args, **kwargs)

class Withdrawal(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Original requested amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Net amount user receives after fee
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    transaction = models.OneToOneField('Transaction', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and self.transaction and self.transaction.airtel_transaction_id:
            try:
                wallet = Wallet.objects.get(user=self.user)
                if wallet.income >= self.requested_amount:  # Check income balance
                    old_income = wallet.income
                    wallet.income -= self.requested_amount
                    wallet.save()
                    logger.info(f"Processed withdrawal for user {self.user.username}: Old income {old_income}, New income {wallet.income}, Requested amount {self.requested_amount}, Fee {self.transaction.fee}, Net amount {self.amount}")
                else:
                    logger.error(f"Insufficient income balance for withdrawal by user {self.user.username}: Requested {self.requested_amount}, Available {wallet.income}")
                    self.status = 'Rejected'
            except Wallet.DoesNotExist:
                logger.error(f"No wallet found for user {self.user.username}")
            except Exception as e:
                logger.error(f"Error processing withdrawal for user {self.user.username}: {str(e)}")
        super().save(*args, **kwargs)

class ExchangeReward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=50, default='Bonus')
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Exchange Reward {self.amount} KSh"

class Deposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Completed', 'Completed'), ('Processing', 'Processing')], default='Processing')
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Deposit {self.amount} KSh"

# Signal to create UserProfile for new users
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)