from django import template

register = template.Library()

def get_value(dictionary, key):
    return dictionary[key]

register.filter('get_value', get_value)