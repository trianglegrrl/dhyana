from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base_models import BaseModel

class SlackTeam(BaseModel):
    """Slack team/workspace model"""
    __tablename__ = 'slack_teams'

    team_id = Column(String(20), unique=True, nullable=False)
    team_name = Column(String(100), nullable=False)
    team_domain = Column(String(100))
    bot_token = Column(Text)  # Encrypted in production
    bot_user_id = Column(String(20))
    is_active = Column(Boolean, default=True)

    # Relationships
    users = relationship('SlackUser', back_populates='team', cascade='all, delete-orphan')
    channels = relationship('SlackChannel', back_populates='team', cascade='all, delete-orphan')

class SlackUser(BaseModel):
    """Slack user model"""
    __tablename__ = 'slack_users'

    user_id = Column(String(20), nullable=False)
    team_id = Column(String(20), ForeignKey('slack_teams.team_id'), nullable=False)
    username = Column(String(100))
    real_name = Column(String(200))
    email = Column(String(200))
    is_bot = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

    # Relationships
    team = relationship('SlackTeam', back_populates='users')
    messages = relationship('SlackMessage', back_populates='user', cascade='all, delete-orphan')

class SlackChannel(BaseModel):
    """Slack channel model"""
    __tablename__ = 'slack_channels'

    channel_id = Column(String(20), nullable=False)
    team_id = Column(String(20), ForeignKey('slack_teams.team_id'), nullable=False)
    name = Column(String(100))
    is_private = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    topic = Column(Text)
    purpose = Column(Text)

    # Relationships
    team = relationship('SlackTeam', back_populates='channels')
    messages = relationship('SlackMessage', back_populates='channel', cascade='all, delete-orphan')

class SlackMessage(BaseModel):
    """Slack message model"""
    __tablename__ = 'slack_messages'

    message_ts = Column(String(20), nullable=False)  # Slack timestamp
    channel_id = Column(String(20), ForeignKey('slack_channels.channel_id'), nullable=False)
    user_id = Column(String(20), ForeignKey('slack_users.user_id'))
    text = Column(Text)
    message_type = Column(String(50), default='message')
    thread_ts = Column(String(20))  # For threaded messages

    # Relationships
    channel = relationship('SlackChannel', back_populates='messages')
    user = relationship('SlackUser', back_populates='messages')