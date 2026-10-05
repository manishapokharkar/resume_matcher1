import sqlite3

DB_PATH = "resume_matcher.db"


connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()


# Check existing columns
cursor.execute(
    "PRAGMA table_info(candidates)"
)

columns = [
    row[1]
    for row in cursor.fetchall()
]

print("Existing candidates columns:")
print(columns)


# Add source column if missing
if "source" not in columns:

    cursor.execute(
        """
        ALTER TABLE candidates
        ADD COLUMN source TEXT
        """
    )

    print("Added missing column: source")

else:

    print("Column already exists: source")


connection.commit()
connection.close()

print("Database migration completed.")