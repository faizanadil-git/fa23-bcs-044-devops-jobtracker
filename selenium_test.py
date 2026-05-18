"""
JobTrack — Selenium Test Suite
Student: FA23-BCS-044 (Faizan)
Course: CSC418 DevOps Final Lab
6 test cases covering login, register, dashboard, analytics, navigation, and error handling
Run: python selenium_tests.py  (make sure app is running at http://localhost)
"""

import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

BASE_URL = "http://localhost"
TEST_EMAIL = "faizan@gmail.com"
TEST_PASSWORD = "112233"


def get_driver():
    """Create and return a Chrome WebDriver instance."""
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Uncomment the line below to run headless (no browser window):
    # options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver


class JobTrackSeleniumTests(unittest.TestCase):

    def setUp(self):
        """Run before each test — create a fresh browser."""
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 10)

    def tearDown(self):
        """Run after each test — close the browser."""
        self.driver.quit()

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Login Page Loads Correctly
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_login_page_loads(self):
        """Verify the login page loads with correct title and elements."""
        print("\n[TEST 1] Checking login page loads...")
        self.driver.get(f"{BASE_URL}/login")

        # Check page title
        self.assertIn("JobTrack", self.driver.title)

        # Check logo is visible
        logo = self.driver.find_element(By.CLASS_NAME, "logo")
        self.assertIn("JobTrack", logo.text)

        # Check input fields exist
        identifier_field = self.driver.find_element(By.ID, "identifier")
        password_field = self.driver.find_element(By.ID, "password")
        self.assertTrue(identifier_field.is_displayed())
        self.assertTrue(password_field.is_displayed())

        # Check sign-in button exists
        sign_in_btn = self.driver.find_element(By.CLASS_NAME, "btn")
        self.assertTrue(sign_in_btn.is_displayed())

        # Check register link is present
        register_link = self.driver.find_element(By.LINK_TEXT, "Register")
        self.assertTrue(register_link.is_displayed())

        print("[TEST 1] PASSED — Login page loaded successfully.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Successful Login Redirects to Dashboard
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_successful_login(self):
        """Login with valid credentials and verify redirect to dashboard."""
        print("\n[TEST 2] Testing login with valid credentials...")
        self.driver.get(f"{BASE_URL}/login")

        # Fill in credentials
        self.driver.find_element(By.ID, "identifier").send_keys(TEST_EMAIL)
        self.driver.find_element(By.ID, "password").send_keys(TEST_PASSWORD)

        # Click Sign In
        self.driver.find_element(By.CLASS_NAME, "btn").click()

        # Wait for redirect to dashboard
        self.wait.until(EC.url_contains("/dashboard"))
        self.assertIn("/dashboard", self.driver.current_url)

        print("[TEST 2] PASSED — Login successful, redirected to dashboard.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Login Error Message for Wrong Credentials
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_login_error_on_wrong_credentials(self):
        """Verify error message shows when wrong credentials are entered."""
        print("\n[TEST 3] Testing login error with wrong credentials...")
        self.driver.get(f"{BASE_URL}/login")

        # Enter wrong credentials
        self.driver.find_element(By.ID, "identifier").send_keys("wrong@test.com")
        self.driver.find_element(By.ID, "password").send_keys("wrongpass")
        self.driver.find_element(By.CLASS_NAME, "btn").click()

        # Wait for the error div to appear
        self.wait.until(EC.visibility_of_element_located((By.ID, "error")))
        error_div = self.driver.find_element(By.ID, "error")

        self.assertTrue(error_div.is_displayed())
        self.assertNotEqual(error_div.text.strip(), "")  # Error message is not empty

        print(f"[TEST 3] PASSED — Error shown: '{error_div.text.strip()}'")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: Register Page Loads and Shows Correct Form Fields
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_register_page_loads(self):
        """Verify the register page loads with all required form fields."""
        print("\n[TEST 4] Checking register page and form fields...")
        self.driver.get(f"{BASE_URL}/register")

        # Verify title
        self.assertIn("JobTrack", self.driver.title)

        # Verify subtitle text
        subtitle = self.driver.find_element(By.CLASS_NAME, "subtitle")
        self.assertIn("Create", subtitle.text)

        # Verify all 3 form fields exist
        username_field = self.driver.find_element(By.ID, "username")
        email_field = self.driver.find_element(By.ID, "email")
        password_field = self.driver.find_element(By.ID, "password")

        self.assertTrue(username_field.is_displayed())
        self.assertTrue(email_field.is_displayed())
        self.assertTrue(password_field.is_displayed())

        # Verify "Sign in" link at bottom
        signin_link = self.driver.find_element(By.LINK_TEXT, "Sign in")
        self.assertTrue(signin_link.is_displayed())

        # Verify clicking "Sign in" navigates to login
        signin_link.click()
        self.wait.until(EC.url_contains("/login"))
        self.assertIn("/login", self.driver.current_url)

        print("[TEST 4] PASSED — Register page loaded with all fields and link works.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 5: Analytics Page Loads After Login
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_analytics_page_loads(self):
        """Login and then verify the analytics page loads with nav and war room."""
        print("\n[TEST 5] Testing analytics page after login...")

        # Login first
        self.driver.get(f"{BASE_URL}/login")
        self.driver.find_element(By.ID, "identifier").send_keys(TEST_EMAIL)
        self.driver.find_element(By.ID, "password").send_keys(TEST_PASSWORD)
        self.driver.find_element(By.CLASS_NAME, "btn").click()
        self.wait.until(EC.url_contains("/dashboard"))

        # Navigate to analytics
        self.driver.get(f"{BASE_URL}/analytics")

        # Verify we are on analytics page (not redirected to login)
        self.assertIn("/analytics", self.driver.current_url)

        # Verify title
        self.assertIn("JobTrack", self.driver.title)

        # Wait for page to load (the JS calls /api/stats)
        time.sleep(2)

        # Check the main content area loaded (not blank)
        main_content = self.driver.find_element(By.ID, "main-content")
        self.assertTrue(main_content.is_displayed())
        self.assertNotEqual(main_content.text.strip(), "")

        # Check analytics nav link is active
        nav_links = self.driver.find_elements(By.CSS_SELECTOR, ".nav a")
        active_links = [l for l in nav_links if "active" in (l.get_attribute("class") or "")]
        self.assertTrue(len(active_links) > 0)

        print("[TEST 5] PASSED — Analytics page loaded and content rendered.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 6: Navigation Between Dashboard and Analytics
    # ─────────────────────────────────────────────────────────────────────────
    def test_06_navigation_between_pages(self):
        """Login and verify navigation links between dashboard and analytics work."""
        print("\n[TEST 6] Testing navigation between Dashboard and Analytics...")

        # Login first
        self.driver.get(f"{BASE_URL}/login")
        self.driver.find_element(By.ID, "identifier").send_keys(TEST_EMAIL)
        self.driver.find_element(By.ID, "password").send_keys(TEST_PASSWORD)
        self.driver.find_element(By.CLASS_NAME, "btn").click()
        self.wait.until(EC.url_contains("/dashboard"))

        # Verify we are on dashboard
        self.assertIn("/dashboard", self.driver.current_url)

        # Click "Analytics" nav link
        analytics_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Analytics"))
        )
        analytics_link.click()
        self.wait.until(EC.url_contains("/analytics"))
        self.assertIn("/analytics", self.driver.current_url)

        # Now click "Dashboard" nav link to go back
        dashboard_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Dashboard"))
        )
        dashboard_link.click()
        self.wait.until(EC.url_contains("/dashboard"))
        self.assertIn("/dashboard", self.driver.current_url)

        # Verify dashboard has the logo
        logo = self.driver.find_element(By.CLASS_NAME, "logo")
        self.assertIn("JobTrack", logo.text)

        print("[TEST 6] PASSED — Navigation between Dashboard and Analytics works.")


if __name__ == "__main__":
    print("=" * 60)
    print("  JobTrack Selenium Test Suite — FA23-BCS-044")
    print("  Make sure your app is running: docker compose up -d")
    print("=" * 60)
    unittest.main(verbosity=2)