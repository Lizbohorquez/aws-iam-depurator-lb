from aws_solutions_constructs.aws_eventbridge_lambda import EventbridgeToLambda, EventbridgeToLambdaProps
from aws_cdk import (
    aws_lambda as _lambda,
    aws_events as events,
    Duration,
    Stack
)
from constructs import Construct


class CdkEventBridgeLambdaStack(Stack):

    def __init__(self, scope: Construct, id: str, lambda_function, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        EventbridgeToLambda(self, 'test-eventbridge-lambda',
                            existing_lambda_obj=lambda_function,
                            # lambda_function_props=_lambda.FunctionProps(
                            #     code=_lambda.Code.from_asset('lambda'),
                            #     runtime=_lambda.Runtime.PYTHON_3_9,
                            #     handler='index.handler'
                            # ),
                            event_rule_props=events.RuleProps(
                                schedule=events.Schedule.rate(
                                    Duration.minutes(5))
                            ))
