"""
Computer Service Company - Main Flask Application
Tech stack: Flask + Supabase (Postgres + Auth) + Vanilla HTML/CSS/JS
Hosting: Vercel

This is the FUNCTIONAL LAYOUT stage: every route works end-to-end against
Supabase, using minimal styling. Once we confirm the flows are correct,
we polish the templates/CSS.
"""

import os
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # server-only, bypasses RLS

# Public client (respects RLS) - used for normal user actions
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Admin client (service role) - used ONLY for admin dashboard operations
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# Helpers / decorators
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id") or not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", user=session.get("user_name"))


@app.route("/ecommerce")
def ecommerce():
    """Public product listing - anyone can view, no login needed to browse."""
    products = supabase.table("products").select("*").eq("is_active", True).execute()
    return render_template("ecommerce.html", products=products.data, user=session.get("user_name"))


@app.route("/product/<product_id>")
def product_detail(product_id):
    product = supabase.table("products").select("*").eq("id", product_id).single().execute()
    return render_template("product_detail.html", product=product.data, user=session.get("user_name"))


@app.route("/blog")
def blog():
    posts = supabase.table("blog_posts").select("*").eq("is_published", True).order("created_at", desc=True).execute()
    return render_template("blog.html", posts=posts.data, user=session.get("user_name"))


@app.route("/blog/<post_id>")
def blog_detail(post_id):
    post = supabase.table("blog_posts").select("*").eq("id", post_id).single().execute()
    return render_template("blog_detail.html", post=post.data, user=session.get("user_name"))


@app.route("/community")
@login_required
def community():
    """Community requires login to post, but let's allow viewing publicly too."""
    posts = supabase.table("community_posts").select("*, profiles(full_name)").order("created_at", desc=True).execute()
    return render_template("community.html", posts=posts.data, user=session.get("user_name"))


@app.route("/community/new", methods=["POST"])
@login_required
def community_new():
    title = request.form.get("title")
    content = request.form.get("content")
    supabase.table("community_posts").insert({
        "title": title,
        "content": content,
        "user_id": session["user_id"],
    }).execute()
    flash("Post published!", "success")
    return redirect(url_for("community"))


# ---------------------------------------------------------------------------
# Auth: Signup / Login / Logout
# ---------------------------------------------------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    full_name = request.form.get("full_name")
    email = request.form.get("email")
    password = request.form.get("password")
    phone = request.form.get("phone")

    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
        })
        new_user = auth_response.user
        if new_user:
            # Create a matching row in profiles table
            supabase_admin.table("profiles").insert({
                "id": new_user.id,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "role": "customer",
            }).execute()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
    except Exception as e:
        flash(f"Signup failed: {str(e)}", "danger")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        user = auth_response.user

        profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute()

        session["user_id"] = user.id
        session["user_name"] = profile.data.get("full_name")
        session["is_admin"] = profile.data.get("role") == "admin"

        flash("Logged in successfully!", "success")
        if session["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("index"))

    except Exception as e:
        flash("Invalid email or password.", "danger")
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Enquiries / Orders (public submits, admin reads)
# ---------------------------------------------------------------------------

@app.route("/enquiry/<product_id>", methods=["POST"])
def send_enquiry(product_id):
    """Handles both 'Send Enquiry' and 'Order Now' buttons."""
    message_type = request.form.get("type", "enquiry")  # enquiry | order
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    message = request.form.get("message")
    quantity = request.form.get("quantity", 1)

    supabase_admin.table("enquiries").insert({
        "product_id": product_id,
        "user_id": session.get("user_id"),
        "name": name,
        "email": email,
        "phone": phone,
        "message": message,
        "quantity": quantity,
        "type": message_type,
        "status": "new",
    }).execute()

    flash("Your request has been sent! We'll contact you soon.", "success")
    return redirect(url_for("product_detail", product_id=product_id))


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    products = supabase_admin.table("products").select("*").execute()
    enquiries = supabase_admin.table("enquiries").select("*").order("created_at", desc=True).execute()
    stats = {
        "total_products": len(products.data),
        "new_enquiries": len([e for e in enquiries.data if e["status"] == "new"]),
        "total_enquiries": len(enquiries.data),
    }
    return render_template("admin_dashboard.html", products=products.data,
                            enquiries=enquiries.data, stats=stats, user=session.get("user_name"))


@app.route("/admin/product/add", methods=["POST"])
@admin_required
def admin_add_product():
    supabase_admin.table("products").insert({
        "name": request.form.get("name"),
        "description": request.form.get("description"),
        "price": request.form.get("price"),
        "category": request.form.get("category"),
        "image_url": request.form.get("image_url"),
        "stock": request.form.get("stock", 0),
        "is_active": True,
    }).execute()
    flash("Product added.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/edit/<product_id>", methods=["POST"])
@admin_required
def admin_edit_product(product_id):
    supabase_admin.table("products").update({
        "name": request.form.get("name"),
        "description": request.form.get("description"),
        "price": request.form.get("price"),
        "category": request.form.get("category"),
        "image_url": request.form.get("image_url"),
        "stock": request.form.get("stock", 0),
        "is_active": request.form.get("is_active") == "on",
    }).eq("id", product_id).execute()
    flash("Product updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/delete/<product_id>", methods=["POST"])
@admin_required
def admin_delete_product(product_id):
    supabase_admin.table("products").delete().eq("id", product_id).execute()
    flash("Product deleted.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/enquiry/<enquiry_id>/respond", methods=["POST"])
@admin_required
def admin_respond_enquiry(enquiry_id):
    """Admin marks status / adds a note. Actual email/call happens outside app,
    but we log the response note here."""
    supabase_admin.table("enquiries").update({
        "status": request.form.get("status", "contacted"),
        "admin_note": request.form.get("admin_note"),
        "responded_at": datetime.utcnow().isoformat(),
    }).eq("id", enquiry_id).execute()
    flash("Enquiry updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/blog/add", methods=["POST"])
@admin_required
def admin_add_blog():
    supabase_admin.table("blog_posts").insert({
        "title": request.form.get("title"),
        "content": request.form.get("content"),
        "cover_image": request.form.get("cover_image"),
        "author_id": session["user_id"],
        "is_published": True,
    }).execute()
    flash("Blog post published.", "success")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# JSON API (optional, handy for JS-driven UI later)
# ---------------------------------------------------------------------------

@app.route("/api/products")
def api_products():
    products = supabase.table("products").select("*").eq("is_active", True).execute()
    return jsonify(products.data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
