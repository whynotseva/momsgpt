from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.api.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")
    configs = relationship("Config", back_populates="user")


class AppServer(Base): # Renamed to avoid confusion with Python's http.server
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_url = Column(String, nullable=False) # Marzban URL
    api_user = Column(String, nullable=True) # If needed per server
    api_password = Column(String, nullable=True) # If needed per server
    region = Column(String, default="EU")
    is_active = Column(Boolean, default=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="subscription")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer, nullable=False) # In minimal units (kopecks) or float
    currency = Column(String, default="RUB")
    provider_payment_id = Column(String, unique=True, index=True) # Yookassa ID
    status = Column(String, default="pending") # pending, succeeded, canceled
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")


class Config(Base):
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    server_id = Column(Integer, ForeignKey("servers.id"))
    uuid = Column(String, unique=True, index=True)
    email = Column(String, index=True) # Marzban username
    vless_link = Column(Text)
    subscription_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="configs")
    server = relationship("AppServer")


class Device(Base):
    """Track devices that connected to subscription endpoint."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_name = Column(String, nullable=True)  # e.g. "iPhone 14 Pro Max"
    os_version = Column(String, nullable=True)   # e.g. "iOS 18.2"
    app_name = Column(String, nullable=True)     # e.g. "Happ"
    app_version = Column(String, nullable=True)  # e.g. "3.7.0"
    user_agent = Column(Text, nullable=True)     # Full User-Agent
    ip_address = Column(String, nullable=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
