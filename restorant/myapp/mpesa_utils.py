import requests
import json
from django.conf import settings
from datetime import datetime
import base64

class MpesaAPI:
    """
    M-Pesa API integration using Daraja API
    """
    
    # API URLs
    AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    STK_PUSH_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    BALANCE_URL = "https://sandbox.safaricom.co.ke/mpesa/accountbalance/v1/query"
    TRANSACTION_STATUS_URL = "https://sandbox.safaricom.co.ke/mpesa/transactionstatus/v1/query"
    
    def __init__(self):
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.business_short_code = getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', '')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        self.access_token = None
    
    def get_access_token(self):
        """Get access token from M-Pesa API"""
        try:
            response = requests.get(
                self.AUTH_URL,
                auth=(self.consumer_key, self.consumer_secret),
                timeout=10
            )
            
            if response.status_code == 200:
                self.access_token = response.json()['access_token']
                return self.access_token
            else:
                print(f"Error getting access token: {response.text}")
                return None
        except Exception as e:
            print(f"Exception in get_access_token: {str(e)}")
            return None
    
    def initiate_stk_push(self, phone_number, amount, order_id):
        """
        Initiate STK Push for payment
        """
        try:
            # Get access token
            token = self.get_access_token()
            if not token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            # Prepare STK Push request
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Create password (Base64 encoded)
            password_str = f"{self.business_short_code}{self.passkey}{timestamp}"
            password = base64.b64encode(password_str.encode()).decode()
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "BusinessShortCode": self.business_short_code,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": str(int(amount)),  # Amount must be integer
                "PartyA": phone_number,  # Customer phone number
                "PartyB": self.business_short_code,  # Business short code
                "PhoneNumber": phone_number,
                "CallBackURL": self.callback_url,
                "AccountReference": f"Order-{order_id}",
                "TransactionDesc": f"Restaurant Order #{order_id}"
            }
            
            response = requests.post(
                self.STK_PUSH_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'message': result.get('ResponseDescription')
                }
            else:
                error_msg = result.get('ResponseDescription', 'Unknown error')
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            print(f"Exception in initiate_stk_push: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_transaction_status(self, checkout_request_id):
        """
        Check transaction status
        """
        try:
            token = self.get_access_token()
            if not token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password_str = f"{self.business_short_code}{self.passkey}{timestamp}"
            password = base64.b64encode(password_str.encode()).decode()
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "BusinessShortCode": self.business_short_code,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            response = requests.post(
                self.TRANSACTION_STATUS_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            return result
            
        except Exception as e:
            print(f"Exception in check_transaction_status: {str(e)}")
            return {'success': False, 'error': str(e)}


def process_payment_callback(request_data):
    """
    Process M-Pesa payment callback
    """
    try:
        if 'Body' not in request_data:
            return False
        
        result = request_data['Body']['stkCallback']
        result_code = result.get('ResultCode', 1)
        
        if result_code == 0:  # Success
            checkout_request_id = result.get('CheckoutRequestID')
            merchant_request_id = result.get('MerchantRequestID')
            callback_metadata = result.get('CallbackMetadata', {})
            
            # Extract metadata
            items = callback_metadata.get('Item', [])
            metadata = {}
            for item in items:
                name = item.get('Name')
                value = item.get('Value')
                if name:
                    metadata[name] = value
            
            return {
                'success': True,
                'checkout_request_id': checkout_request_id,
                'merchant_request_id': merchant_request_id,
                'metadata': metadata,
                'amount': metadata.get('Amount'),
                'receipt_number': metadata.get('MpesaReceiptNumber'),
                'transaction_date': metadata.get('TransactionDate'),
                'phone_number': metadata.get('PhoneNumber')
            }
        else:
            return {
                'success': False,
                'error': 'Payment failed',
                'result_code': result_code
            }
    except Exception as e:
        print(f"Exception in process_payment_callback: {str(e)}")
        return {'success': False, 'error': str(e)}
