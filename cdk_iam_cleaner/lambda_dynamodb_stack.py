from aws_solutions_constructs.aws_lambda_dynamodb import LambdaToDynamoDBProps, LambdaToDynamoDB
from aws_cdk import (
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    Stack
)
from constructs import Construct
from lambda_main import constants


class CdkLambdaDynamoDBStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        LambdaToDynamoDB(self, 'iam-cleaner-function',
                         lambda_function_props=_lambda.FunctionProps(
                             code=_lambda.Code.from_asset(
                                 'lambda_main'),
                             runtime=_lambda.Runtime.PYTHON_3_9,
                             handler='app.lambda_handler',
                             tracing=_lambda.Tracing.DISABLED,
                             initial_policy=[
                                 iam.PolicyStatement(
                                     effect=iam.Effect.ALLOW,
                                     actions=["sts:AssumeRole"],
                                     resources=[f"arn:aws:iam::*:role/{constants.ASSUME_ROLE}"]
                                 )
                             ]

                         ),
                         dynamo_table_props=dynamodb.TableProps(
                             table_name=constants.TABLE_NAME,
                             partition_key={
                                 'name': 'account_id',
                                 'type': dynamodb.AttributeType.STRING
                             },
                             sort_key={
                                 'name': 'username',
                                 'type': dynamodb.AttributeType.STRING
                             },
                             billing_mode=dynamodb.BillingMode.PROVISIONED,
                             read_capacity=1,
                             write_capacity=1
                         )
                         )
