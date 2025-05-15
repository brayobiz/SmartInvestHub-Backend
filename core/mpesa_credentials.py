# core/mpesa_credentials.py
class MpesaCredentials:
    CONSUMER_KEY = "YOUR_CONSUMER_KEY"  # Replace with Safaricom API Consumer Key
    CONSUMER_SECRET = "YOUR_CONSUMER_SECRET"  # Replace with Safaricom API Consumer Secret
    SHORTCODE = "YOUR_SHORTCODE"  # Replace with your registered shortcode
    PASSKEY = "YOUR_PASSKEY"  # Replace with your passkey

    @classmethod
    def get_access_token(cls):
        # Simulate token fetching (replace with actual API call)
        return "SIMULATED_ACCESS_TOKEN"  # Replace with real token logic

    @classmethod
    def get_password(cls):
        # Simulate password generation (replace with actual logic)
        return "SIMULATED_PASSWORD", timezone.now().strftime('%Y%m%d%H%M%S')