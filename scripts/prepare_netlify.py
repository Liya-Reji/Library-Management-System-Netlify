"""
Build helper script for Netlify.
Generates public/_redirects for Netlify Serverless Functions & SPA routing.
"""
import os

def main():
    redirects_content = """# Netlify Serverless & SPA Routing
# Route all API calls directly to the Netlify Serverless Function
/api/*  /.netlify/functions/api/:splat  200

# Single Page Application routing: serve index.html for all frontend views
/*  /index.html  200
"""

    os.makedirs("public", exist_ok=True)
    redirects_path = os.path.join("public", "_redirects")

    with open(redirects_path, "w", encoding="utf-8") as f:
        f.write(redirects_content)

    print(f"[+] Successfully generated {redirects_path}")

if __name__ == "__main__":
    main()
