
from sqlalchemy import inspect, text
from app.core.database import engine


def main():
    table_name = "relay_gmail_oauth_states"

    inspector = inspect(engine)

    if not inspector.has_table(table_name):
        raise RuntimeError(
            f"Table '{table_name}' does not exist. "
            "Check your database configuration and run the "
            "Gmail OAuth setup first."
        )

    columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    if "code_verifier" in columns:
        print("Column 'code_verifier' already exists. No changes needed.")
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE relay_gmail_oauth_states "
                "ADD COLUMN code_verifier TEXT NULL"
            )
        )

    print("Successfully added nullable code_verifier column.")


if __name__ == "__main__":
    main()
