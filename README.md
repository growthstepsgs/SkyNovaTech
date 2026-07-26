# Computer Service Co. — Web App (Functional Layout v1)

Flask + Supabase + vanilla HTML/CSS/JS, deployed on Vercel.

## 1. Local setup
```bash
cd cs-project
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill in real values
python app.py                  # http://localhost:5000
```

## 2. Supabase setup
1. Create a project at supabase.com.
2. Open SQL editor → run `supabase_schema.sql`.
3. Project Settings → API → copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_KEY` (keep secret, server-only)
4. Auth → Providers → make sure Email is enabled. For testing, you can turn
   off "Confirm email" under Auth settings so signup logs in immediately.
5. Sign up through the app once, then in SQL editor run:
   ```sql
   update profiles set role = 'admin' where email = 'you@example.com';
   ```
   That user becomes the admin and gets redirected to `/admin` after login.

## 3. Folder structure
```
cs-project/
├── app.py
├── requirements.txt
├── vercel.json
├── supabase_schema.sql
├── .env.example
├── templates/
│   ├── base.html          (nav + flash messages, all pages extend this)
│   ├── index.html         (home/about)
│   ├── login.html
│   ├── signup.html
│   ├── ecommerce.html     (product listing)
│   ├── product_detail.html (enquiry/order form)
│   ├── blog.html
│   ├── blog_detail.html
│   ├── community.html
│   └── admin_dashboard.html
└── static/
    ├── css/style.css
    └── js/main.js
```

## 4. Routes (functional layout)
| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Home/about |
| `/signup` | GET/POST | Public signup |
| `/login` | GET/POST | Login (redirects admin → `/admin`) |
| `/logout` | GET | Clear session |
| `/ecommerce` | GET | Public product list |
| `/product/<id>` | GET | Product detail + enquiry/order form |
| `/enquiry/<product_id>` | POST | Saves enquiry/order to Supabase |
| `/blog`, `/blog/<id>` | GET | Public blog |
| `/community` | GET (login) | View + post community messages |
| `/community/new` | POST (login) | Create community post |
| `/admin` | GET (admin) | Dashboard: stats, products, enquiries, blog |
| `/admin/product/add\|edit\|delete` | POST (admin) | Manage products |
| `/admin/enquiry/<id>/respond` | POST (admin) | Update enquiry status/notes |
| `/admin/blog/add` | POST (admin) | Publish blog post |
| `/api/products` | GET | JSON product feed (for later JS use) |

## 5. Deploy to Vercel
```bash
vercel login
vercel            # first deploy, follow prompts
```
Add the same `.env` values under Vercel Project → Settings → Environment Variables.

## 6. Next step (as requested)
Test this functional layout end-to-end (signup → login → admin promote →
add product → public enquiry → admin sees it → responds), then we move to
full UI/UX polish (real design system, responsive layout, cart-like flow,
image uploads via Supabase Storage, etc.)
