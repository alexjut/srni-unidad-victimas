from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auditoria", "0003_alter_logacceso_accion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="logacceso",
            name="accion",
            field=models.CharField(
                choices=[
                    ("LOGIN", "Inicio de sesión"),
                    ("LOGOUT", "Cierre de sesión"),
                    ("LOGIN_FALLIDO", "Intento de login fallido"),
                    ("BUSQUEDA_RNI", "Búsqueda en el RNI"),
                    ("VER_VICTIMA", "Vista de datos de víctima"),
                    ("CREAR_HOGAR", "Creación de hogar"),
                    ("AGREGAR_MIEMBRO", "Miembro agregado al hogar"),
                    ("RESPONDER_PREGUNTA", "Respuesta a pregunta"),
                    ("FINALIZAR_ENCUESTA", "Encuesta finalizada"),
                    ("EXPORTAR", "Exportación de datos"),
                    ("CAMBIO_PASSWORD", "Cambio de contraseña"),
                    ("CAMBIO_USUARIO", "Modificación de usuario"),
                    ("ACCESO_DENEGADO", "Acceso denegado"),
                    ("LLAMADA_GEMINI", "Llamada al asistente IA Gemini"),
                    ("CONSENTIMIENTO_IA", "Consentimiento de uso de IA"),
                    ("DESCARGA_APK", "Descarga de APK móvil"),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
    ]
