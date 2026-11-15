db = db.getSiblingDB("pagila_docs");

function show(title, value) {
  print("\n=== " + title);
  printjson(value);
}

const q1 = { rating: "PG-13", length: { $gt: 120 } };
show("1. PG-13 and longer than 120 min: count", db.films.countDocuments(q1));
show("1. first 3", db.films.find(q1, { title: 1, rating: 1, length: 1 }).sort({ _id: 1 }).limit(3).toArray());

const q2 = { "actors.actor_id": 1 };
show("2. films with actor 1: count", db.films.countDocuments(q2));
show("2. first 3", db.films.find(q2, { title: 1 }).sort({ _id: 1 }).limit(3).toArray());

const q3 = { categories: "Horror", rental_rate: NumberDecimal("0.99") };
show("3. Horror at 0.99: count", db.films.countDocuments(q3));
show("3. first 3", db.films.find(q3, { title: 1, categories: 1, rental_rate: 1 }).sort({ _id: 1 }).limit(3).toArray());

const q4 = { recent_rentals: { $elemMatch: { return_date: null } } };
show("4. customers with an open recent rental: count", db.customers.countDocuments(q4));
show("4. first 3", db.customers.find(q4, { first_name: 1, last_name: 1 }).sort({ _id: 1 }).limit(3).toArray());

const c1 = db.customers.findOne(
  { _id: 1 },
  { _id: 0, first_name: 1, last_name: 1, "recent_rentals.title": 1 }
);
show("5. customer 1 (projection)", c1);
show("5. number of titles", c1.recent_rentals.length);

const r6 = db.films.updateMany(
  { rating: "NC-17", length: { $lt: 60 } },
  { $inc: { rental_rate: NumberDecimal("0.50") } }
);
show("6. updateMany NC-17 < 60 min", r6);

const r7 = db.customers.updateOne(
  { _id: 1 },
  {
    $push: {
      recent_rentals: {
        $each: [{
          rental_id: 99999, film_id: 1, title: "ACADEMY DINOSAUR",
          rental_date: new Date("2026-08-01T10:00:00Z"), return_date: null
        }],
        $position: 0,
        $slice: 10
      }
    },
    $inc: { rental_count: 1 }
  }
);
show("7. $push with $each/$position/$slice", r7);
const after7 = db.customers.findOne({ _id: 1 }, { _id: 0, recent_rentals: 1 }).recent_rentals;
show("7. recent_rentals size", after7.length);
show("7. first item", after7[0]);
show("7. last item", after7[after7.length - 1]);

const upsert8 = () => db.films.updateOne(
  { _id: 1001 },
  { $setOnInsert: { title: "TEST FILM" } },
  { upsert: true }
);
show("8. first run", upsert8());
show("8. second run", upsert8());
show("8. the document", db.films.findOne({ _id: 1001 }));
