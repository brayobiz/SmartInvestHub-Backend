from django.urls import path, re_path
from django.http import HttpResponseRedirect
from .views import (
    UserProfileView, LoginView, LogoutView, RegisterView, ProductListView, WalletView, ReferralView,
    UserProductView, UpdateIncomeView, RechargeView, RechargeStatusView, WithdrawalView, WalletsView,
    WalletsPurchaseView, ReferralClaimView, StatisticsView, FundingDetailsView, WithdrawalHistoryView,
    ExchangeRewardsView, DepositStatusView, PaymentInstructionsView,
    AdminDashboardView, AdminApproveTransactionView,  # Added new views
)

urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    re_path(r'^api/referral/(?P<referral_code>[a-zA-Z0-9]+)/$',
            lambda request, referral_code: HttpResponseRedirect(f'/register/?referral_code={referral_code}'),
            name='referral-link'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/user-profile/', UserProfileView.as_view(), name='user-profile'),
    path('api/products/', ProductListView.as_view(), name='products'),
    path('api/wallet/', WalletView.as_view(), name='wallet'),
    path('api/wallets/', WalletsView.as_view(), name='wallets'),
    path('api/recharge/', RechargeView.as_view(), name='recharge'),
    path('api/recharge-status/<int:pk>/', RechargeStatusView.as_view(), name='recharge-status'),
    path('api/wallets/purchase/', WalletsPurchaseView.as_view(), name='wallets-purchase'),
    path('api/referral/', ReferralView.as_view(), name='referral'),
    path('api/referral/claim/', ReferralClaimView.as_view(), name='referral-claim'),
    path('api/user-products/', UserProductView.as_view(), name='user-products'),
    path('api/update-income/', UpdateIncomeView.as_view(), name='update-income'),
    path('api/wallets/withdraw/', WithdrawalView.as_view(), name='withdraw'),
    path('api/statistics/', StatisticsView.as_view(), name='statistics'),
    path('api/funding-details/', FundingDetailsView.as_view(), name='funding-details'),
    path('api/withdrawal-history/', WithdrawalHistoryView.as_view(), name='withdrawal-history'),
    path('api/exchange-rewards/', ExchangeRewardsView.as_view(), name='exchange-rewards'),
    path('api/deposit-status/', DepositStatusView.as_view(), name='deposit-status'),
    path('api/payment-instructions/', PaymentInstructionsView.as_view(), name='payment-instructions'),
    path('api/admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),  # Added
    path('api/admin/approve-transaction/', AdminApproveTransactionView.as_view(), name='admin_approve_transaction'),  # Added
]