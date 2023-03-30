import boto3
from datetime import datetime
import itertools
import db

from user import User

iam = boto3.client('iam')
paginator = iam.get_paginator('list_users')

date_format = "%m/%d/%Y, %H:%M:%S"


# create table if not exists
# create_table()

# listar usuarios
def list_users():
    return list(itertools.chain.from_iterable([i["Users"] for i in paginator.paginate()]))


# Listar usuarios inactivos
def list_zombie_users():
    expected_days = 4
    result = list()
    for user in list_users():
        last_access = get_last_access(user)
        if isinstance(last_access, datetime):
            difference = (datetime.now().replace(tzinfo=None) - last_access.replace(tzinfo=None)).days
            # Dias de incatividad
            if difference == expected_days:
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
    # print(user['UserName'])
    access_keys = list_access_keys(user['UserName'])
    last_access_by_password = False
    last_access_by_key = False
    last_access = None
    if access_keys['AccessKeyMetadata']:
        last_access_by_key = iam.get_access_key_last_used(
            AccessKeyId=access_keys['AccessKeyMetadata'][0]['AccessKeyId'])['AccessKeyLastUsed']['LastUsedDate']
        # print(f"Ultimo acceso por access key: {last_access_by_key}")
    if 'PasswordLastUsed' in user:
        last_access_by_password = user['PasswordLastUsed']
        # print(f"Ultimo acceso por password: {last_access_by_password}")
    if last_access is None:
        last_access = user['CreateDate']

    # print(f"Fecha de creacion del usuario: {last_access}")
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
        db.update_users([User(username, '', datetime.now().strftime(date_format), '', '', '')])
    except:
        print(f"Error al actualizar usuario: {username}")
    return response


def delete_user(username):
    access_keys = list_access_keys(username)
    try:
        # policies = iam.list_user_policies(UserName=username)
        policies = iam.list_attached_user_policies(UserName=username)['AttachedPolicies']
        for policy in policies:
            iam.detach_user_policy(UserName=username, PolicyArn=policy['PolicyArn'])
            iam.delete_user_policy(UserName=username, PolicyName=policy['PolicyName'])
    except:
        pass
    try:
        roles = iam.list_roles_for_user(UserName=username)['Roles']
        for role in roles:
            iam.remove_role_from_user(UserName=username, RoleName=role['RoleName'])
    except:
        pass
    for access_key in access_keys['AccessKeyMetadata']:
        iam.delete_access_key(UserName=username, AccessKeyId=access_key['AccessKeyId'])
    # Se elimina finalmente el usuario de IAM
    try:
        print(iam.delete_user(UserName=username))
        db.update_users([User(username, '', '', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), '', '')])
        print(f"Usuario {username} eliminado")
    except:
        print(f"Error al eliminar el usuario: {username}")


if __name__ == "__main__":
    user1 = User('Test', '', '', '', '', '')
    # db.create_user(user1)
    while 1:
        option = int(input(
            "\nEscriba el numero de la opcion y presione enter: \n"
            "1. Listar usuarios con ultimo acceso\n"
            "2. Eliminar password y dehabilitar access keys\n"
            "3. Listar usuarios con inactividad 4 dias\n"
            "4. Eliminar usuarios inactivos\n"
            "5. Guardar usuarios en la base de datos\n"
            "6. Listar usuarios en base de datos\n"
        ))
        users = list_users()
        zombie_users = list_zombie_users()
        if option == 1:
            print(users)
            [print(f"{i['UserName']}\nUltimo acceso: {get_last_access(i)}") for i in users]
        elif option == 2:
            [delete_password_and_key(z_user['UserName']) for z_user in list_zombie_users()]
        elif option == 3:
            [print(i['UserName']) for i in list_zombie_users()]
        elif option == 4:
            inactive_users = db.get_inactive_users()
            for user in inactive_users:
                difference = datetime.now().replace(tzinfo=None) - datetime.strptime(user[2], date_format).replace(
                    tzinfo=None)
                if difference.days > 1:
                    delete_user(user[0])
        elif option == 5:
            user_list = []
            # users = [User(user['UserName'], get_last_access(user['UserName']).strftime("%m/%d/%Y, %H:%M:%S"), datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), user['CreatedDate'], datetime.now().strftime("%m/%d/%Y, %H:%M:%S")) for user in users]
            for user in users:
                user_list.append(User(
                    user['UserName'],
                    get_last_access(user),
                    '',
                    '',
                    user['CreateDate'].strftime("%m/%d/%Y, %H:%M:%S"),
                    datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                ))
            [db.create_user(user) for user in user_list]
        elif option == 6:
            print(f"Base de datos: {db.get_users()}")
        else:
            print("\nDigite una opcion valida!!! \n")