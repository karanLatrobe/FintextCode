from django.shortcuts import render, HttpResponseRedirect, redirect
from django.contrib import messages
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, UserChangeForm, UserCreationForm
)
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache

from enroll.forms import SignUP, EditUserProfileForm, EditAdminProfileForm
from django.core.mail import send_mail

# ==============================================================
# HOME
# ==============================================================

def home(request):
    if request.user.is_authenticated:
        logout(request)
    return render(request, 'home.html')


# ==============================================================
# SIGNUP
# ==============================================================
import random
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SignUP
from django.core.mail import send_mail

def sign_up(request):
    if request.method == 'POST':
        form = SignUP(request.POST)
        if form.is_valid():
            request.session['temp_user'] = form.cleaned_data
            otp = random.randint(100000, 999999)

            request.session['otp'] = otp

            send_mail(
                'Your OTP Verification',
                f'Your OTP is: {otp}',
                'yourgmail@gmail.com',
                [form.cleaned_data['email']],
                fail_silently=False,
            )

            return redirect('verify_otp')

    else:
        form = SignUP()

    return render(request, 'signup.html', {'form': form})


from django.contrib.auth.models import User

def verify_otp(request):

    # ⛔ Direct URL Access Ko Block Karna
    if 'otp' not in request.session or 'temp_user' not in request.session:
        return redirect('signup')

    if request.method == "POST":
        entered = request.POST.get('otp')
        real_otp = str(request.session.get('otp'))
        user_data = request.session.get('temp_user')

        if entered == real_otp:
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password1']
            )
            user.save()

            messages.success(request, "Account Verified Successfully!")
            
            del request.session['otp']
            del request.session['temp_user']

            return redirect('login')
        else:
            messages.error(request, "Invalid OTP. Try again.")

    return render(request, 'verify_otp.html')

# ==============================================================
# LOGIN
# ==============================================================


@never_cache
def user_login(request):

    # ❌ Logged-in user ko logout mat karo
    # ✔ Instead usse profile pe redirect karo
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = AuthenticationForm(request=request, data=request.POST)

        if form.is_valid():
            uname = form.cleaned_data['username']
            upass = form.cleaned_data['password']
            user = authenticate(username=uname, password=upass)

            if user is not None:
                login(request, user)

                # Login success email
                try:
                    send_mail(
                        subject='Login Notification',
                        message=f'User {uname} logged in successfully.',
                        from_email='karansharma89200@gmail.com',
                        recipient_list=['myquoraai89200@gmail.com'],
                        fail_silently=True,
                    )
                except:
                    pass

                messages.success(request, f"Hi {request.user.username}, Logged in successfully!")
                return redirect('profile')

        else:
            messages.error(request, "Invalid username or password.")

    else:
        form = AuthenticationForm()

    return render(request, 'userlogin.html', {'form': form})




def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # Check user exists
        if not User.objects.filter(email=email).exists():
            messages.error(request, "Email not registered!")
            return redirect("forgot_password")

        # OTP generate
        otp = random.randint(100000, 999999)

        request.session['reset_email'] = email
        request.session['reset_otp'] = otp

        # Send OTP
        send_mail(
            "Password Reset OTP",
            f"Your OTP is: {otp}",
            "karansharma89200@gmail.com",
            [email],
            fail_silently=False
        )

        return redirect("forgot_password_otp")

    return render(request, "forgot_password.html")


def forgot_password_otp(request):

    # Direct URL access block
    if 'reset_email' not in request.session:
        return redirect("forgot_password")

    if request.method == "POST":
        entered = request.POST.get("otp")
        real = str(request.session.get("reset_otp"))

        if entered == real:
            return redirect("reset_password")
        else:
            messages.error(request, "Invalid OTP!")

    return render(request, "forgot_password_otp.html")


def reset_password(request):

    # Direct URL access block
    if 'reset_email' not in request.session:
        return redirect("forgot_password")

    if request.method == "POST":
        new = request.POST.get("new_password")
        confirm = request.POST.get("confirm_password")

        if new != confirm:
            messages.error(request, "Passwords do not match!")
            return redirect("reset_password")

        email = request.session['reset_email']
        user = User.objects.get(email=email)
        user.set_password(new)
        user.save()

        del request.session['reset_email']
        del request.session['reset_otp']

        messages.success(request, "Password updated! Login now.")
        return redirect("login")

    return render(request, "reset_password.html")
# ==============================================================
# LOGOUT
# ==============================================================

def user_logout(request):
    logout(request)
    return redirect('home')


# ==============================================================
# CHANGE PASSWORD
# ==============================================================

def user_change_pass(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            PS = PasswordChangeForm(user=request.user, data=request.POST)
            if PS.is_valid():
                PS.save()
                update_session_auth_hash(request, PS.user)
                return HttpResponseRedirect('/profile/')
        else:
            PS = PasswordChangeForm(user=request.user)

        return render(request, 'changepass.html', {'form': PS})

    return HttpResponseRedirect('/login/')


# ==============================================================
# USER DETAIL (ADMIN VIEW)
# ==============================================================

def user_detail(request, id):
    if request.user.is_authenticated:
        pi = User.objects.get(pk=id)
        fm = EditAdminProfileForm(instance=pi)
        return render(request, "user_detail.html", {'form': fm})
    return HttpResponseRedirect('/login/')


# ==============================================================
# IMPORTS FOR PROFILE + PDF PROCESSING
# ==============================================================

import os
import datetime
from pathlib import Path
import pandas as pd

from django.http import HttpResponse, Http404
from django.conf import settings
from django.urls import reverse

from enroll.utils.common import process_pdf_and_return_output_path
from enroll.ModelBuildingFintext.predictor import predict_for_dataframe


# ==============================================================
# MAIN PROFILE VIEW
# ==============================================================

@never_cache
def user_profile(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/')

    name = request.user.username
    users = User.objects.all() if request.user.is_superuser else None

    rows = None
    columns = None
    download_link = None

    # ------------------ CASE 1: FILE UPLOAD ------------------
    if "uploadedFile" in request.FILES:
        pdf = request.FILES["uploadedFile"]

        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        temp_pdf = os.path.join(temp_dir, pdf.name)
        with open(temp_pdf, "wb+") as f:
            for c in pdf.chunks():
                f.write(c)

        # Extract PDF
        try:
            raw_excel_path, df = process_pdf_and_return_output_path(temp_pdf)
            df = df.fillna('-')
        except Exception as e:
            return render(request, "profile.html", {"name": name, "msg": f"PDF Processing Error: {e}"})

        # Predict
        try:
            result_df = predict_for_dataframe(df, verbose=False)
        except Exception as e:
            return render(request, "profile.html", {"name": name, "msg": f"Prediction Error: {e}"})

        # Save output
        outputs_dir = Path(__file__).resolve().parent / "utils" / "outputs"
        outputs_dir.mkdir(exist_ok=True, parents=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"predicted_{timestamp}.xlsx"
        out_full_path = outputs_dir / out_name
        result_df.to_excel(out_full_path, index=False)

        rows = result_df.to_dict(orient="records")
        columns = result_df.columns.tolist()
        download_link = f"{reverse('download_excel')}?file={out_name}"

        try:
            os.remove(temp_pdf)
        except:
            pass

        return render(request, "profile.html", {
            "name": name,
            "rows": rows,
            "columns": columns,
            "download_link": download_link,
            "users": users
        })

    # ------------------ CASE 2: EDIT PROFILE ------------------
    if request.method == "POST":
        fm = EditAdminProfileForm(request.POST, instance=request.user) if request.user.is_superuser \
            else EditUserProfileForm(request.POST, instance=request.user)

        if fm.is_valid():
            fm.save()
            messages.success(request, "Profile Updated!")
    else:
        fm = EditAdminProfileForm(instance=request.user) if request.user.is_superuser \
            else EditUserProfileForm(instance=request.user)

    return render(request, "profile.html", {
        "name": name,
        "form": fm,
        "users": users,
        "rows": rows,
        "columns": columns,
        "download_link": download_link,
    })


# ==============================================================
# DOWNLOAD EXCEL
# ==============================================================

def download_excel(request):
    fname = request.GET.get("file")

    if not fname:
        raise Http404("File missing")

    outputs_dir = Path(__file__).resolve().parent / "utils" / "outputs"
    file_path = outputs_dir / fname

    if not file_path.exists():
        raise Http404("Not found")

    with open(file_path, "rb") as f:
        data = f.read()

    try:
        file_path.unlink()
    except:
        pass

    response = HttpResponse(data, content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{fname}"'
    return response


from django.http import JsonResponse
import pandas as pd
import os, datetime
from pathlib import Path
from django.http import JsonResponse
import pandas as pd



from django.http import JsonResponse
import pandas as pd


def ajax_upload(request):
    if request.method == "POST" and request.FILES.get("uploadedFile"):
        file = request.FILES["uploadedFile"]

        # SAVE TEMP FILE
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_ajax")
        os.makedirs(temp_dir, exist_ok=True)

        temp_path = os.path.join(temp_dir, file.name)
        with open(temp_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        # ------------ PDF OR CSV HANDLE ------------
        try:
            if file.name.lower().endswith(".pdf"):
                raw_excel_path, df = process_pdf_and_return_output_path(temp_path)
            else:
                df = pd.read_csv(temp_path, on_bad_lines="skip", encoding_errors="ignore")
        except Exception as e:
            return JsonResponse({"error": f"Unable to process file: {e}"})

        df = df.fillna("-")

        # ------------ ML PREDICTION ------------
        try:
            result_df = predict_for_dataframe(df, verbose=False)
        except Exception as e:
            return JsonResponse({"error": f"Prediction Error: {e}"})

        # ------------ SAVE OUTPUT EXCEL (IMPORTANT) ------------
        outputs_dir = Path(__file__).resolve().parent / "utils" / "outputs"
        outputs_dir.mkdir(exist_ok=True, parents=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"predicted_ajax_{timestamp}.xlsx"
        out_full_path = outputs_dir / out_name
        result_df.to_excel(out_full_path, index=False)

        # RETURN JSON including excel filename
        return JsonResponse({
            "columns": list(result_df.columns),
            "rows": result_df.to_dict(orient="records"),
            "excel_file": out_name
        })

    return JsonResponse({"error": "Invalid request"})




def faq(request):
    return render(request,'FAQ.html')