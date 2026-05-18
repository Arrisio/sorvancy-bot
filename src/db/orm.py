from datetime import date, datetime
from sqlalchemy import (
    BigInteger, Boolean, Integer, String, Text, Date, TIMESTAMP,
    ForeignKey, CheckConstraint, UniqueConstraint, Sequence,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(
        Integer, Sequence("customers_id_seq", start=10000), primary_key=True
    )
    max_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    max_username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    survey_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    discount_percent: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="NOW()", nullable=False
    )
    birthday_reminded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opt_out_marketing: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    last_touch: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    survey_draft: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    children: Mapped[list["Child"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    coupons: Mapped[list["Coupon"]] = relationship(back_populates="customer")


class Child(Base):
    __tablename__ = "children"
    __table_args__ = (CheckConstraint("gender IN ('male', 'female')", name="gender_check"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    birthday_reminded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="NOW()", nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="children")


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    max_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    is_owner: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    customer_mode: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="NOW()", nullable=False
    )

    broadcasts: Mapped[list["Broadcast"]] = relationship(back_populates="creator")


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    max_payment_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active", server_default="'active'"
    )

    customer: Mapped["Customer"] = relationship(back_populates="coupons")


class FinancialConfig(Base):
    __tablename__ = "financial_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # always 1
    registration_discount_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, server_default="10"
    )
    survey_coupon_value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300, server_default="300"
    )
    survey_coupon_valid_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    survey_coupon_max_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    birthday_coupon_value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300, server_default="300"
    )
    birthday_coupon_valid_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7, server_default="7"
    )
    birthday_coupon_max_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_message_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    scheduled_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="NOW()", nullable=False
    )
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    coupon_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coupon_validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coupon_max_payment_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coupon_display_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    creator: Mapped["Staff"] = relationship(back_populates="broadcasts")
    recipients: Mapped[list["BroadcastRecipient"]] = relationship(back_populates="broadcast")


class BroadcastRecipient(Base):
    __tablename__ = "broadcast_recipients"
    __table_args__ = (UniqueConstraint("broadcast_id", "customer_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", server_default="'pending'"
    )
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    broadcast: Mapped["Broadcast"] = relationship(back_populates="recipients")
    customer: Mapped["Customer"] = relationship()
