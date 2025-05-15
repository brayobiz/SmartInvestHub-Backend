from rest_framework import serializers
from .models import Product, Wallet, Referral, UserProduct, UserProfile, Recharge, Withdrawal, ExchangeReward, Deposit, Transaction
from django.contrib.auth.models import User

# Serializer for nesting user data (used in ReferralSerializer for invitees)
class UserSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='profile.phone_number', read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'phone_number']

# Serializer for UserProfile (used for phone_number in MyPage.js or other views)
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['phone_number']

# Serializer for user registration
class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(max_length=15, required=True, allow_blank=False)  # Add phone_number field

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'phone_number']

    def create(self, validated_data):
        phone_number = validated_data.pop('phone_number')  # Remove phone_number from validated_data
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        # Create or update UserProfile with the phone number
        UserProfile.objects.update_or_create(user=user, defaults={'phone_number': phone_number})
        return user

# Serializer for Product model
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'cost', 'price', 'daily_income', 'return_rate', 'total_income', 'cycles']

# Serializer for Wallet model
class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance', 'income', 'last_income_update', 'has_recharged']

# Serializer for wallet recharge operations
class WalletRechargeSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)

    class Meta:
        fields = ['amount', 'phone_number']

# Serializer for Referral model (includes nested invitees with usernames)
class ReferralSerializer(serializers.ModelSerializer):
    invitees = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Referral
        fields = ['referral_code', 'referrals_count', 'vip_level', 'invitees']

# Serializer for UserProduct model (includes nested product details)
class UserProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = UserProduct
        fields = ['id', 'product', 'purchase_date', 'cycles_completed', 'active']

# Serializer for Transaction model (used in RechargeSerializer)
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'phone_number', 'airtel_transaction_id', 'timestamp', 'status', 'transaction_type']

# Serializer for Recharge model
class RechargeSerializer(serializers.ModelSerializer):
    transaction = TransactionSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Recharge
        fields = ['id', 'user', 'amount', 'date', 'status', 'transaction', 'username']
        read_only_fields = ['id', 'user', 'date', 'status', 'transaction', 'username']

# Serializer for Recharge status (for polling)
class RechargeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recharge
        fields = ['status']

# Serializer for Withdrawal model
class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ['id', 'requested_amount', 'amount', 'date', 'status', 'phone_number', 'transaction']

# Serializer for ExchangeReward model
class ExchangeRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeReward
        fields = ['id', 'amount', 'date', 'type']

# Serializer for Deposit model
class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ['id', 'amount', 'date', 'status']
        
class RechargeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recharge
        fields = ['status']