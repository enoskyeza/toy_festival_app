from django.shortcuts import render

# Create your views here.
posts = [
    {
    "author": "Micheal A.",
    "title": "Blog 0ne",
    "age": 23,
    },
    {
    "author": "Tracy E.",
    "title": "Blog Two",
    "age": 20,
    }
]

def home(request):
    context = {
        'posts': posts
    }
    return render(request, 'reg/home.html', context)