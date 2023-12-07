import uuid
import boto3
import os
from django.shortcuts import render, redirect
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView, DetailView
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Cat, Toy, Photo
from .forms import FeedingForm

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

@login_required
def cats_index(request):
    cats = Cat.objects.filter(user=request.user) # retrieve all cats
    return render(request, 'cats/index.html', {
        'cats': cats
    })

@login_required
def cats_detail(request, cat_id):
    cat = Cat.objects.get(id=cat_id) # retrieve a single cat
    id_list = cat.toys.values_list('id') # get the ids of the toys the cat doesn't have
    toys_cat_doesnt_have = Toy.objects.exclude(id__in=id_list) # get the toys the cat doesn't have
    feeding_form = FeedingForm() # instantiate FeedingForm to be rendered in the template
    print(request.user.id)
    print(cat.user.id)
    return render(request, 'cats/detail.html', {
        'cat': cat,
        'feeding_form': feeding_form, # pass the feeding_form as context
        'toys': toys_cat_doesnt_have # pass the toys_cat_doesnt_have as context
    })

@login_required
def add_photo(request, cat_id):
    # photo-file will be the "name" attribute on the <input type="file">
    photo_file = request.FILES.get('photo-file', None)
    if photo_file:
        s3 = boto3.client('s3')
        # need a unique "key" for S3 / needs image file extension too
        key = uuid.uuid4().hex[:6] + photo_file.name[photo_file.name.rfind('.'):]
        # just in case something goes wrong
        try:
            bucket = os.environ['S3_BUCKET']
            s3.upload_fileobj(photo_file, bucket, key)
            # build the full url string
            url = f"{os.environ['S3_BASE_URL']}{bucket}/{key}"
            # we can assign to cat_id or cat (if you have a cat object)
            Photo.objects.create(url=url, cat_id=cat_id)
        except Exception as e:
            print('An error occurred uploading file to S3')
            print(e)
    return redirect('detail', cat_id=cat_id)

class CatCreate(LoginRequiredMixin, CreateView):
    model = Cat
    fields = ['name', 'breed', 'description', 'age']
    

    def form_valid(self, form):
        form.instance.user = self.request.user # set the current user as the cat's user
        add_photo(self.request)
        return super().form_valid(form) # call the parent method with the updated data

class CatUpdate(LoginRequiredMixin, UpdateView):
    model = Cat
    fields = ['name', 'breed', 'description', 'age']

class CatDelete(LoginRequiredMixin, DeleteView):
    model = Cat
    success_url = '/cats'
    
@login_required
def add_feeding(request, cat_id):
    form = FeedingForm(request.POST) # instantiate FeedingForm with data from request.POST
    if form.is_valid(): # check if the form is valid
        new_feeding = form.save(commit=False) # don't save the form to the db until it has the cat_id assigned
        new_feeding.cat_id = cat_id # assign the cat_id
        new_feeding.save() # save the now-complete form with the cat_id field assigned
    return redirect('detail', cat_id=cat_id)

class ToyList(LoginRequiredMixin, ListView):
    model = Toy

    def get_queryset(self):
        # Get the initial queryset
        queryset = super().get_queryset()

        # Apply your filtering criteria
        # For example, let's say you want to filter based on a field called 'criteria_field'
        # criteria_value = self.request.GET.get(self.request.user)  # Get the value from the URL parameter
        criteria_value = self.request.user  # Get the value from the URL parameter
        if criteria_value:
            queryset = queryset.filter(user=criteria_value)

        return queryset

class ToyDetail(LoginRequiredMixin, DetailView):
    model = Toy

class ToyCreate(LoginRequiredMixin, CreateView):
    model = Toy
    fields = ['name', 'color']

    def form_valid(self, form):
        form.instance.user = self.request.user # set the current user as the cat's user
        return super().form_valid(form) # call the parent method with the updated data

class ToyUpdate(LoginRequiredMixin, UpdateView):
    model = Toy
    fields = ['name', 'color']

class ToyDelete(LoginRequiredMixin, DeleteView):
    model = Toy
    success_url = '/toys'

@login_required
def assoc_toy(request, cat_id, toy_id):
    Cat.objects.get(id=cat_id).toys.add(toy_id) # add the toy to the cat's toys
    return redirect('detail', cat_id=cat_id) # redirect to the cat's detail page

@login_required
def unassoc_toy(request, cat_id, toy_id):
    Cat.objects.get(id=cat_id).toys.remove(toy_id) # remove the toy from the cat's toys
    return redirect('detail', cat_id=cat_id) # redirect to the cat's detail page

def signup(request):
    error_message = ''
    form = UserCreationForm(request.POST) # create a new instance of the UserCreationForm
    if request.method == 'POST': # if the form has been submitted
        if form.is_valid(): # check if the form is valid
            user = form.save() # save the new user to the db
            login(request, user) # log the user in
            return redirect('index') # redirect to the index page
        else:
            error_message = 'Invalid sign up - try again'
    # if the form hasn't been submitted, or there are errors, render the form template with error_message as context
    context = {'form': form, 'error_message': error_message}
    return render(request, 'registration/signup.html', context)