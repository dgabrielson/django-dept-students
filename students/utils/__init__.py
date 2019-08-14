from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


def admin_history(object, message, action_flag, user):
    def _guess_action_flag(msg):
        if "[" in msg:
            msg = msg.rsplit("[", 1)[0]  # ignore annotation
        if "create" in msg.lower():
            action_flag = ADDITION
        elif "added" in msg.lower():
            action_flag = ADDITION
        else:
            action_flag = CHANGE
        return action_flag

    def _get_user_id(user):
        if user is None:
            # Best choice -- AnonymousUser installed by django-guardian
            try:
                user = User.objects.get(username="AnonymousUser")
            except User.DoesNotExist:
                pass
        if user is None:
            # Second best choice (poor choice)
            #   -- Lowest PK superuser
            user_id = min(
                User.objects.filter(is_superuser=True).values_list("id", flat=True)
            )
        else:
            user_id = user.pk
        return user_id

    # admin_history begins

    user_id = _get_user_id(user)
    if action_flag is None:
        action_flag = _guess_action_flag(message)

    return LogEntry.objects.log_action(
        user_id=user_id,
        content_type_id=ContentType.objects.get_for_model(object).pk,
        object_id=object.pk,
        object_repr=str(object),
        action_flag=action_flag,
        change_message=message,
    )
