import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    username text unique,
    last_access text,
    inactive_at text,
    delete_at text,
    created_at text,
    updated_at text
)""")

connection.commit()


def create_user(user):
    with connection:
        try:
            cursor.execute(
                "INSERT INTO users VALUES (:username, :last_access, :inactive_at, :delete_at, :created_at, :updated_at)",
                {'username': user.username, 'last_access': user.last_access, 'inactive_at': user.inactive_at,
                 'delete_at': user.delete_at, 'created_at': user.created_at,
                 'updated_at': user.updated_at})
        except:
            pass


def get_users():
    with connection:
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()


def update_users(users):
    with connection:
        for user in users:
            if user.inactive_at != '':
                cursor.execute(f"UPDATE users SET inactive_at='{user.inactive_at}' WHERE username='{user.username}'")
            if user.delete_at != '':
                cursor.execute(f"UPDATE users SET delete_at='{user.delete_at}' WHERE username='{user.username}'")


def get_inactive_users():
    with connection:
        cursor.execute("SELECT * FROM users WHERE inactive_at <> ''")
        return cursor.fetchall()
