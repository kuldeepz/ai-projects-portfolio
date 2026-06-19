# SQL Query Generator

Convert natural language questions into correct, optimized SQL — with explanations, performance tips, and alternative approaches. Supports 6 SQL dialects and is schema-aware for accurate, context-specific queries.

## Features

- **6 SQL Dialects** — PostgreSQL, MySQL, SQLite, SQL Server, BigQuery, Snowflake
- **Schema-aware** — Provide your CREATE TABLE statements for accurate column/table names
- **Explains every query** — Plain English breakdown of what the SQL does
- **Assumptions listed** — Shows what it assumed about your schema
- **Performance notes** — Index recommendations and optimization tips
- **Alternative approaches** — Shows a second way to write the same query
- **Multi-turn session** — Ask follow-up questions referencing earlier queries
- **Save to .sql file** — Export all queries from a session

## Setup

```bash
cd sql-query-generator

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key
```

## Usage

### Interactive Mode

```bash
python generator.py
```

Select dialect → optionally load schema → ask questions in plain English.

### CLI Mode (single query)

```bash
python generator.py "Show me the top 10 customers by total order value in the last 90 days"

# With schema file for accuracy
python generator.py "Find all users who never placed an order" --schema schema.sql --dialect PostgreSQL
```

**Schema file example** (`schema.sql`):
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    created_at TIMESTAMP
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total DECIMAL(10,2),
    created_at TIMESTAMP
);
```

**Sample output:**
```
╭── Generated PostgreSQL Query ──────────────────────────────────╮
│  1 SELECT u.name, SUM(o.total) AS total_value                  │
│  2 FROM users u                                                 │
│  3 JOIN orders o ON o.user_id = u.id                           │
│  4 WHERE o.created_at >= NOW() - INTERVAL '90 days'            │
│  5 GROUP BY u.id, u.name                                       │
│  6 ORDER BY total_value DESC                                    │
│  7 LIMIT 10;                                                    │
╰────────────────────────────────────────────────────────────────╯

╭── What This Query Does ─────────╮
│  Joins users and orders, filters │
│  to last 90 days, aggregates by  │
│  user, and returns top 10.       │
╰─────────────────────────────────╯
```

## Run Tests

```bash
python test_generator.py
```

No API key needed.

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Structured Output | OpenAI Function Calling |
| Terminal UI | Rich (syntax highlighting) |

## Project Structure

```
sql-query-generator/
├── generator.py        # Main application
├── test_generator.py   # Sanity tests
├── requirements.txt
├── .env.example
└── README.md
```
