def generate_upload_path(instance, filename):
    app_name = instance._meta.app_label.lower()
    modified_filename = f'{app_name}/{filename}'

    return modified_filename