import datetime
import logging

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

date_format = "%m/%d/%Y, %H:%M:%S"


class Users:
    """Encapsulates an Amazon DynamoDB table of user data."""

    def __init__(self, dyn_resource):
        """
        :param dyn_resource: A Boto3 DynamoDB resource.
        """
        self.dyn_resource = dyn_resource
        self.table = None

    def create_table(self, table_name):
        """
        Create a table with table_name as name.
        :param table_name: The name of the table to create.
        :return: Table info in dict; otherwise, raise a error.
        """
        try:
            self.table = self.dyn_resource.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'account_id', 'KeyType': 'HASH'},  # Partition key
                    {'AttributeName': 'username', 'KeyType': 'RANGE'}  # Sort key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'account_id', 'AttributeType': 'S'},
                    {'AttributeName': 'username', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1})
            self.table.wait_until_exists()
        except ClientError as err:
            logger.error(
                "Couldn't create table %s. Here's why: %s: %s", table_name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            return self.table

    def add_user(self, user):
        """
        Add a user to table.
        :param user: A object of User class.
        :return: user details if added; otherwise, raise a error.
        """
        try:
            self.table.put_item(
                Item={
                    'account_id': user.account_id,
                    'username': user.username,
                    'last_access': user.last_access,
                    'inactive_at': user.inactive_at,
                    'delete_at': user.delete_at,
                    'created_at': user.created_at,
                    'updated_at': user.updated_at
                })
        except ClientError as err:
            logger.error(
                "Couldn't add user %s to table %s. Here's why: %s: %s",
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

    def exists(self, table_name):
        """
        Determines whether a table exists. As a side effect, stores the table in
        a member variable.
        :param table_name: The name of the table to check.
        :return: True when the table exists; otherwise, False.
        """
        try:
            table = self.dyn_resource.Table(table_name)
            table.load()
            exists = True
        except ClientError as err:
            if err.response['Error']['Code'] == 'ResourceNotFoundException':
                exists = False
            else:
                logger.error(
                    "Couldn't check for existence of %s. Here's why: %s: %s",
                    table_name,
                    err.response['Error']['Code'], err.response['Error']['Message'])
                raise
        else:
            self.table = table
        return exists

    def scan_users(self, args={}):
        """
        Get all users in table.
        :param args: Dict with filters.
        :return: users in table; otherwise, raise a error.
        """
        users = []
        scan_kwargs = args
        # 'FilterExpression': Key('username')
        # 'ProjectionExpression': "#yr, title, info.rating",
        # 'ExpressionAttributeNames': {"#yr": "year"}}
        try:
            done = False
            start_key = None
            while not done:
                if start_key:
                    scan_kwargs['ExclusiveStartKey'] = start_key
                response = self.table.scan(**scan_kwargs)
                users.extend(response.get('Items', []))
                start_key = response.get('LastEvaluatedKey', None)
                done = start_key is None
        except ClientError as err:
            logger.error(
                "Couldn't scan for users. Here's why: %s: %s",
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

        return users

    def get_inactive_users(self):
        """
        Get all of inactive users in table.
        :return: users in table with inactive_at field not empty; otherwise, raise a error.
        """
        return self.scan_users({
            'FilterExpression': 'inactive_at <> :is_empty AND delete_at = :is_empty',
            'ExpressionAttributeValues': {
                ':is_empty': ''
            }
        })

    def update_user(self, user):
        """
        Update a user in table.
        :param user: A object of User class to update.
        :return: response attributes if updated; otherwise, raise a error.
        """
        try:
            if user.last_access != '':
                response = self.table.update_item(
                    Key={'account_id': user.account_id, 'username': user.username},
                    UpdateExpression="set last_access=:l, created_at=:c, updated_at=:n",
                    ExpressionAttributeValues={
                        ':l': user.last_access,
                        ':n': datetime.datetime.now().strftime(date_format),
                        ':c': user.created_at,
                    },
                    ReturnValues="UPDATED_NEW"
                )
            if user.inactive_at != '':
                response = self.table.update_item(
                    Key={'account_id': user.account_id, 'username': user.username},
                    UpdateExpression="set inactive_at=:i, updated_at=:n",
                    ExpressionAttributeValues={
                        ':i': user.inactive_at, ':n': datetime.datetime.now().strftime(date_format)},
                    ReturnValues="UPDATED_NEW"
                )
            if user.delete_at != '':
                response = self.table.update_item(
                    Key={'account_id': user.account_id, 'username': user.username},
                    UpdateExpression="set delete_at=:d, updated_at=:n",
                    ExpressionAttributeValues={
                        ':d': user.delete_at, ':n': datetime.datetime.now().strftime(date_format)},
                    ReturnValues="UPDATED_NEW"
                )
        except ClientError as err:
            logger.error(
                "Couldn't update user %s in table %s. Here's why: %s: %s", self.table.name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            return response['Attributes']

    def user_exists(self, account_id, username):
        """
        Determines whether a user exists in table.
        :param account_id: id of aws account where user owns.
        :param username: username of user to search.
        :return: True when the table exists; otherwise, False.
        """
        try:
            response = self.table.query(KeyConditionExpression=Key('account_id').eq(account_id) & Key('username').eq(username))
            if len(response['Items']) > 0:
                response = True
            else:
                response = False
        except ClientError as err:
            logger.error(
                "Couldn't query for movies released in %s. Here's why: %s: %s",
                err.response['Error']['Code'], err.response['Error']['Message'])
        else:
            return response
