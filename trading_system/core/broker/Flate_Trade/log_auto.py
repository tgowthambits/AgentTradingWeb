from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, parse_qs


def get_otp():
    import pyotp

    # Replace 'YOUR_BASE32_SECRET' with your actual base32 secret key
    secret = 'JOQ7SBK3UNWDNVHICRTO7562J53RYS4Y'

    # Create a TOTP object
    totp = pyotp.TOTP(secret)

    # Generate the current TOTP code
    current_code = totp.now()

    print("Your current TOTP code is:", current_code)

    return current_code

class FlattradeLogin:
    def __init__(self, url, username, password, otp):
        self.url = url
        self.username = username
        self.password = password
        self.otp = otp
    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,   # MUST be False for OTP
                slow_mo=300       # Makes typing visible
            )

            page = browser.new_page()
            page.goto(self.url)

            # ⏳ Wait for login page to load
            page.wait_for_load_state("networkidle")

            # ✅ Fill Username
            page.fill('input[id="input-19"]', self.username)

            # ✅ Fill Password
            page.fill('input[id="pwd"]', self.password)
            
            page.fill('input[id="pan"]', self.otp)

            print("✅ Username & Password filled.")

            # Capture redirect URL
            redirect_url = None
            
            def handle_request(request):
                nonlocal redirect_url
                if '127.0.0.1' in request.url or 'localhost' in request.url:
                    redirect_url = request.url
            
            page.on("request", handle_request)
            page.click('button[id="sbmt"]')
            
            # Wait for redirect
            for _ in range(40):
                page.wait_for_timeout(25)
                if redirect_url:
                    break
                if '127.0.0.1' in page.url or 'localhost' in page.url:
                    redirect_url = page.url
                    break
            
            browser.close()
            
            # Extract code parameter from URL
            if redirect_url:
                parsed = urlparse(redirect_url)
                params = parse_qs(parsed.query)
                code = params.get('code', [None])[0]
                return code
            
            return None


if __name__ == "__main__":
    URL = "https://auth.flattrade.in/?app_key=8ee6ee6a7e8e49e38266639d15bbbad3"

    USERNAME = "FT042478"
    PASSWORD = "26@Jesus"
    OTP = get_otp()
    
    code = FlattradeLogin(URL, USERNAME, PASSWORD, OTP).run()
    #  copy the code to clipboard
    # import pyperclip
    # pyperclip.copy(code)
    if code:
        print(f"✅ Authorization Code: {code}")
    else:
        print("⚠️  Could not extract authorization code")
