db = db.getSiblingDB("pagila_docs");

function summary(label) {
  const e = db.films.find({ "actors.actor_id": 1 }).explain("executionStats");
  const stages = [];
  let s = e.queryPlanner.winningPlan;
  while (s) {
    stages.push(s.stage + (s.indexName ? " (" + s.indexName + ")" : ""));
    s = s.inputStage;
  }
  print("\n=== " + label);
  printjson({
    stages: stages.join(" <- "),
    nReturned: e.executionStats.nReturned,
    totalDocsExamined: e.executionStats.totalDocsExamined,
    totalKeysExamined: e.executionStats.totalKeysExamined,
    executionTimeMillis: e.executionStats.executionTimeMillis
  });
}

if (db.films.getIndexes().some(i => i.name === "actors.actor_id_1")) db.films.dropIndex("actors.actor_id_1");
summary("before the index");

print("\ncreateIndex: " + db.films.createIndex({ "actors.actor_id": 1 }));
summary("after the index");
