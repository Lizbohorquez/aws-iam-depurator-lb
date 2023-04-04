# CLEANUP INACTIVE IAM USERS

This program delete all incative users in iam service.

```python
pyhton3 main.py
```

## Workflow
* Actualizar la base de datos(registrar nuevos usuarios, actualiza last_access)
* Inhabilitar usuarios fuera del umbral de inactividad
* Eliminar usuarios inhabilitados por mas de 7 dias
* Actualizar usuarios inhabilitados y eliminados