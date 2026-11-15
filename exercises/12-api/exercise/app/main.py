from datetime import date, datetime, time, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager

from app.db import SessionLocal
from app.models import Customer, Film, Inventory, Rental

app = FastAPI(title="Exercise 12: rentals API")

MAX_ATTEMPTS = 3

def get_session():
    with SessionLocal() as session:
        yield session

class RentalIn(BaseModel):
    customer_id: int
    film_id: int
    store_id: int
    staff_id: int

class NoCopyAvailable(Exception):
    pass

def try_rent(session: Session, body: RentalIn) -> Rental:
    with session.begin():
        if session.get(Customer, body.customer_id) is None:
            raise HTTPException(404, f"customer {body.customer_id} not found")
        if session.get(Film, body.film_id) is None:
            raise HTTPException(404, f"film {body.film_id} not found")

        open_rental = exists().where(
            Rental.inventory_id == Inventory.inventory_id,
            Rental.return_date.is_(None),
        )
        copy = session.scalars(
            select(Inventory)
            .where(
                Inventory.film_id == body.film_id,
                Inventory.store_id == body.store_id,
                ~open_rental,
            )
            .order_by(Inventory.inventory_id)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if copy is None:
            raise NoCopyAvailable()

        rental = Rental(
            rental_date=func.now(),
            inventory_id=copy.inventory_id,
            customer_id=body.customer_id,
            staff_id=body.staff_id,
        )
        session.add(rental)
        session.flush()
        return rental

@app.post("/rentals", status_code=201)
def create_rental(body: RentalIn, session: Session = Depends(get_session)):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            rental = try_rent(session, body)
            return {"rental_id": rental.rental_id, "inventory_id": rental.inventory_id}
        except NoCopyAvailable:
            raise HTTPException(409, "no copy of this film is available in this store")
        except IntegrityError as e:
            if "rental_one_open_per_copy" not in str(e.orig):
                raise
    raise HTTPException(409, "no copy available after retrying")

@app.post("/rentals/{rental_id}/return")
def return_rental(rental_id: int, session: Session = Depends(get_session)):
    with session.begin():
        rental = session.get(Rental, rental_id, with_for_update=True)
        if rental is None:
            raise HTTPException(404, f"rental {rental_id} not found")
        if rental.return_date is not None:
            raise HTTPException(409, f"rental {rental_id} was already returned")
        rental.return_date = func.now()
        session.flush()
        session.refresh(rental, ["return_date"])
        return {"rental_id": rental.rental_id, "return_date": rental.return_date}

@app.get("/rentals/overdue")
def overdue_rentals(as_of: date = Query(...), session: Session = Depends(get_session)):
    as_of_ts = datetime.combine(as_of, time.min, tzinfo=timezone.utc)
    due_date = (Rental.rental_date + func.make_interval(0, 0, 0, Film.rental_duration)).label("due_date")
    rows = session.execute(
        select(Rental, due_date)
        .join(Rental.customer)
        .join(Rental.inventory)
        .join(Inventory.film)
        .options(
            contains_eager(Rental.customer),
            contains_eager(Rental.inventory).contains_eager(Inventory.film),
        )
        .where(Rental.return_date.is_(None), due_date < as_of_ts)
        .order_by(Rental.rental_date, Rental.rental_id)
    ).all()
    return [
        {
            "rental_id": r.rental_id,
            "rental_date": r.rental_date,
            "due_date": due,
            "customer": {
                "customer_id": r.customer.customer_id,
                "first_name": r.customer.first_name,
                "last_name": r.customer.last_name,
            },
            "film": {"film_id": r.inventory.film.film_id, "title": r.inventory.film.title},
        }
        for r, due in rows
    ]
