import json
import re

import requests

from blog.models import BlogPost
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from products.models import Category, Product
from products.tasks import get_queue, send_mail

from .forms import ContactForm, SubscribeForm, UniversalForm
from .models import Subscribe


def site_verify(request):
    google_recaptcha_verify = "https://www.google.com/recaptcha/api/siteverify"
    google_recaptcha_secret = settings.RECAPTCHA_SECRET_KEY
    # get token from request.body
    token = json.loads(request.body).get("token", False)
    if not token:
        return JsonResponse({"error": "Token is required."}, status=400)
    data = {"secret": google_recaptcha_secret, "response": token}
    r = requests.post(google_recaptcha_verify, data=data)
    result = r.json()
    if result.get("success", False) and result.get("score", 0) > 0.5:
        return JsonResponse({"status": "success"}, status=200)
    else:
        return JsonResponse({"status": "Invalid token."}, status=400)


# Create your views here.
def contact(request):
    context = {}
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            send_mail_contact(form)
            messages.success(request, "Contact request submitted successfully.")
            return redirect(reverse("contact"))
        else:
            context["form"] = form
            context["formerrors"] = ", ".join([x[0] for _, x in form.errors.items()])
            messages.error(request, context["formerrors"])
            return redirect(reverse("contact"))

    if request.method == "GET":
        context = {}
        form = ContactForm()
        context["form"] = form
        context["cls_name"] = form.__class__.__name__
        return render(request, "contact.html", context)


# Create your views here.
def universal(request):
    context = {}
    if request.method == "POST":
        try:
            form = UniversalForm(request.POST, request.FILES)
            if form.is_valid():
                    form.save()
                    send_mail_universal(form)
                    messages.success(request, "Universal request submitted successfully.")
                    return redirect(reverse("universalplumbing"))

            else:
                context["form"] = form
                context["formerrors"] = ", ".join([x[0] for _, x in form.errors.items()])
                messages.error(request, context["formerrors"])
                return redirect(reverse("universalplumbing"))
        except Exception as e:
            messages.error(request, str(e))
            return redirect(reverse("universalplumbing"))

    if request.method == "GET":
        context = {}
        form = UniversalForm()
        context["form"] = form
        context["cls_name"] = form.__class__.__name__
        return render(request, "universal.html", context)

def send_mail_contact(form):
    get_queue("default").enqueue(
        send_mail,
        type_mail="contact",
        email=form.cleaned_data["email_address"],
        name=form.cleaned_data["name"],
        subject=form.cleaned_data["subject"],
        phone=form.cleaned_data["phone_number"],
        message=form.cleaned_data["message"],
        order_number=form.cleaned_data["order_number"],
    )


def send_mail_universal(form):
    try:
        get_queue("default").enqueue(
            send_mail,
            type_mail="universal",
            towel_rail=form.cleaned_data["towel_rail"],
            name=form.cleaned_data["name"],
            company_name=form.cleaned_data["company_name"],
            shipping_address=form.cleaned_data["shipping_address"],
            email=form.cleaned_data["email_address"],
            phone=form.cleaned_data["phone_number"],
            proof_purchase=form.cleaned_data["proof_purchase"],
        )
        # send_mail(
        #     type_mail="universal",
        #     towel_rail=form.cleaned_data["towel_rail"],
        #     name=form.cleaned_data["name"],
        #     company_name=form.cleaned_data["company_name"],
        #     shipping_address=form.cleaned_data["shipping_address"],
        #     email=form.cleaned_data["email_address"],
        #     phone=form.cleaned_data["phone_number"],
        #     proof_purchase=form.cleaned_data["proof_purchase"],
        # )
    except Exception as e:
        print("Error: ", e)
        pass



def contact_post(request):
    if request.method == "POST":
        path = request.POST["current_path"]
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            send_mail_contact(form)
            messages.success(request, "%s submitted successfully." % form.cleaned_data["subject"])

            return redirect("/" + path)
        else:
            error = ", ".join([x[0] for _, x in form.errors.items()])
            messages.error(request, error)
            return redirect("/" + path)

    if request.method == "GET":
        return redirect("/contact")


def subscribe(request):
    if request.method == "POST":
        if request.POST:
            data_post = request.POST
        else:
            data_post = json.loads(request.body)
        context = {}
        form = SubscribeForm(data_post)
        if form.is_valid():
            exist_sub = Subscribe.objects.filter(email_address=data_post["email_address"]).exists()
            if exist_sub:
                messages.error(
                    request,
                    "The email address {email} is already subscribed to receive our newsletter.".format(
                        email=data_post["email_address"]
                    ),
                )
                context.update({"is_error": True})
            else:
                form.save()
                get_queue("default").enqueue(
                    send_mail,
                    type_mail="subscribe",
                    email=form.cleaned_data["email_address"],
                    subject="Subscription success",
                )
                messages.success(
                    request,
                    "Thank you for joining our mailing list. You'll be sent the next issue of our newsletter shortly.",
                )
                context.update({"is_error": False})
            # return JsonResponse({"is_error": False, "msg": "Thanks - Subscribed Successfully!"})
        else:
            error = ", ".join([x[0] for _, x in form.errors.items()])
            messages.error(request, error)
            context.update({"is_error": True})
            # return JsonResponse({"is_error": True, "msg": error})
        return render(request, "subscribe.html", context=context)


def generic_staticpage_content():
    """Returns standard blog / products for
    rendering in a flatpage context"""
    blogs = BlogPost.get_all_cached()
    blogs = []
    prods = Product.get_featured_products()
    brand_objs = []
    return {"blogs": blogs, "prods": prods, "brand_objs": brand_objs}


def about(request):
    context = generic_staticpage_content()
    return render(request, "about.html", context)


def serenity(request):
    context = generic_staticpage_content()
    return render(request, "serenity.html", context)


def harrow(request):
    context = generic_staticpage_content()
    return render(request, "harrow.html", context)


def francisco(request):
    context = generic_staticpage_content()
    return render(request, "francisco.html", context)


def porscha(request):
    context = generic_staticpage_content()
    return render(request, "porscha.html", context)


def oxley(request):
    context = generic_staticpage_content()
    return render(request, "oxley.html", context)


# def laundry(request):
#     context = generic_staticpage_content()
#     return render(request, "laundry.html", context)


def bathroom_planner(request):
    context = generic_staticpage_content()
    return render(request, "bathroom-planner.html", context)


# laundry-planner url
def laundry_planner(request):
    context = generic_staticpage_content()
    return render(request, "laundry-planner.html", context)


def video(request):
    context = generic_staticpage_content()
    return render(request, "video.html", context)


def index(request):
    context = generic_staticpage_content()
    context["current_path"] = request.path.strip("/")
    context["cls_name"] = ContactForm().__class__.__name__
    return render(request, "new-home.html", context)


def project(request):
    context = generic_staticpage_content()

    projects = BlogPost.objects.all()
    context["projects"] = projects

    return render(request, "project.html", context)


def project_details(request, slug):
    context = generic_staticpage_content()

    project = get_object_or_404(BlogPost, slug=slug)
    context["project"] = project
    return render(request, "project-details.html", context)


def catalogues(request):
    context = generic_staticpage_content()
    return render(request, "catalogues.html", context)


def terms_of_trade(request):
    context = generic_staticpage_content()
    return render(request, "terms-of-trade.html", context)


def return_policy(request):
    context = generic_staticpage_content()
    return render(request, "return-policy.html", context)


def about_us(request):
    context = generic_staticpage_content()
    return render(request, "about-us.html", context)


def concept_showroom(request):
    context = generic_staticpage_content()
    return render(request, "concept-showroom.html", context)


def not_found_404(request):
    context = generic_staticpage_content()
    return render(request, "404.html", context)


def vista_range(request):
    context = {"generic": generic_staticpage_content()}
    return render(request, "vista-range.html")


# site maps view
def site_map(request):
    cat = (Category.get_category_tree()[:4],)
    # print(cat)
    context = {"generic": generic_staticpage_content(), "cat": cat}
    return render(request, "site-map.html", context)


# site maps categories
def site_map_category(request):
    cat = Category.get_category_tree()
    context = {"generic": generic_staticpage_content(), "cat": cat}
    return render(request, "site-map-categories.html", context)
