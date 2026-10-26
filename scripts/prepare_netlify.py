"""
Build helper script for Netlify.
Reads BACKEND_URL from environment and generates the Netlify _redirects file.
Defaults to the production Render web service URL.
"""
import os

def main():
    backend_url = os.getenv("BACKEND_URL", "https://library-management-system.onrender.com").strip().rstrip("/")

    redirects_content = f"""# Netlify Proxy Configuration
# Static assets served directly from Netlify Edge CDN
/static/*  /:splat  200

# Proxy all dynamic routes, forms, sessions, and APIs to Render Flask Backend
/*  {backend_url}/:splat  200!
"""

    os.makedirs("static", exist_ok=True)
    redirects_path = os.path.join("static", "_redirects")

    with open(redirects_path, "w", encoding="utf-8") as f:
        f.write(redirects_content)

    print(f"[+] Successfully generated {redirects_path}")
    print(f"[*] Proxy target configured: {backend_url}")

if __name__ == "__main__":
    main()
