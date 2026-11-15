from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from db import make_engine
from models import Actor, Category, Film, FilmActor, FilmCategory

HANDWRITTEN = {
    "Q1": """
        SELECT c.name, count(*) AS films
        FROM category c JOIN film_category fc ON fc.category_id = c.category_id
        GROUP BY c.category_id, c.name
        ORDER BY films DESC, c.name""",
    "Q2": """
        SELECT f.film_id, f.title, f.length
        FROM film f
        WHERE f.length > (SELECT avg(length) FROM film)
        ORDER BY f.length DESC, f.film_id""",
    "Q3": """
        SELECT a.actor_id, a.first_name, a.last_name, count(*) AS films
        FROM actor a JOIN film_actor fa ON fa.actor_id = a.actor_id
        GROUP BY a.actor_id
        ORDER BY films DESC, a.actor_id
        LIMIT 10""",
}

films = func.count().label("films")
q1 = (
    select(Category.name, films)
    .join(FilmCategory, FilmCategory.category_id == Category.category_id)
    .group_by(Category.category_id, Category.name)
    .order_by(films.desc(), Category.name)
)

avg_length = select(func.avg(Film.length)).scalar_subquery()
q2 = (
    select(Film.film_id, Film.title, Film.length)
    .where(Film.length > avg_length)
    .order_by(Film.length.desc(), Film.film_id)
)

films3 = func.count().label("films")
q3 = (
    select(Actor.actor_id, Actor.first_name, Actor.last_name, films3)
    .join(FilmActor, FilmActor.actor_id == Actor.actor_id)
    .group_by(Actor.actor_id)
    .order_by(films3.desc(), Actor.actor_id)
    .limit(10)
)

def main():
    engine = make_engine(echo=True)
    with Session(engine) as session:
        for name, query in [("Q1", q1), ("Q2", q2), ("Q3", q3)]:
            print(f"\n================ {name} (ORM) ================")
            orm_rows = [tuple(r) for r in session.execute(query)]
            print(f"\n---------------- {name} (handwritten) ----------------")
            sql_rows = [tuple(r) for r in session.execute(text(HANDWRITTEN[name]))]
            same = orm_rows == sql_rows
            print(f"\n{name}: ORM {len(orm_rows)} rows, handwritten {len(sql_rows)} rows, same rows: {same}")
            for row in orm_rows[:3]:
                print("   ", row)
            assert same, f"{name} differs"

if __name__ == "__main__":
    main()
