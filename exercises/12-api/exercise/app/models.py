from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, SmallInteger, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    type_annotation_map = {datetime: DateTime(timezone=True)}

class Customer(Base):
    __tablename__ = "customer"

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int]
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    activebool: Mapped[bool]
    create_date: Mapped[date]
    loyalty_points: Mapped[int] = mapped_column(server_default=text("0"))

    rentals: Mapped[list["Rental"]] = relationship(back_populates="customer")

class Staff(Base):
    __tablename__ = "staff"

    staff_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    store_id: Mapped[int]
    active: Mapped[bool]

class Film(Base):
    __tablename__ = "film"

    film_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    rental_duration: Mapped[int] = mapped_column(SmallInteger)
    rental_rate: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    length: Mapped[int | None] = mapped_column(SmallInteger)

    inventory: Mapped[list["Inventory"]] = relationship(back_populates="film")

class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("film.film_id"))
    store_id: Mapped[int]

    film: Mapped[Film] = relationship(back_populates="inventory")
    rentals: Mapped[list["Rental"]] = relationship(back_populates="inventory")

class Rental(Base):
    __tablename__ = "rental"
    __table_args__ = (
        Index(
            "rental_one_open_per_copy",
            "inventory_id",
            unique=True,
            postgresql_where=text("return_date IS NULL"),
        ),
    )

    rental_id: Mapped[int] = mapped_column(primary_key=True)
    rental_date: Mapped[datetime]
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.inventory_id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.customer_id"))
    return_date: Mapped[datetime | None]
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.staff_id"))

    customer: Mapped[Customer] = relationship(back_populates="rentals")
    inventory: Mapped[Inventory] = relationship(back_populates="rentals")
    staff: Mapped[Staff] = relationship()
