class User:

    def __init__(self, account_id, username, last_access, inactive_at, delete_at, created_at, updated_at):
        self.account_id = account_id
        self.updated_at = updated_at
        self.created_at = created_at
        self.delete_at = delete_at
        self.inactive_at = inactive_at
        self.last_access = last_access
        self.username = username


