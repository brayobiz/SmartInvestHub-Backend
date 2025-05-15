from rest_framework import generics, permissions
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView  # Correct import
from .serializers import WalletRechargeSerializer, RechargeSerializer, WithdrawalSerializer, ExchangeRewardSerializer, DepositSerializer, TransactionSerializer
import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Product, Wallet, Referral, UserProduct, Transaction, Recharge, Withdrawal, ExchangeReward, Deposit
from .serializers import UserSerializer, ProductSerializer, WalletSerializer, ReferralSerializer, UserProductSerializer
from django.utils import timezone
from django.db.models import Sum
import uuid

logger = logging.getLogger(__name__)

# Your Airtel Money number for receiving payments
PAYMENT_PHONE_NUMBER = "+254736196188"

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            referral_code = request.data.get('referral_code', '').strip()
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            logger.info(f"User registered: {user.username}")

            # Create or get the user's wallet
            wallet, created = Wallet.objects.get_or_create(user=user)

            # New User Bonus: KSh 200
            new_user_bonus = 200
            wallet.balance += new_user_bonus
            wallet.save()
            transaction = Transaction.objects.create(
                user=user,
                amount=new_user_bonus,
                transaction_type='EXCHANGE_REWARD',
                status='COMPLETED'
            )
            ExchangeReward.objects.create(
                user=user,
                amount=new_user_bonus,
                transaction=transaction,
                type='New User Bonus'
            )
            logger.info(f"New user bonus of {new_user_bonus} KSh credited to {user.username}")

            # Handle Referral Bonus if a valid referral code is provided
            if referral_code:
                try:
                    referrer = Referral.objects.get(referral_code=referral_code)
                    referrer.invitees.add(user)
                    referrer.increment_referrals()
                    logger.info(f"User {user.username} registered with referral code from {referrer.user.username}")

                    # Referral Bonus: KSh 200 for the referrer
                    referral_bonus = 200
                    referrer_wallet, _ = Wallet.objects.get_or_create(user=referrer.user)
                    referrer_wallet.balance += referral_bonus
                    referrer_wallet.save()
                    referrer_transaction = Transaction.objects.create(
                        user=referrer.user,
                        amount=referral_bonus,
                        transaction_type='EXCHANGE_REWARD',
                        status='COMPLETED'
                    )
                    ExchangeReward.objects.create(
                        user=referrer.user,
                        amount=referral_bonus,
                        transaction=referrer_transaction,
                        type='Referral Bonus'
                    )
                    logger.info(f"Referral bonus of {referral_bonus} KSh credited to {referrer.user.username}")
                except Referral.DoesNotExist:
                    logger.warning(f"Invalid referral code provided: {referral_code}")

            return Response({
                'message': 'User registered successfully',
                'token': token.key,
                'user_id': user.id,
                'referral_code': user.referral.referral_code
            }, status=201)
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=400)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]  
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"User {username} logged in successfully")
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
            })
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            return Response({'detail': 'Invalid credentials'}, status=400)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logger.info(f"Logout attempt for user: {request.user.username}")
        try:
            logout(request)
            logger.info(f"User {request.user.username} logged out successfully")
            return Response({'message': 'Logged out'})
        except Exception as e:
            logger.error(f"Logout error for user {request.user.username}: {str(e)}")
            return Response({'error': 'Logout failed'}, status=500)

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Attempt to get phone_number, assuming it might be in a related model or directly on User
            phone_number = getattr(request.user, 'phone_number', '')
            logger.info(f"User profile fetched: username={request.user.username}, phone_number={phone_number}")
            return Response({
                'username': request.user.username,
                'phone_number': phone_number,
                'is_staff': request.user.is_staff,
                'is_superuser': request.user.is_superuser,
            })
        except Exception as e:
            logger.error(f"Error fetching user profile for {request.user.username}: {str(e)}")
            return Response({
                'username': request.user.username,
                'phone_number': '',
                'is_staff': request.user.is_staff,
                'is_superuser': request.user.is_superuser,
            })

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

class WalletView(generics.RetrieveUpdateAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return Wallet.objects.get(user=self.request.user)

class WalletsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            logger.info(f"Wallets endpoint accessed - Wallet retrieved for user: {request.user.username}")
            return Response(WalletSerializer(wallet).data)
        except Exception as e:
            logger.error(f"Error retrieving wallet for user {request.user.username}: {str(e)}")
            return Response({'error': 'Failed to retrieve wallet'}, status=500)

class RechargeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logger.info(f"Recharge request initiated for user: {request.user.username}")
        serializer = WalletRechargeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                wallet = Wallet.objects.get(user=request.user)
                amount = serializer.validated_data['amount']
                phone_number = serializer.validated_data.get('phone_number', '')

                # Validate amount
                if amount <= 0:
                    logger.error(f"Invalid recharge amount for user {request.user.username}: {amount}")
                    return Response({'error': 'Amount must be greater than 0'}, status=400)

                # Create a pending transaction
                transaction = Transaction.objects.create(
                    user=request.user,
                    amount=amount,
                    phone_number=phone_number,
                    transaction_type='RECHARGE',
                    status='PENDING'
                )

                # Create a recharge entry with pre-filled username
                recharge = Recharge.objects.create(
                    user=request.user,
                    amount=amount,
                    transaction=transaction,
                    status='Pending',
                    username=request.user.username
                )

                logger.info(f"Recharge request created for user {request.user.username}: {amount} KSh, Transaction ID: {transaction.id}")
                return Response({
                    'message': f'Please send KES {amount} to Airtel Money number {PAYMENT_PHONE_NUMBER}. After payment, send the full transaction confirmation message to {PAYMENT_PHONE_NUMBER} on WhatsApp.',
                    'transaction_id': recharge.id,  # Use recharge ID for polling
                    'status': recharge.status
                }, status=201)
            except Exception as e:
                logger.error(f"Error creating recharge request for user {request.user.username}: {str(e)}", exc_info=True)
                return Response({'error': 'Internal server error'}, status=500)
        logger.error(f"Invalid recharge data: {serializer.errors}")
        return Response(serializer.errors, status=400)

class RechargeStatusView(APIView):  # Fixed: ApiView -> APIView
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):  # Use pk instead of transaction_id for clarity
        try:
            recharge = Recharge.objects.get(id=pk, user=request.user)
            serializer = RechargeStatusSerializer(recharge)
            return Response(serializer.data)
        except Recharge.DoesNotExist:
            logger.error(f"Recharge not found for user {request.user.username}: Recharge ID {pk}")
            return Response({'error': 'Recharge not found'}, status=404)
        except Exception as e:
            logger.error(f"Error checking recharge status for user {request.user.username}: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)

class PaymentInstructionsView(APIView):  # Fixed: ApiView -> APIView
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        logger.info(f"Payment instructions requested for user: {request.user.username}")
        return Response({
            'message': 'Please send the recharge amount to the following Airtel Money number and await admin verification.',
            'phone_number': PAYMENT_PHONE_NUMBER,
            'instructions': (
                '1. Open your Airtel Money or M-Pesa app.\n'
                '2. Select "Send Money".\n'
                '3. Enter the Airtel number above.\n'
                '4. Enter the amount.\n'
                '5. Complete the transaction and note the transaction ID (e.g., QJ1234567890).\n'
                '6. Wait for an admin to verify your payment.'
            )
        })

class UpdateIncomeView(APIView):  # Fixed: ApiView -> APIView
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        wallet = Wallet.objects.get(user=request.user)
        user_products = UserProduct.objects.filter(user=request.user, active=True)
        today = timezone.now()
        twenty_four_hours_ago = today - timezone.timedelta(hours=24)

        # Check if 24 hours have passed since the last update
        if wallet.last_income_update and wallet.last_income_update > twenty_four_hours_ago:
            logger.info(f"No income update for {request.user.username}: Less than 24 hours since last update.")
            return Response(WalletSerializer(wallet).data)

        # Update income for each active product
        for user_product in user_products:
            days_since_purchase = (today.date() - user_product.purchase_date.date()).days
            if days_since_purchase <= user_product.product.cycles and user_product.cycles_completed < user_product.product.cycles:
                wallet.income += user_product.product.daily_income
                user_product.cycles_completed += 1
                if user_product.cycles_completed >= user_product.product.cycles:
                    user_product.active = False
                user_product.save()

        # Update the last income update timestamp
        wallet.last_income_update = today
        wallet.save()
        logger.info(f"Income updated for {request.user.username}: {wallet.income} KSh")
        return Response(WalletSerializer(wallet).data)

class WithdrawalView(APIView):  # Fixed: ApiView -> APIView
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            amount = float(request.data.get('amount'))
            phone_number = request.data.get('phone_number')
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=400)

            # Calculate withdrawal fee based on tiered structure
            fee = 0
            if 1 <= amount <= 1000:
                fee = max(5, min(50, amount * 0.05))  # 5% fee, capped between 5 and 50 KSh
            elif amount > 1000:
                fee = amount * 0.10  # 10% fee for amounts above 1000 KSh

            net_amount = amount - fee  # Amount the user receives after fee deduction

            wallet = Wallet.objects.get(user=request.user)
            if wallet.balance < amount:  # Check against the requested amount
                return Response({'error': f'Insufficient balance'}, status=400)

            transaction = Transaction.objects.create(
                user=request.user,
                amount=net_amount,  # Record the net amount the user receives
                phone_number=phone_number,
                transaction_type='WITHDRAWAL',
                status='PENDING',
                fee=fee  # Store the fee in the Transaction model
            )
            withdrawal = Withdrawal.objects.create(
                user=request.user,
                requested_amount=amount,  # Store the original requested amount
                amount=net_amount,  # Store the net amount in Withdrawal
                phone_number=phone_number,
                transaction=transaction
            )
            serializer = WithdrawalSerializer(withdrawal)
            logger.info(f"Withdrawal request created for user {request.user.username}: Requested {amount} KSh, Fee {fee} KSh, Net Amount {net_amount} KSh")
            return Response({
                'message': f'Withdrawal request submitted. Requested: {amount} KSh, Fee: {fee} KSh, You will receive: {net_amount} KSh',
                'data': serializer.data
            }, status=201)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=400)
        except Wallet.DoesNotExist:
            logger.error(f"No wallet found for user {request.user.username}")
            return Response({'error': 'Wallet not found'}, status=404)
        except Exception as e:
            logger.error(f"Error creating withdrawal for user {request.user.username}: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)

class WalletsPurchaseView(APIView):  # Fixed: ApiView -> APIView
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            if not product_id:
                return Response({'error': 'Product ID is required'}, status=400)

            product = Product.objects.get(id=product_id)
            wallet = Wallet.objects.get(user=request.user)

            if wallet.balance < product.price:
                return Response({'error': 'Insufficient wallet balance'}, status=400)

            wallet.balance -= product.price
            wallet.save()

            UserProduct.objects.create(
                user=request.user,
                product=product,
                cycles_completed=0,
                active=True
            )

            logger.info(f"Product {product.name} purchased by {request.user.username} using wallet")
            return Response({'balance': wallet.balance}, status=200)
        except Product.DoesNotExist:
            logger.error(f"Product not found for id: {product_id}")
            return Response({'error': 'Product not found'}, status=404)
        except Wallet.DoesNotExist:
            logger.error(f"Wallet not found for user: {request.user.username}")
            return Response({'error': 'Wallet not found'}, status=404)
        except Exception as e:
            logger.error(f"Purchase error for user {request.user.username}: {str(e)}")
            return Response({'error': 'Purchase failed'}, status=500)

class ReferralClaimView(APIView):  # Fixed: ApiView -> APIView
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            referral = Referral.objects.get(user=request.user)
            if referral.vip_level == 'VIP0':
                return Response({'error': 'No rewards available to claim.'}, status=400)

            wallet, created = Wallet.objects.get_or_create(user=request.user)
            amount = 0
            message = ''
            if referral.vip_level == 'VIP1':
                amount = 500
                message = '500 KSh added to your wallet.'
            elif referral.vip_level == 'VIP2':
                amount = 1000
                message = '1000 KSh added to your wallet and 5% extra daily income applied.'
            elif referral.vip_level == 'VIP3':
                amount = 2000
                message = '2000 KSh added to your wallet and 10% extra daily income applied.'

            if amount > 0:
                wallet.balance += amount
                wallet.save()
                transaction = Transaction.objects.create(
                    user=request.user,
                    amount=amount,
                    transaction_type='EXCHANGE_REWARD',
                    status='COMPLETED'
                )
                ExchangeReward.objects.create(user=request.user, amount=amount, transaction=transaction)

            logger.info(f"Reward claimed by {request.user.username}: {message}")
            return Response({'message': message, 'balance': wallet.balance}, status=200)
        except Referral.DoesNotExist:
            logger.error(f"No referral found for user: {request.user.username}")
            return Response({'error': 'Referral not found.'}, status=404)
        except Exception as e:
            logger.error(f"Error claiming reward for {request.user.username}: {str(e)}")
            return Response({'error': 'Failed to claim reward.'}, status=500)

class StatisticsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user)
            transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')[:3]
            trend = [
                {
                    'date': t.timestamp.strftime('%Y-%m-%d'),
                    'balance': wallet.balance,
                    'income': wallet.income
                } for t in transactions
            ]
            return Response({'trend': trend})
        except Wallet.DoesNotExist:
            logger.error(f"No wallet found for user: {request.user.username}")
            return Response({'error': 'Wallet not found'}, status=404)

class FundingDetailsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RechargeSerializer

    def get_queryset(self):
        return Recharge.objects.filter(user=self.request.user).order_by('-date')

class WithdrawalHistoryView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawalSerializer

    def get_queryset(self):
        return Withdrawal.objects.filter(user=self.request.user).order_by('-date')

class ExchangeRewardsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExchangeRewardSerializer

    def get_queryset(self):
        return ExchangeReward.objects.filter(user=self.request.user).order_by('-date')

class DepositStatusView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DepositSerializer

    def get_queryset(self):
        return Deposit.objects.filter(user=self.request.user).order_by('-date')

# Add UserProductView here
class UserProductView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProductSerializer

    def get_queryset(self):
        return UserProduct.objects.filter(user=self.request.user).order_by('-purchase_date')

class ReferralView(generics.RetrieveAPIView):
    serializer_class = ReferralSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            referral, created = Referral.objects.get_or_create(user=request.user)
            if created:
                logger.info(f"Created new referral for user: {request.user.username}")
            serializer = self.get_serializer(referral)
            logger.info(f"Referral fetched for user: {request.user.username}")
            return Response([serializer.data])
        except Exception as e:
            logger.error(f"Error fetching referral for user {request.user.username}: {str(e)}")
            return Response([{'referral_code': '', 'vip_level': 'VIP0', 'referrals_count': 0}])

class AdminDashboardView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        # Aggregate stats
        total_recharges = Transaction.objects.filter(transaction_type='RECHARGE', status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0
        total_withdrawals = Transaction.objects.filter(transaction_type='WITHDRAWAL', status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0
        active_users = User.objects.filter(is_active=True).count()

        # Recent activities (last 10 transactions)
        activities = Transaction.objects.select_related('user').filter(status='COMPLETED').order_by('-timestamp')[:10]
        activities_data = TransactionSerializer(activities, many=True).data

        # Pending alerts
        pending_recharges = Recharge.objects.filter(status='Pending').select_related('user', 'transaction').values(
            'id', 'user__username', 'amount', 'date', 'transaction__airtel_transaction_id'
        )
        pending_withdrawals = Withdrawal.objects.filter(status='Pending').select_related('user', 'transaction').values(
            'id', 'user__username', 'amount', 'date', 'transaction__airtel_transaction_id'
        )

        # Users list
        users = User.objects.all().values('id', 'username', 'email', 'is_staff', 'is_superuser', 'is_active')

        return Response({
            'stats': {
                'totalRecharges': float(total_recharges),
                'totalWithdrawals': float(total_withdrawals),
                'activeUsers': active_users
            },
            'activities': activities_data,
            'users': list(users),
            'alerts': {
                'pendingRecharges': list(pending_recharges),
                'pendingWithdrawals': list(pending_withdrawals)
            }
        })

    def post(self, request):
        # Handle user updates (e.g., toggle is_staff, is_superuser, is_active)
        user_id = request.data.get('user_id')
        action = request.data.get('action')

        try:
            user = User.objects.get(id=user_id)
            if action == 'toggle_staff':
                user.is_staff = not user.is_staff
                logger.info(f"Admin {request.user.username} toggled is_staff for {user.username} to {user.is_staff}")
            elif action == 'toggle_superuser':
                user.is_superuser = not user.is_superuser
                logger.info(f"Admin {request.user.username} toggled is_superuser for {user.username} to {user.is_superuser}")
            elif action == 'toggle_active':
                user.is_active = not user.is_active
                logger.info(f"Admin {request.user.username} toggled is_active for {user.username} to {user.is_active}")
            user.save()
            return Response({'message': f'User {user.username} updated successfully', 'user': {
                'id': user.id,
                'username': user.username,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active,
            }})
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found by admin {request.user.username}")
            return Response({'error': 'User not found'}, status=404)
        except Exception as e:
            logger.error(f"Error updating user by admin {request.user.username}: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)

class AdminApproveTransactionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        type = request.data.get('type')  # 'pendingRecharges' or 'pendingWithdrawals'
        id = request.data.get('id')
        status = request.data.get('status')  # 'COMPLETED' or 'REJECTED'

        try:
            if type == 'pendingRecharges':
                recharge = Recharge.objects.get(id=id)
                transaction = recharge.transaction
                if status == 'COMPLETED':
                    recharge.status = 'Completed'
                    transaction.status = 'COMPLETED'
                    wallet = Wallet.objects.get(user=recharge.user)
                    wallet.balance += recharge.amount
                    wallet.save()
                    logger.info(f"Admin {request.user.username} approved recharge {id} for {recharge.user.username}")
                else:  # REJECTED
                    recharge.status = 'Rejected'
                    transaction.status = 'REJECTED'
                    logger.info(f"Admin {request.user.username} rejected recharge {id} for {recharge.user.username}")
                recharge.save()
                transaction.save()
            elif type == 'pendingWithdrawals':
                withdrawal = Withdrawal.objects.get(id=id)
                transaction = withdrawal.transaction
                if status == 'COMPLETED':
                    withdrawal.transaction.status = 'COMPLETED'
                    logger.info(f"Admin {request.user.username} approved withdrawal {id} for {withdrawal.user.username}")
                else:  # REJECTED
                    withdrawal.transaction.status = 'REJECTED'
                    wallet = Wallet.objects.get(user=withdrawal.user)
                    wallet.balance += withdrawal.amount  # Refund the amount
                    wallet.save()
                    logger.info(f"Admin {request.user.username} rejected withdrawal {id} for {withdrawal.user.username}")
                withdrawal.transaction.save()
            return Response({'message': f'{type} {id} updated to {status}'})
        except (Recharge.DoesNotExist, Withdrawal.DoesNotExist):
            logger.error(f"Transaction {id} of type {type} not found by admin {request.user.username}")
            return Response({'error': 'Transaction not found'}, status=404)
        except Exception as e:
            logger.error(f"Error processing transaction {id} by admin {request.user.username}: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)
