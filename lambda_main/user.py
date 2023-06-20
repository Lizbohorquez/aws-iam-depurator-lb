class User:
    """
    La clase User representa los usuarios de IAM, contiene propiedades que
    describen el usuario y su registro de actividad.
    """

    def __init__(self, account_id, username, last_access, inactive_at, delete_at, created_at, updated_at):
        """
        Crea una instancia de la clase User.
        :param account_id (str): El ID de la cuenta de AWS a la que pertenece el usuario.
        :param username (str): El nombre del usuario de IAM.

        Args:
            account_id (str): El ID de la cuenta de AWS a la que pertenece el usuario.
            username (str): El nombre del usuario de IAM.
            last_access (str): La fecha y hora de la última actividad del usuario.
            inactive_at(str): La fecha y hora en que el usuario se volvió inactivo.
            delete_at(str): La fecha y hora en que se eliminará el usuario.
            created_at(str): La fecha y hora en que se creó el usuario.
            updated_at(str): La fecha y hora en que se actualizó el usuario por última vez.
        """
        self.account_id = account_id
        self.updated_at = updated_at
        self.created_at = created_at
        self.delete_at = delete_at
        self.inactive_at = inactive_at
        self.last_access = last_access
        self.username = username


