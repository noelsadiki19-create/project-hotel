import requests
import json
from django.conf import settings

class SMSNotification:
    """
    SMS Notification service for sending messages to customers
    Supports multiple SMS providers: Africastalking, HTTP endpoint
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'SMS_API_KEY', '')
        self.sender_id = getattr(settings, 'SMS_SENDER_ID', 'MAISON')
        self.provider = getattr(settings, 'SMS_PROVIDER', 'http')  # 'africastalking' or 'http'
        self.sms_endpoint = getattr(settings, 'SMS_ENDPOINT', '')
    
    def send_payment_confirmation(self, phone_number, order_id, amount, status='success'):
        """
        Send payment confirmation SMS to customer
        """
        if status == 'success':
            message = f"Payment Confirmed! Order #{order_id} - KS{amount} received. Thank you for using MAISON ROYALE BRALMOS. Your order is being prepared."
        else:
            message = f"Payment Failed! Order #{order_id} - KS{amount}. Please retry or contact support. Ref: {order_id}"
        
        return self.send_sms(phone_number, message)
    
    def send_order_status_update(self, phone_number, order_id, status):
        """
        Send order status update SMS to customer
        """
        status_messages = {
            'pending': f"Order #{order_id} is pending confirmation. We will notify you when it's confirmed.",
            'confirmed': f"Order #{order_id} confirmed! Your order is being prepared. Est. time: 30-45 mins.",
            'preparing': f"Order #{order_id} is being prepared. Get ready for collection/delivery soon!",
            'ready': f"Order #{order_id} is READY! Come collect your order at MAISON ROYALE BRALMOS.",
            'completed': f"Order #{order_id} completed successfully! Thank you for dining with us. Visit again!",
            'cancelled': f"Order #{order_id} has been cancelled. Contact us if you have questions."
        }
        
        message = status_messages.get(status, f"Order #{order_id} status: {status}")
        return self.send_sms(phone_number, message)
    
    def send_booking_confirmation(self, phone_number, booking_id, booking_date, booking_time, guests):
        """
        Send table booking confirmation SMS to customer
        """
        time_str = f"at {booking_time.strftime('%H:%M')}" if booking_time else ""
        message = f"Booking Confirmed! Ref #{booking_id} - {guests} guests on {booking_date} {time_str}. MAISON ROYALE BRALMOS. Call: +254XXX for changes."
        
        return self.send_sms(phone_number, message)
    
    def send_sms(self, phone_number, message):
        """
        Send SMS using configured provider
        """
        try:
            # Format phone number to international format if needed
            formatted_phone = self._format_phone_number(phone_number)
            
            if self.provider == 'africastalking':
                return self._send_via_africastalking(formatted_phone, message)
            else:
                return self._send_via_http(formatted_phone, message)
        
        except Exception as e:
            print(f"Error sending SMS: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _format_phone_number(self, phone_number):
        """
        Format phone number to international format (254xxxxxxxxx)
        """
        phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # If starts with 0 (local Kenyan format), replace with 254
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        # If local format without 0, add 254
        elif not phone.startswith('254') and len(phone) == 9:
            phone = '254' + phone
        
        return phone
    
    def _send_via_africastalking(self, phone_number, message):
        """
        Send SMS via Africastalking API
        """
        if not self.api_key:
            return {'success': False, 'error': 'Africastalking API key not configured'}
        
        try:
            url = "https://api.sandbox.africastalking.com/version1/messaging"
            
            headers = {
                'Accept': 'application/json',
                'Content-type': 'application/x-www-form-urlencoded',
                'apiKey': self.api_key,
            }
            
            payload = {
                'username': 'sandbox',  # Use 'sandbox' for testing
                'to': f'+{phone_number}',
                'message': message,
            }
            
            response = requests.post(url, headers=headers, data=payload, timeout=10)
            result = response.json()
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'provider': 'africastalking',
                    'phone': phone_number,
                    'message': message
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'provider': 'africastalking'
                }
        
        except Exception as e:
            print(f"Africastalking error: {str(e)}")
            return {'success': False, 'error': str(e), 'provider': 'africastalking'}
    
    def _send_via_http(self, phone_number, message):
        """
        Send SMS via HTTP endpoint (generic SMS gateway)
        """
        if not self.sms_endpoint:
            print(f"[SMS NOTIFICATION] Phone: +{phone_number} | Message: {message}")
            return {
                'success': True,
                'provider': 'console',
                'phone': phone_number,
                'message': message,
                'note': 'SMS printed to console - configure SMS_ENDPOINT for actual sending'
            }
        
        try:
            payload = {
                'api_key': self.api_key,
                'phone': phone_number,
                'message': message,
                'sender_id': self.sender_id,
            }
            
            response = requests.post(self.sms_endpoint, json=payload, timeout=10)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'provider': 'http',
                    'phone': phone_number,
                    'message': message
                }
            else:
                return {
                    'success': False,
                    'error': 'HTTP request failed',
                    'provider': 'http',
                    'status_code': response.status_code
                }
        
        except Exception as e:
            print(f"HTTP SMS error: {str(e)}")
            return {'success': False, 'error': str(e), 'provider': 'http'}


# Convenience function
def send_payment_sms(phone, order_id, amount, status='success'):
    """Send payment confirmation SMS"""
    sms = SMSNotification()
    return sms.send_payment_confirmation(phone, order_id, amount, status)


def send_order_sms(phone, order_id, status):
    """Send order status update SMS"""
    sms = SMSNotification()
    return sms.send_order_status_update(phone, order_id, status)


def send_booking_sms(phone, booking_id, booking_date, booking_time, guests):
    """Send booking confirmation SMS"""
    sms = SMSNotification()
    return sms.send_booking_confirmation(phone, booking_id, booking_date, booking_time, guests)
