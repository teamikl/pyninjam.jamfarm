CREATE TABLE user_table (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE,
    password VARCHAR,
    enable BOOLEAN DEFAULT 0,
    lastlogin DATETIME DEFAULT NULL,
    registered DATETIME DEFAULT CURRENT_DATE
);

CREATE TABLE server_table (
    id INTEGER PRIMARY KEY,
    uid INTEGER,
    address VARCHAR UNIQUE,
    username VARCHAR,
    password VARCHAR,
    url VARCHAR,
    comment VARCHAR,
    enable BOOLEAN DEFAULT 1,
    lastaccess DATETIME,
    registered DATETIME DEFAULT CURRENT_DATE
);

CREATE TABLE log_table (
    id INTEGER PRIMARY KEY,
    uid INTEGER,
    sender VARCHAR,
    message VARCHAR,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- currently, event_table is not used.
CREATE TABLE event_table (
    id INTEGER PRIMARY KEY,
    uid INTEGER,
    sid INTEGER,
    message VARCHAR,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

