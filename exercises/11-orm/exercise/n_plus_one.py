from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db import QueryCounter, make_engine
from models import Film

def print_films(films):
    for film in films:
        names = ", ".join(a.name for a in film.actors)
        print(f"{film.film_id:>4} {film.title}: {names}")

def main():
    engine = make_engine()
    counter = QueryCounter(engine)

    with Session(engine) as session:
        counter.count = 0
        films = session.scalars(select(Film).order_by(Film.film_id).limit(100)).all()
        print_films(films)
        n_plus_one = counter.count

    with Session(engine) as session:
        counter.count = 0
        films = session.scalars(
            select(Film).order_by(Film.film_id).limit(100).options(selectinload(Film.actors))
        ).all()
        print_films(films)
        fixed = counter.count

    print()
    print(f"SELECT statements with lazy loading (N+1): {n_plus_one}")
    print(f"SELECT statements with selectinload:       {fixed}")

if __name__ == "__main__":
    main()
