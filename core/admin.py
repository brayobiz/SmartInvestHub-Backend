from django.contrib import admin
from django.contrib import messages
from django import forms
from .models import UserProfile, Product, Wallet, Referral, UserProduct, Transaction, Recharge, Withdrawal, ExchangeReward, Deposit

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'cost', 'price', 'daily_income', 'total_income', 'cycles')
    search_fields = ('name',)

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'income', 'has_recharged', 'last_income_update')
    search_fields = ('user__username',)

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('user', 'referral_code', 'referrals_count', 'vip_level')
    search_fields = ('user__username', 'referral_code')

@admin.register(UserProduct)
class UserProductAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'purchase_date', 'cycles_completed', 'active')
    search_fields = ('user__username', 'product__name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'get_phone_number', 'airtel_transaction_id', 'status', 'transaction_type', 'timestamp')
    list_filter = ('transaction_type', 'status')
    search_fields = ('user__username', 'airtel_transaction_id', 'phone_number')

    class TransactionAdminForm(forms.ModelForm):
        class Meta:
            model = Transaction
            fields = '__all__'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if 'user' in self.initial:
                user = self.initial['user']
                try:
                    profile = user.profile
                    self.initial['phone_number'] = profile.phone_number or ''
                except (UserProfile.DoesNotExist, AttributeError):
                    self.initial['phone_number'] = ''
            # Update phone_number when user changes
            if self.instance and self.instance.user:
                try:
                    profile = self.instance.user.profile
                    if not self.initial.get('phone_number'):
                        self.initial['phone_number'] = profile.phone_number or ''
                except (UserProfile.DoesNotExist, AttributeError):
                    pass

    form = TransactionAdminForm

    def get_phone_number(self, obj):
        """Return the phone number from Transaction or UserProfile if available."""
        if obj.phone_number:
            return obj.phone_number
        try:
            return obj.user.profile.phone_number or 'Not set'
        except UserProfile.DoesNotExist:
            return 'Not set'
    get_phone_number.short_description = 'Phone Number'

    # Optional action to assist with verification (manual trigger)
    def verify_transaction(self, request, queryset):
        for transaction in queryset.filter(status='PENDING', transaction_type='RECHARGE'):
            try:
                recharge = Recharge.objects.get(transaction=transaction)
                if not transaction.airtel_transaction_id:
                    self.message_user(
                        request,
                        f"Transaction for {transaction.user.username} (ID: {transaction.id}) is missing the Airtel/M-Pesa transaction ID. Please edit the transaction and add it.",
                        level='error'
                    )
                    continue
                # No automatic update here; let the Recharge save method handle it
                self.message_user(
                    request,
                    f"Transaction for {transaction.user.username} (ID: {transaction.id}) is ready for manual verification in the Recharge section.",
                    level='info'
                )
            except Recharge.DoesNotExist:
                self.message_user(
                    request,
                    f"No recharge record found for transaction {transaction.id}.",
                    level='error'
                )
    verify_transaction.short_description = "Mark transactions as ready for verification"
    actions = ['verify_transaction']  # Replace the old action with this one

@admin.register(Recharge)
class RechargeAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'date', 'status', 'username', 'get_phone_number', 'get_airtel_transaction_id')
    list_filter = ('status',)
    search_fields = ('user__username', 'username')

    def get_phone_number(self, obj):
        try:
            transaction = obj.transaction
            if transaction and transaction.phone_number:
                return transaction.phone_number
            return obj.user.profile.phone_number or 'Not set'
        except (Transaction.DoesNotExist, UserProfile.DoesNotExist):
            return 'Not set'
    get_phone_number.short_description = 'Phone Number'

    def get_airtel_transaction_id(self, obj):
        try:
            return obj.transaction.airtel_transaction_id if obj.transaction else 'Not set'
        except Transaction.DoesNotExist:
            return 'Not set'
    get_airtel_transaction_id.short_description = 'Airtel Transaction ID'

    def save_model(self, request, obj, form, change):
        # When saving in the admin panel, ensure the transaction's airtel_transaction_id is set before completing
        if 'status' in form.changed_data and obj.status == 'Completed' and obj.transaction:
            if not obj.transaction.airtel_transaction_id:
                self.message_user(request, "Please enter an Airtel Transaction ID in the associated Transaction before setting the status to Completed.", level='error')
                obj.status = 'Pending'  # Revert to Pending if no airtel_transaction_id
                return
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'transaction':
            kwargs['queryset'] = Transaction.objects.filter(transaction_type='RECHARGE')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'date', 'status', 'get_phone_number')
    list_filter = ('status',)
    search_fields = ('user__username',)

    def get_phone_number(self, obj):
        try:
            transaction = obj.transaction
            if transaction and transaction.phone_number:
                return transaction.phone_number
            return obj.user.profile.phone_number or 'Not set'
        except (Transaction.DoesNotExist, UserProfile.DoesNotExist):
            return 'Not set'
    get_phone_number.short_description = 'Phone Number'

    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data and obj.status == 'Approved' and obj.transaction:
            if not obj.transaction.airtel_transaction_id:
                self.message_user(request, "Please enter an Airtel Transaction ID in the associated Transaction before approving.", level='error')
                obj.status = 'Pending'
                return
        super().save_model(request, obj, form, change)

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'date', 'status', 'get_phone_number')
    list_filter = ('status',)
    search_fields = ('user__username',)

    def get_phone_number(self, obj):
        try:
            transaction = obj.transaction
            if transaction and transaction.phone_number:
                return transaction.phone_number
            return obj.user.profile.phone_number or 'Not set'
        except (Transaction.DoesNotExist, UserProfile.DoesNotExist):
            return 'Not set'
    get_phone_number.short_description = 'Phone Number'

@admin.register(ExchangeReward)
class ExchangeRewardAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'date', 'type')
    search_fields = ('user__username',)