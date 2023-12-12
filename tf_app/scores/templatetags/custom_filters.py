from django import template

register = template.Library()

# get a value given the key filter
def get_value(dictionary, key):
    return dictionary[key]

register.filter('get_value', get_value)