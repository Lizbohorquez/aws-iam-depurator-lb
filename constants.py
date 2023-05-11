"""
Módulo constants: define las constantes utilizadas en la función Lambda.

DATE_FORMAT: formato de fecha utilizado en la función.
INACTIVE_DAYS: cantidad de días para que un usuario sea considerado inactivo.
INACTIVE_DAYS_TO_DELETE: cantidad de días para que un usuario inactivo sea eliminado.
"""
DATE_FORMAT = "%m/%d/%Y, %H:%M:%S"
INACTIVE_DAYS = 30
INACTIVE_DAYS_TO_DELETE = 7

# boto3.client('sts').get_caller_identity().get('Account')