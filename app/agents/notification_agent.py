from typing import Dict, Any
import uuid
import asyncio
from datetime import datetime

from app.agents.base import BaseAgent


class NotificationAgent(BaseAgent):
    """
    Agent for sending notifications across multiple channels.
    
    Supports email, SMS, push notifications, webhooks, etc.
    """
    
    def __init__(self):
        super().__init__("notification")
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate notification input."""
        required_fields = ["channel", "message"]
        
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"Missing required field: {field}")
        
        valid_channels = ["email", "sms", "push", "webhook", "slack", "teams"]
        if input_data["channel"] not in valid_channels:
            raise ValueError(f"Invalid channel. Must be one of: {valid_channels}")
        
        return True
    
    async def execute(
        self, 
        task_id: uuid.UUID,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute notification task."""
        await self.pre_execute(task_id, input_data)
        
        try:
            await self.validate_input(input_data)
            
            channel = input_data["channel"]
            
            # Route to appropriate channel handler
            if channel == "email":
                result = await self._send_email_notification(input_data)
            elif channel == "sms":
                result = await self._send_sms_notification(input_data)
            elif channel == "push":
                result = await self._send_push_notification(input_data)
            elif channel == "webhook":
                result = await self._send_webhook_notification(input_data)
            elif channel == "slack":
                result = await self._send_slack_notification(input_data)
            elif channel == "teams":
                result = await self._send_teams_notification(input_data)
            else:
                raise ValueError(f"Unsupported channel: {channel}")
            
            await self.post_execute(task_id, result, success=True)
            return result
            
        except Exception as e:
            error_result = await self.handle_error(task_id, e)
            await self.post_execute(task_id, error_result, success=False)
            raise
    
    async def _send_email_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email notification."""
        await asyncio.sleep(0.8)
        
        recipients = input_data.get("recipients", [])
        subject = input_data.get("subject", "Notification")
        message = input_data["message"]
        
        self.logger.info(f"Sending email notification to {len(recipients)} recipients")
        
        return {
            "success": True,
            "channel": "email",
            "recipients_count": len(recipients),
            "message_ids": [f"email_{uuid.uuid4().hex[:10]}" for _ in recipients],
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def _send_sms_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS notification."""
        await asyncio.sleep(0.5)
        
        phone_numbers = input_data.get("phone_numbers", [])
        message = input_data["message"]
        
        return {
            "success": True,
            "channel": "sms",
            "recipients_count": len(phone_numbers),
            "message_ids": [f"sms_{uuid.uuid4().hex[:10]}" for _ in phone_numbers],
            "character_count": len(message),
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def _send_push_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send push notification."""
        await asyncio.sleep(0.3)
        
        device_tokens = input_data.get("device_tokens", [])
        title = input_data.get("title", "Notification")
        message = input_data["message"]
        
        return {
            "success": True,
            "channel": "push",
            "devices_count": len(device_tokens),
            "notification_id": f"push_{uuid.uuid4().hex[:12]}",
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def _send_webhook_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send webhook notification."""
        await asyncio.sleep(0.4)
        
        url = input_data.get("url", "")
        payload = input_data.get("payload", {})
        
        self.logger.info(f"Sending webhook to {url}")
        
        # Simulate HTTP request
        return {
            "success": True,
            "channel": "webhook",
            "url": url,
            "status_code": 200,
            "response_time_ms": 150,
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def _send_slack_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send Slack notification."""
        await asyncio.sleep(0.6)
        
        channel = input_data.get("slack_channel", "#general")
        message = input_data["message"]
        
        return {
            "success": True,
            "channel": "slack",
            "slack_channel": channel,
            "message_ts": datetime.utcnow().timestamp(),
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def _send_teams_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send Microsoft Teams notification."""
        await asyncio.sleep(0.6)
        
        channel = input_data.get("teams_channel", "General")
        message = input_data["message"]
        
        return {
            "success": True,
            "channel": "teams",
            "teams_channel": channel,
            "message_id": f"teams_{uuid.uuid4().hex[:12]}",
            "sent_at": datetime.utcnow().isoformat()
        }
