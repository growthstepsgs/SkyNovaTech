"""
Sky Nova Tech - Main Flask Application
Tech stack: Flask + Supabase (Postgres + Auth + Storage) + Vanilla HTML/CSS/JS
Hosting: Vercel
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
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # server-only, bypasses RLS

# Public client (respects RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
# Admin client (service role) - admin operations only
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Image uploads go to Supabase Storage (Vercel's disk is read-only)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
STORAGE_BUCKET = "product-images"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_product_image(file):
    """Uploads a file to Supabase Storage and returns its public URL."""
    filename = secure_filename(file.filename)
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
    supabase_admin.storage.from_(STORAGE_BUCKET).upload(
        path=filename,
        file=file.read(),
        file_options={"content-type": file.mimetype, "upsert": "true"},
    )
    return supabase_admin.storage.from_(STORAGE_BUCKET).get_public_url(filename)


# ---------------------------------------------------------------------------
# Decorators
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
    try:
        featured = (
            supabase.table("products").select("*")
            .eq("is_active", True).limit(4).execute()
        )
        featured_data = featured.data
    except Exception:
        featured_data = []
    return render_template("index.html", user=session.get("user_name"),
                           featured_products=featured_data)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        try:
            supabase_admin.table("enquiries").insert({
                "product_id": None,
                "user_id": session.get("user_id"),
                "name": request.form.get("name"),
                "email": request.form.get("email"),
                "phone": request.form.get("phone"),
                "message": request.form.get("message"),
                "quantity": 1,
                "type": "enquiry",
                "status": "new",
            }).execute()
            flash("Message sent! We'll get back to you soon.", "success")
            return redirect(url_for("contact"))
        except Exception as e:
            flash(f"Something went wrong: {str(e)}", "danger")
    return render_template("contact.html", user=session.get("user_name"))


@app.route("/about")
def about():
    return render_template("about.html", user=session.get("user_name"))


@app.route("/ecommerce")
def ecommerce():
    search = request.args.get("q", "").strip()
    query = supabase.table("products").select("*").eq("is_active", True)
    if search:
        query = query.ilike("name", f"%{search}%")
    products = query.execute()
    return render_template("ecommerce.html", products=products.data,
                           query=search, user=session.get("user_name"))


@app.route("/product/<product_id>")
def product_detail(product_id):
    product = supabase.table("products").select("*").eq("id", product_id).single().execute()
    return render_template("product_detail.html", product=product.data,
                           user=session.get("user_name"))


@app.route("/blog")
def blog():
    posts = (supabase.table("blog_posts").select("*").eq("is_published", True)
             .order("created_at", desc=True).execute())
    return render_template("blog.html", posts=posts.data, user=session.get("user_name"))


@app.route("/blog/<post_id>")
def blog_detail(post_id):
    post = supabase.table("blog_posts").select("*").eq("id", post_id).single().execute()
    return render_template("blog_detail.html", post=post.data, user=session.get("user_name"))


@app.route("/community")
@login_required
def community():
    posts = (supabase.table("community_posts").select("*, profiles(full_name)")
             .order("created_at", desc=True).execute())
    return render_template("community.html", posts=posts.data, user=session.get("user_name"))


@app.route("/community/new", methods=["POST"])
@login_required
def community_new():
    supabase.table("community_posts").insert({
        "title": request.form.get("title"),
        "content": request.form.get("content"),
        "user_id": session["user_id"],
    }).execute()
    flash("Post published!", "success")
    return redirect(url_for("community"))


# ---------------------------------------------------------------------------
# Auth
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
        auth_response = supabase.auth.sign_up({"email": email, "password": password})
        new_user = auth_response.user
        if new_user:
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
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = auth_response.user
        profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute()

        session["user_id"] = user.id
        session["user_name"] = profile.data.get("full_name")
        session["is_admin"] = profile.data.get("role") == "admin"

        flash("Logged in successfully!", "success")
        if session["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("index"))
    except Exception:
        flash("Invalid email or password.", "danger")
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Public enquiry / order submit
# ---------------------------------------------------------------------------

@app.route("/enquiry/<product_id>", methods=["POST"])
def send_enquiry(product_id):
    supabase_admin.table("enquiries").insert({
        "product_id": product_id,
        "user_id": session.get("user_id"),
        "name": request.form.get("name"),
        "email": request.form.get("email"),
        "phone": request.form.get("phone"),
        "message": request.form.get("message"),
        "quantity": request.form.get("quantity", 1),
        "type": request.form.get("type", "enquiry"),
        "status": "new",
    }).execute()
    flash("Your request has been sent! We'll contact you soon.", "success")
    return redirect(url_for("product_detail", product_id=product_id))


# ===========================================================================
# ADMIN  (each area has its own page)
# ===========================================================================

# ---- Overview -------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    products = supabase_admin.table("products").select("id").execute()
    enquiries = (supabase_admin.table("enquiries").select("*")
                 .order("created_at", desc=True).execute())
    blogs = supabase_admin.table("blog_posts").select("id").execute()
    posts = supabase_admin.table("community_posts").select("id").execute()
    stats = {
        "total_products": len(products.data),
        "new_enquiries": len([e for e in enquiries.data if e["status"] == "new"]),
        "total_enquiries": len(enquiries.data),
        "total_blogs": len(blogs.data),
        "total_posts": len(posts.data),
    }
    return render_template("admin_dashboard.html", stats=stats,
                           recent_enquiries=enquiries.data[:5],
                           user=session.get("user_name"))


# ---- Products -------------------------------------------------------------
@app.route("/admin/products")
@admin_required
def admin_products():
    products = (supabase_admin.table("products").select("*")
                .order("created_at", desc=True).execute())
    return render_template("admin_products.html", products=products.data,
                           user=session.get("user_name"))


@app.route("/admin/products/add", methods=["POST"])
@admin_required
def admin_add_product():
    image_url = request.form.get("image_url", "").strip()
    file = request.files.get("image_file")
    if file and file.filename and allowed_file(file.filename):
        try:
            image_url = upload_product_image(file)
        except Exception as e:
            flash(f"Image upload failed: {e}", "danger")
            return redirect(url_for("admin_products"))

    supabase_admin.table("products").insert({
        "name": request.form.get("name"),
        "description": request.form.get("description"),
        "price": request.form.get("price"),
        "category": request.form.get("category"),
        "image_url": image_url or None,
        "stock": request.form.get("stock", 0),
        "is_active": True,
    }).execute()
    flash("Product added.", "success")
    return redirect(url_for("admin_products"))


@app.route("/admin/products/<product_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_product(product_id):
    if request.method == "POST":
        # keep the current image unless a new file / URL is supplied
        image_url = request.form.get("image_url", "").strip() or request.form.get("current_image_url") or None
        file = request.files.get("image_file")
        if file and file.filename and allowed_file(file.filename):
            try:
                image_url = upload_product_image(file)
            except Exception as e:
                flash(f"Image upload failed: {e}", "danger")
                return redirect(url_for("admin_edit_product", product_id=product_id))

        supabase_admin.table("products").update({
            "name": request.form.get("name"),
            "description": request.form.get("description"),
            "price": request.form.get("price"),
            "category": request.form.get("category"),
            "image_url": image_url,
            "stock": request.form.get("stock", 0),
            "is_active": request.form.get("is_active") == "on",
        }).eq("id", product_id).execute()
        flash("Product updated.", "success")
        return redirect(url_for("admin_products"))

    try:
        product = supabase_admin.table("products").select("*").eq("id", product_id).single().execute()
    except Exception:
        flash("Product not found.", "danger")
        return redirect(url_for("admin_products"))
    return render_template("admin_product_edit.html", product=product.data,
                           user=session.get("user_name"))


@app.route("/admin/products/<product_id>/delete", methods=["POST"])
@admin_required
def admin_delete_product(product_id):
    supabase_admin.table("products").delete().eq("id", product_id).execute()
    flash("Product deleted.", "info")
    return redirect(url_for("admin_products"))


# ---- Blog posts -----------------------------------------------------------
@app.route("/admin/blogs")
@admin_required
def admin_blogs():
    posts = (supabase_admin.table("blog_posts").select("*")
             .order("created_at", desc=True).execute())
    return render_template("admin_blogs.html", posts=posts.data, user=session.get("user_name"))


@app.route("/admin/blogs/add", methods=["POST"])
@admin_required
def admin_add_blog():
    supabase_admin.table("blog_posts").insert({
        "title": request.form.get("title"),
        "content": request.form.get("content"),
        "cover_image": request.form.get("cover_image") or None,
        "author_id": session["user_id"],
        "is_published": request.form.get("is_published") == "on",
    }).execute()
    flash("Blog post saved.", "success")
    return redirect(url_for("admin_blogs"))


@app.route("/admin/blogs/<post_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_blog(post_id):
    if request.method == "POST":
        supabase_admin.table("blog_posts").update({
            "title": request.form.get("title"),
            "content": request.form.get("content"),
            "cover_image": request.form.get("cover_image") or None,
            "is_published": request.form.get("is_published") == "on",
        }).eq("id", post_id).execute()
        flash("Blog post updated.", "success")
        return redirect(url_for("admin_blogs"))

    try:
        post = supabase_admin.table("blog_posts").select("*").eq("id", post_id).single().execute()
    except Exception:
        flash("Blog post not found.", "danger")
        return redirect(url_for("admin_blogs"))
    return render_template("admin_blog_edit.html", post=post.data, user=session.get("user_name"))


@app.route("/admin/blogs/<post_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_blog(post_id):
    post = supabase_admin.table("blog_posts").select("is_published").eq("id", post_id).single().execute()
    supabase_admin.table("blog_posts").update(
        {"is_published": not post.data["is_published"]}
    ).eq("id", post_id).execute()
    flash("Post visibility changed.", "success")
    return redirect(url_for("admin_blogs"))


@app.route("/admin/blogs/<post_id>/delete", methods=["POST"])
@admin_required
def admin_delete_blog(post_id):
    supabase_admin.table("blog_posts").delete().eq("id", post_id).execute()
    flash("Blog post deleted.", "info")
    return redirect(url_for("admin_blogs"))


# ---- Community ------------------------------------------------------------
@app.route("/admin/community")
@admin_required
def admin_community():
    posts = (supabase_admin.table("community_posts").select("*, profiles(full_name)")
             .order("created_at", desc=True).execute())
    return render_template("admin_community.html", posts=posts.data, user=session.get("user_name"))


@app.route("/admin/community/<post_id>/edit", methods=["POST"])
@admin_required
def admin_edit_community_post(post_id):
    supabase_admin.table("community_posts").update({
        "title": request.form.get("title"),
        "content": request.form.get("content"),
    }).eq("id", post_id).execute()
    flash("Community post updated.", "success")
    return redirect(url_for("admin_community"))


@app.route("/admin/community/<post_id>/delete", methods=["POST"])
@admin_required
def admin_delete_community_post(post_id):
    supabase_admin.table("community_posts").delete().eq("id", post_id).execute()
    flash("Community post deleted.", "info")
    return redirect(url_for("admin_community"))


# ---- Enquiries ------------------------------------------------------------
@app.route("/admin/enquiries")
@admin_required
def admin_enquiries():
    status = request.args.get("status", "all")
    query = supabase_admin.table("enquiries").select("*").order("created_at", desc=True)
    if status in ("new", "contacted", "closed"):
        query = query.eq("status", status)
    enquiries = query.execute()
    return render_template("admin_enquiries.html", enquiries=enquiries.data,
                           status=status, user=session.get("user_name"))


@app.route("/admin/enquiries/<enquiry_id>/respond", methods=["POST"])
@admin_required
def admin_respond_enquiry(enquiry_id):
    """Updates only the fields that were submitted, so saving a note
    doesn't reset the status (and vice versa)."""
    updates = {"responded_at": datetime.utcnow().isoformat()}
    if "status" in request.form:
        updates["status"] = request.form["status"]
    if "admin_note" in request.form:
        updates["admin_note"] = request.form["admin_note"]
    supabase_admin.table("enquiries").update(updates).eq("id", enquiry_id).execute()
    flash("Enquiry updated.", "success")
    return redirect(request.referrer or url_for("admin_enquiries"))


@app.route("/admin/enquiries/<enquiry_id>/delete", methods=["POST"])
@admin_required
def admin_delete_enquiry(enquiry_id):
    supabase_admin.table("enquiries").delete().eq("id", enquiry_id).execute()
    flash("Enquiry deleted.", "info")
    return redirect(url_for("admin_enquiries"))


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@app.route("/api/products")
def api_products():
    products = supabase.table("products").select("*").eq("is_active", True).execute()
    return jsonify(products.data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)