from pydantic import BaseModel

class NotificationSettings(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = False 