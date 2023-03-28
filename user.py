class User:

    def __init__(self, username, last_access, inactive_at, delete_at, created_at, updated_at):
        self.updated_at = updated_at
        self.created_at = created_at
        self.delete_at = delete_at
        self.inactive_at = inactive_at
        self.last_access = last_access
        self.username = username


