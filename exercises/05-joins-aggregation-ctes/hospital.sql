
CREATE TABLE main_unit ( --this creates the table--
    main_unit_id integer primary key, --main unit will be the column name, the int stores numbers,
    name text not null  --won't allow the columns to be empty--
);

CREATE TABLE unit (
    unit_id integer primary key,
    main_unit_id integer not null references main_unit,
    name text not null
);

CREATE TABLE room (
    id integer primary key,
    id integer not null references unit,
    roomNumber text not null
);

CREATE TABLE staff (
    staff_id integer primary key,
    name text not null
);

CREATE TABLE shift (
    shift_id integer primary key,
    main_unit_id integer not null references main_unit,
    staff_id integer not null references staff,
    shift_date date not null
);

CREATE TABLE patient (
    patient_id integer primary key,
    name text not null
);

CREATE TABLE patient_case (
    case_id integer primary key,
    patient_id integer not null references patient
);

CREATE TABLE episode (
    episode_id integer primary key,
    case_id integer not null references patient_case,
    main_unit_id integer not null references main_unit
);

--insurance, finance and report missing--
