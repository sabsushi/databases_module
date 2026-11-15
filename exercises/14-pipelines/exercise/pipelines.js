db = db.getSiblingDB("pagila_docs");

function show(title, docs, n) {
  print("\n=== " + title + " (" + docs.length + " documents)");
  printjson(n ? docs.slice(0, n) : docs);
}

const p1 = db.rentals.aggregate([
  { $match: { rental_date: { $gte: ISODate("2025-01-01T00:00:00Z"), $lt: ISODate("2026-01-01T00:00:00Z") } } },
  { $unwind: "$categories" },
  {
    $group: {
      _id: {
        category: "$categories",
        month: { $dateTrunc: { date: "$rental_date", unit: "month", timezone: "UTC" } }
      },
      revenue: { $sum: "$amount" }
    }
  },
  { $project: { _id: 0, category: "$_id.category", month: "$_id.month", revenue: 1 } },
  { $sort: { category: 1, month: 1 } }
]).toArray();
show("1. Revenue per category per month in 2025", p1, 3);
show("1. Action, January 2025", p1.filter(d => d.category === "Action" && d.month.getUTCMonth() === 0));

const p2 = db.films.aggregate([
  { $unwind: "$categories" },
  { $unwind: "$actors" },
  {
    $group: {
      _id: { category: "$categories", actor_id: "$actors.actor_id" },
      name: { $first: "$actors.name" },
      films: { $sum: 1 }
    }
  },
  {
    $group: {
      _id: "$_id.category",
      films: { $max: "$films" },
      candidates: { $push: { actor_id: "$_id.actor_id", name: "$name", films: "$films" } }
    }
  },
  {
    $project: {
      _id: 0,
      category: "$_id",
      films: 1,
      actors: {
        $sortArray: {
          input: {
            $map: {
              input: { $filter: { input: "$candidates", cond: { $eq: ["$$this.films", "$films"] } } },
              in: { actor_id: "$$this.actor_id", name: "$$this.name" }
            }
          },
          sortBy: { actor_id: 1 }
        }
      }
    }
  },
  { $sort: { category: 1 } }
]).toArray();
show("2. Actor(s) with most films in each category", p2, 3);
print("total actors: " + p2.reduce((n, d) => n + d.actors.length, 0));

const p3 = db.films.aggregate([
  {
    $bucket: {
      groupBy: "$length",
      boundaries: [0, 60, 90, 120, 150, 186],
      default: "other",
      output: { films: { $sum: 1 } }
    }
  }
]).toArray();
show("3. Film lengths ($bucket)", p3);

const p4 = db.films.aggregate([
  {
    $facet: {
      totals: [
        { $group: { _id: null, films: { $sum: 1 }, avg_rental_rate: { $avg: "$rental_rate" } } },
        { $project: { _id: 0, films: 1, avg_rental_rate: { $round: ["$avg_rental_rate", 2] } } }
      ],
      by_rating: [
        { $group: { _id: "$rating", films: { $sum: 1 } } },
        { $project: { _id: 0, rating: "$_id", films: 1 } },
        { $sort: { rating: 1 } }
      ],
      longest: [
        { $sort: { length: -1, title: 1 } },
        { $limit: 5 },
        { $project: { _id: 0, title: 1, length: 1 } }
      ]
    }
  }
]).toArray();
show("4. $facet summaries", p4);
