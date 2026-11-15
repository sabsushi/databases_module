from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Language(Base):
    __tablename__ = "language"

    language_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    last_update: Mapped[datetime]

    films: Mapped[list["Film"]] = relationship(
        back_populates="language", foreign_keys="Film.language_id"
    )

    def __repr__(self):
        return f"Language({self.language_id}, {self.name!r})"

class FilmActor(Base):
    __tablename__ = "film_actor"

    actor_id: Mapped[int] = mapped_column(ForeignKey("actor.actor_id"), primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("film.film_id"), primary_key=True)
    last_update: Mapped[datetime]

class FilmCategory(Base):
    __tablename__ = "film_category"

    film_id: Mapped[int] = mapped_column(ForeignKey("film.film_id"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.category_id"), primary_key=True)
    last_update: Mapped[datetime]

class Film(Base):
    __tablename__ = "film"

    film_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    release_year: Mapped[int | None]
    language_id: Mapped[int] = mapped_column(ForeignKey("language.language_id"))
    original_language_id: Mapped[int | None] = mapped_column(ForeignKey("language.language_id"))
    rental_duration: Mapped[int] = mapped_column(SmallInteger)
    rental_rate: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    length: Mapped[int | None] = mapped_column(SmallInteger)
    replacement_cost: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    rating: Mapped[str | None] = mapped_column(String)
    last_update: Mapped[datetime]

    language: Mapped[Language] = relationship(
        back_populates="films", foreign_keys=[language_id]
    )
    actors: Mapped[list["Actor"]] = relationship(
        secondary="film_actor", back_populates="films", order_by="Actor.actor_id"
    )
    categories: Mapped[list["Category"]] = relationship(
        secondary="film_category", back_populates="films", order_by="Category.category_id"
    )

    def __repr__(self):
        return f"Film({self.film_id}, {self.title!r})"

class Actor(Base):
    __tablename__ = "actor"

    actor_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    last_update: Mapped[datetime]

    films: Mapped[list[Film]] = relationship(
        secondary="film_actor", back_populates="actors", order_by="Film.film_id"
    )

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"Actor({self.actor_id}, {self.name!r})"

class Category(Base):
    __tablename__ = "category"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    last_update: Mapped[datetime]

    films: Mapped[list[Film]] = relationship(
        secondary="film_category", back_populates="categories", order_by="Film.film_id"
    )

    def __repr__(self):
        return f"Category({self.category_id}, {self.name!r})"
