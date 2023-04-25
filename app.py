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
account_ids = []


# listar usuarios
def list_users():
    paginator = iam.get_paginator('list_users')
    return list(itertools.chain.from_iterable([i["Users"] for i in paginator.paginate()]))


# Listar usuarios inactivos
def list_zombie_users():
    expected_days = constants.INACTIVE_DAYS
    result = list()
    for user in list_users():
        last_access = get_last_access(user)
        if isinstance(last_access, datetime):
            difference = (datetime.now().replace(tzinfo=None) - last_access.replace(tzinfo=None)).days
            # Dias de incatividad
            if difference >= expected_days:
                result.append(user)
        if isinstance(last_access, str) and (
                datetime.now().replace(tzinfo=None) - user['CreateDate'].replace(tzinfo=None)).days > expected_days:
            result.append(user)
    return result


# Listar access keys
def list_access_keys(username):
    return iam.list_access_keys(UserName=username)


# Imprimir ultimo acceso
def get_last_access(user):
    access_keys = list_access_keys(user['UserName'])
    last_access_by_password = False
    last_access_by_key = False
    last_access = None
    if access_keys['AccessKeyMetadata']:
        try:
            last_access_by_key = iam.get_access_key_last_used(
                AccessKeyId=access_keys['AccessKeyMetadata'][0]['AccessKeyId'])['AccessKeyLastUsed']['LastUsedDate']
        except:
            pass
    if 'PasswordLastUsed' in user:
        last_access_by_password = user['PasswordLastUsed']
    if last_access is None:
        last_access = user['CreateDate']
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


def delete_password_and_key(username):
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
        users.update_user(User(username, '', datetime.now().strftime(constants.DATE_FORMAT), '', '', ''))
    except:
        print(f"Error al actualizar usuario: {username}")
    try:
        # policies = iam.list_user_policies(UserName=username)
        policies = iam.list_attached_user_policies(UserName=username)['AttachedPolicies']
        for policy in policies:
            iam.detach_user_policy(UserName=username, PolicyArn=policy['PolicyArn'])
            # iam.delete_user_policy(UserName=username, PolicyName=policy['PolicyName'])
    except:
        pass
    return response


def delete_user(username):
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
        users.update_user(User(username, '', '', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), '', ''))
        print(f"Usuario {username} eliminado")
    except:
        print(f"Error al eliminar el usuario: {username}")


if __name__ == "__main__":
    # user1 = User('Test', '', '', '', '', '')
    # db.create_user(user1)
    while 1:
        option = int(input(
            "\nEscriba el numero de la opcion y presione enter: \n"
            "1. Listar usuarios con ultimo acceso\n"
            "2. Eliminar password y dehabilitar access keys\n"
            "3. Listar usuarios con inactividad 4 dias\n"
            "4. Eliminar usuarios inactivos\n"
            "5. Guardar usuarios en la base de datos\n"
            "6. Listar usuarios inactivos en dynamodb\n"
            "7. Crear tabla en dynamodb\n"
            "8. Guardar usuarios en dynamodb\n"
            "9. Obtener usuarios de dynamodb\n"
        ))
        users1 = list_users()
        zombie_users = list_zombie_users()

        user_list = []
        account_id = sts.get_caller_identity().get('Account')
        # users = [User(user['UserName'], get_last_access(user['UserName']).strftime("%m/%d/%Y, %H:%M:%S"), datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), user['CreatedDate'], datetime.now().strftime("%m/%d/%Y, %H:%M:%S")) for user in users]
        for user in users1:
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

        if option == 1:
            [print(f"{i['UserName']}\nUltimo acceso: {get_last_access(i)}") for i in users1]
        elif option == 2:
            [delete_password_and_key(z_user['UserName']) for z_user in list_zombie_users()]
        elif option == 3:
            [print(i['UserName']) for i in list_zombie_users()]
        elif option == 4:
            users.exists('users')
            inactive_users = users.get_inactive_users()
            for user in inactive_users:
                difference = datetime.now().replace(tzinfo=None) - datetime.strptime(user['inactive_at'],
                                                                                     constants.DATE_FORMAT).replace(
                    tzinfo=None)
                if difference.days > constants.INACTIVE_DAYS_TO_DELETE:
                    print(f"Eliminando {user['username']}")
                    delete_user(user['username'])
        elif option == 5:
            print(None)
            # [db.create_user(user) for user in user_list]
        elif option == 6:
            users.exists('users')
            print(users.get_inactive_users())
            # print(f"Base de datos: {db.get_users()}")
        elif option == 7:
            print(users.create_table('users'))
        elif option == 8:
            if users.exists('users'):
                print('Tabla users ya existe!')
            else:
                users.create_table('users')
            for user in user_list:
                user_exists = users.user_exists(user.account_id, user.username)
                if user_exists:
                    print(f"{user.username} existe!")
                    users.update_user(user)
                else:
                    users.add_user(user)
                    print(f"{user.username} creado!")
        elif option == 9:
            print(users.scan_users())
        else:
            print("\nDigite una opcion valida!!! \n")


def role_arn_to_session(**args):
    client = boto3.client("sts")
    response = client.assume_role(**args)
    return boto3.Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )


def lambda_handler(event, context):
    # validar instancia de la tabla (requerido)
    if users.exists('users'):
        print('Tabla users ya existe!')
    else:
        users.create_table('users')
    events = {
        'test': 0,
        'staging': 1,
        'prod': 2
    }
    event = event['detail']['mode']
    if event in list(dict.fromkeys(events)):
        event_number = events[event]

    global iam
    for account in account_ids:
        session = role_arn_to_session(
            RoleArn=f'arn:aws:iam::{account}:role/iam-list-user-role-tem',
            RoleSessionName=f'lambda-cleaner-session-{account}'
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
        elif event_number >= 1:
            # [staging] inhabilitar access keys y eliminar password
            [delete_password_and_key(z_user['UserName']) for z_user in list_zombie_users()]
        elif event_number == 2:
            # [prod] elimina usuarios inactivos en dynamodb
            for user in users_to_delete:
                difference = datetime.now().replace(tzinfo=None) - datetime.strptime(user['inactive_at'],
                                                                                     constants.DATE_FORMAT).replace(
                    tzinfo=None)
                if difference.days > constants.INACTIVE_DAYS_TO_DELETE:
                    print(f"Eliminando {user['username']}")
                    delete_user(user['username'])
        else:
            return "Evento no valido!"

    return "Lambda executed successfully..."
    # user_list = []
    # users_to_delete = users.get_inactive_users()
    # for user in list_users():
    #     user_list.append(User(
    #         account_id,
    #         user['UserName'],
    #         get_last_access(user) if isinstance(get_last_access(user), str) else get_last_access(user).strftime(
    #             constants.DATE_FORMAT),
    #         '',
    #         '',
    #         user['CreateDate'].strftime(constants.DATE_FORMAT),
    #         datetime.now().strftime(constants.DATE_FORMAT)
    #     ))
    # for user in user_list:
    #     user_exists = users.user_exists(user.username)
    #     if user_exists:
    #         print(f"{user.username} existe!")
    #         users.update_user(user)
    #     else:
    #         users.add_user(user)
    #         print(f"{user.username} creado!")
    # [delete_password_and_key(z_user['UserName']) for z_user in list_zombie_users()]
    # for user in users_to_delete:
    #     difference = datetime.now().replace(tzinfo=None) - datetime.strptime(user['inactive_at'],
    #                                                                          constants.DATE_FORMAT).replace(
    #         tzinfo=None)
    #     if difference.days > constants.INACTIVE_DAYS_TO_DELETE:
    #         print(f"Eliminando {user['username']}")
    #         delete_user(user['username'])

