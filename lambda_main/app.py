"""
Módulo app, este módulo contiene las funciones necesarias para listar, desactivar
y eliminar usuarios de IAM de una o varias cuentas de AWS.
"""
import boto3
from datetime import datetime
from dynamodb import Users
import itertools

from user import User
import constants

iam = boto3.client('iam')
sts = boto3.client('sts')
dynamo_resource = boto3.resource('dynamodb')

users = Users(dynamo_resource)
account_ids = ['']


# listar usuarios
def list_users():
    """
    Funcion que devulve una lista de usuarios del servicio IAM de una cuenta en AWS
    utiliza la paginación para manejar las respuestas con muchos usuarios.
    """
    paginator = iam.get_paginator('list_users')
    return list(itertools.chain.from_iterable([i["Users"] for i in paginator.paginate()]))


# Listar usuarios inactivos
def list_zombie_users():
    """
    Función encargada de listar  los usuarios de IAM que no han iniciado sesión
    en un número de días determinado por la constante INACTIVE_DAYS en el modulo constants.py.
    return: Lista con la información de los usuarios inactivos
    """
    expected_days = constants.INACTIVE_DAYS
    result = list()
    for user in list_users():
        last_access = get_last_access(user)
        if isinstance(last_access, datetime):
            difference = (datetime.now().replace(tzinfo=None) - last_access.replace(tzinfo=None)).days
            # Dias de inactividad
            if difference >= expected_days:
                result.append(user)
        if isinstance(last_access, str) and (
                datetime.now().replace(tzinfo=None) - user['CreateDate'].replace(tzinfo=None)).days > expected_days:
            result.append(user)
    return result


# Listar access keys
def list_access_keys(username):
    """
    Función que retorna una lista con la información de todas las access keys del usuario.
    Args:
        username (str): El nombre de usuario para el cual se desea obtener la información.
    Returns:
        dict: diccionario con la siguiente información de cada access keys:
        - AccessKeyId
        - CreateDate
        - Status
        - UserName
    """
    return iam.list_access_keys(UserName=username)


# Imprimir ultimo acceso
def get_last_access(user):
    """
    Devuelve la fecha y hora del ultimo acceso de los usuarios de IAM.
    Teniendo en cuanta su último ingreso por acces key o por password,
    si el usuario no utilizo ninguno de los anteriores nos devuelve la fecha de creación del usuario.
    Args:
        user (dict):un diccionario que representa al usuario de IAM, con los campos 'UserName',
        'PasswordLastUsed' y'CreateDate'.

    Returns:
        last_access de tipo datetime o str que es la fecha y hora del último acceso del usuario, o una cadena
        que indica que el usuario no tiene ni password ni access key
    """
    # Busca las acces keys del usuario
    access_keys = list_access_keys(user['UserName'])
    # inicializa las variables que indican si el ultimo acceso fue por password o access key
    last_access_by_password = False
    last_access_by_key = False
    # Inicializa la variable con la fecha de creacion del usuario
    last_access = None
    # Busca el ultimo acceso por acces key si hay alguna.
    if access_keys['AccessKeyMetadata']:
        try:
            last_access_by_key = iam.get_access_key_last_used(
                AccessKeyId=access_keys['AccessKeyMetadata'][0]['AccessKeyId'])['AccessKeyLastUsed']['LastUsedDate']
        except:
            pass
    # Busca el ultimo acceso por password
    if 'PasswordLastUsed' in user:
        last_access_by_password = user['PasswordLastUsed']
    if last_access is None:
        last_access = user['CreateDate']
    # Determinar cual fue el ultimo acceso entre password y el access key
    if last_access_by_password and last_access_by_key:
        if last_access_by_password < last_access_by_key:
            last_access = last_access_by_key
        else:
            last_access = last_access_by_password
    elif last_access_by_password:
        last_access = last_access_by_password
    elif last_access_by_key:
        last_access = last_access_by_key
    else:
        last_access = "El usuario no tiene password ni access key"
    return last_access


def delete_password_and_key(username, acct_id):
    """
    Función que se encarga de desactivar los usuarios que reportan determinado tiempo de inactividad en la consola.
    Se procede a desactivar las access keys del usuario y se elimina el password.
    Tambien se remueve cualquier politica que este asociada al usuario.
    Args:
        username (str): Nombre de usuario de IAM de AWS
        acct_id (str): id de la cuenta
    Returns:
        list: Una lista de respuestas de AWS
    """
    access_keys = list_access_keys(username)
    response = []
    for access_key in access_keys['AccessKeyMetadata']:
        response.append(iam.update_access_key(
            UserName=username,
            AccessKeyId=access_key['AccessKeyId'],
            Status='Inactive'
        ))
    try:
        response.append(iam.delete_login_profile(UserName=username))
    except:
        pass
    try:
        # db.update_users([User(username, '', datetime.now().strftime(date_format), '', '', '')])
        res = users.update_user(User(acct_id, username, '', datetime.now().strftime(constants.DATE_FORMAT), '', '', ''))
        print(res)
    except:
        print(f"Error al actualizar usuario: {username}")
    try:
        # Obtiene las políticas asociadas al usuario
        policies = iam.list_attached_user_policies(UserName=username)['AttachedPolicies']
        for policy in policies:
            iam.detach_user_policy(UserName=username, PolicyArn=policy['PolicyArn'])
            # iam.delete_user_policy(UserName=username, PolicyName=policy['PolicyName'])
    except:
        pass
    return response


def delete_user(username, acct_id):
    """
    Función que se encarga de eliminar las acces keys del usuario
    asi como de removerlo de los grupos, roles y políticas de IAM que tenga asociadas.
    Y por último se elimina definitivamente el usuario de IAM.
    Args:
        username (str): El nombre de usuario de IAM a eliminar.
    """
    access_keys = list_access_keys(username)
    try:
        policies = iam.list_attached_user_policies(UserName=username)['AttachedPolicies']
        for policy in policies:
            iam.detach_user_policy(UserName=username, PolicyArn=policy['PolicyArn'])
    except:
        pass
    try:
        roles = iam.list_roles_for_user(UserName=username)['Roles']
        for role in roles:
            iam.remove_role_from_user(UserName=username, RoleName=role['RoleName'])
    except:
        pass
    try:
        groups = iam.list_groups_for_user(UserName=username)['Groups']
        for group in groups:
            iam.remove_user_from_group(GroupName=group['GroupName'], UserName=username)
    except:
        pass
    for access_key in access_keys['AccessKeyMetadata']:
        iam.delete_access_key(UserName=username, AccessKeyId=access_key['AccessKeyId'])
    # Se elimina finalmente el usuario de IAM
    try:
        print(iam.delete_user(UserName=username))
        users.update_user(User(acct_id, username, '', '', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), '', ''))
        print(f"Usuario {username} eliminado")
    except:
        print(f"Error al eliminar el usuario: {username}")


def role_arn_to_session(**args):
    """
    Esta función asume un rol de AWS y devuelve una sesión de Boto3 utilizando las credenciales temporales obtenidas al asumir el rol.
    Args:
        **args: Un diccionario que contiene los siguientes parámetros:
        RoleArn: El ARN del rol de AWS que se desea asumir.
        RoleSessionName: Nombre descriptivo para la sesión del rol.
    Returns:
        Una instancia de boto3.Session que utiliza las credenciales temporales obtenidas al asumir el rol especificado.
    """
    client = boto3.client("sts")
    response = client.assume_role(**args)
    return boto3.Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )


def lambda_handler(event, context):
    """
        Es el controlador principal de la función Lambda.
        Toma dos argumentos, `event` y `context`, que se proporcionan
        automáticamente cuando se invoca la función.
        Args:
            event: dict que contiene información sobre el evento que provocó la ejecución de la función.
            context: objeto que proporciona información sobre el entorno de ejecución de la función.
        Returns:
          una cadena que indica si la función se ejecutó correctamente.
        """
    # validar instancia de la tabla (requerido)
    if users.exists(constants.TABLE_NAME):
        print(f'Tabla {constants.TABLE_NAME} ya existe!')
    else:
        users.create_table(constants.TABLE_NAME)
    events = {
        'test': 0,
        'staging': 1,
        'prod': 2
    }
    event = event['detail']['mode']
    if event in list(dict.fromkeys(events)):
        event_number = events[event]
    print(f'Event: {event} \n Event number: {event_number}', )
    global iam
    for account in account_ids:
        session = role_arn_to_session(
            RoleArn=f'arn:aws:iam::{account}:role/{constants.ASSUME_ROLE}',
            RoleSessionName=f'lambda_main-cleaner-session-{account}'
        )
        iam = session.client('iam')
        sts = session.client('sts')
        account_id = sts.get_caller_identity().get('Account')
        user_list = []
        users_to_delete = users.get_inactive_users()
        if event_number >= 0:
            for user in list_users():
                user_list.append(User(
                    account_id,
                    user['UserName'],
                    get_last_access(user) if isinstance(get_last_access(user), str) else get_last_access(user).strftime(
                        constants.DATE_FORMAT),
                    '',
                    '',
                    user['CreateDate'].strftime(constants.DATE_FORMAT),
                    datetime.now().strftime(constants.DATE_FORMAT)
                ))
            # [test] crear o actualizar usuarios en dynamodb
            for user in user_list:
                user_exists = users.user_exists(user.account_id, user.username)
                if user_exists:
                    print(f"{user.username} existe!")
                    users.update_user(user)
                else:
                    users.add_user(user)
                    print(f"{user.username} creado!")
        if event_number == 1:
            # [staging] inhabilitar access keys y eliminar password
            [delete_password_and_key(z_user['UserName'], account_id) for z_user in list_zombie_users()]
        if event_number == 2:
            # [prod] elimina usuarios inactivos en dynamodb
            for user in users_to_delete:
                difference = datetime.now().replace(tzinfo=None) - datetime.strptime(user['inactive_at'],
                                                                                     constants.DATE_FORMAT).replace(
                    tzinfo=None)
                if difference.days >= constants.INACTIVE_DAYS_TO_DELETE:
                    print(f"Eliminando {user['username']}")
                    try:
                        delete_user(user['username'], account_id)
                    except:
                        print(f"Error eliminating {user['username']}")

    return "Lambda executed successfully..."

# if __name__ == "__main__":
#     # user1 = User('Test', '', '', '', '', '')
#     # db.create_user(user1)
#     while 1:
#         option = int(input(
#             "\nEscriba el numero de la opcion y presione enter: \n"
#             "1. Listar usuarios con ultimo acceso\n"
#             "2. Eliminar password y dehabilitar access keys\n"
#             "3. Listar usuarios con inactividad 4 dias\n"
#             "4. Eliminar usuarios inactivos\n"
#             "5. Guardar usuarios en la base de datos\n"
#             "6. Listar usuarios inactivos en dynamodb\n"
#             "7. Crear tabla en dynamodb\n"
#             "8. Guardar usuarios en dynamodb\n"
#             "9. Obtener usuarios de dynamodb\n"
#             "10. Asumir rol en otra cuenta\n"
#         ))
#         users1 = list_users()
#         zombie_users = list_zombie_users()
#
#         user_list = []
#         account_id = sts.get_caller_identity().get('Account')
#         # users = [User(user['UserName'], get_last_access(user['UserName']).strftime("%m/%d/%Y, %H:%M:%S"), datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), user['CreatedDate'], datetime.now().strftime("%m/%d/%Y, %H:%M:%S")) for user in users]
#         for user in users1:
#             user_list.append(User(
#                 account_id,
#                 user['UserName'],
#                 get_last_access(user) if isinstance(get_last_access(user), str) else get_last_access(user).strftime(
#                     constants.DATE_FORMAT),
#                 '',
#                 '',
#                 user['CreateDate'].strftime(constants.DATE_FORMAT),
#                 datetime.now().strftime(constants.DATE_FORMAT)
#             ))
#
#         if option == 1:
#             [print(f"{i['UserName']}\nUltimo acceso: {get_last_access(i)}") for i in users1]
#         elif option == 2:
#             if users.exists('users'):
#                 print('Tabla users ya existe!')
#             else:
#                 users.create_table('users')
#             [delete_password_and_key(z_user['UserName'], account_id) for z_user in list_zombie_users()]
#         elif option == 3:
#             [print(i['UserName']) for i in list_zombie_users()]
#         elif option == 4:
#             users.exists('users')
#             inactive_users = users.get_inactive_users()
#             for user in inactive_users:
#                 difference = datetime.now().replace(tzinfo=None) - datetime.strptime(user['inactive_at'],
#                                                                                      constants.DATE_FORMAT).replace(
#                     tzinfo=None)
#                 if difference.days > constants.INACTIVE_DAYS_TO_DELETE:
#                     print(f"Eliminando {user['username']}")
#                     delete_user(user['username'])
#         elif option == 5:
#             print(None)
#             # [db.create_user(user) for user in user_list]
#         elif option == 6:
#             users.exists('users')
#             print(users.get_inactive_users())
#             # print(f"Base de datos: {db.get_users()}")
#         elif option == 7:
#             print(users.create_table('users'))
#         elif option == 8:
#             if users.exists('users'):
#                 print('Tabla users ya existe!')
#             else:
#                 users.create_table('users')
#             for user in user_list:
#                 user_exists = users.user_exists(user.account_id, user.username)
#                 if user_exists:
#                     print(f"{user.username} existe!")
#                     users.update_user(user)
#                 else:
#                     users.add_user(user)
#                     print(f"{user.username} creado!")
#         elif option == 9:
#             print(users.scan_users())
#         elif option == 10:
#             session = role_arn_to_session(
#                 RoleArn=f"arn:aws:iam::{account_ids[0]}:role/iam-list-user-role-tem",
#                 RoleSessionName='test-t'
#             )
#             iam = session.client('iam')
#             sts = session.client('sts')
#         else:
#             print("\nDigite una opcion valida!!! \n")
