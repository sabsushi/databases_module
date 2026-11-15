db = db.getSiblingDB("pagila_docs");

const schema = {
  bsonType: "object",
  required: ["title", "rating", "length", "rental_rate", "categories", "actors"],
  properties: {
    title: { bsonType: "string" },
    rating: { enum: ["G", "PG", "PG-13", "R", "NC-17"] },
    length: { bsonType: "int", minimum: 1, maximum: 999 },
    rental_rate: { bsonType: "decimal" },
    categories: { bsonType: "array", items: { bsonType: "string" } },
    actors: {
      bsonType: "array",
      items: {
        bsonType: "object",
        required: ["actor_id", "name"],
        properties: {
          actor_id: { bsonType: "int" },
          name: { bsonType: "string" }
        }
      }
    }
  }
};

printjson(db.runCommand({
  collMod: "films",
  validator: { $jsonSchema: schema },
  validationLevel: "strict",
  validationAction: "error"
}));

const valid = db.films.findOne({ _id: 1 });
delete valid._id;

function tryInsert(label, doc) {
  print("\n=== " + label);
  try {
    const r = db.films.insertOne(doc);
    print("inserted: " + r.insertedId);
  } catch (e) {
    print("REJECTED: " + e.message);
    if (e.errInfo) printjson(e.errInfo.details.schemaRulesNotSatisfied);
  }
}

tryInsert("rating: \"XXX\"", Object.assign({}, valid, { _id: 2001, rating: "XXX" }));
tryInsert("length: \"long\"", Object.assign({}, valid, { _id: 2002, length: "long" }));
