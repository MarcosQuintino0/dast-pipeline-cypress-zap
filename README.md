# DAST Automation - Cypress + OWASP ZAP

Automated **DAST** (Dynamic Application Security Testing) template that combines **Cypress** for HTTP traffic generation and **OWASP ZAP** for vulnerability scanning.

---

## About the Project

### Goal

This project demonstrates a complete approach to **automated security testing** for REST APIs. The pipeline works in 3 stages:

1. **Cypress** runs E2E tests that make real API requests, recording all HTTP traffic in **HAR** (HTTP Archive) files
2. **Python scripts** process the HARs: filter noise, deduplicate endpoints, and tokenize sensitive fields
3. **OWASP ZAP** imports the processed traffic, runs passive and active scans, and generates an HTML report with the vulnerabilities found

```
Cypress E2E Tests
       |
       v
  HAR Files (raw traffic)
       |
       v
  Python (filter, deduplicate, tokenize)
       |
       v
  filtered_traffic.har
       |
       v
  OWASP ZAP imports HAR
       |
       v
  Passive Scan (headers, cookies, info leaks)
       |
       v
  Active Scan (SQL Injection, XSS, etc.)
       |
       v
  HTML Vulnerability Report
```

### This is a Template, Not a Recipe

> **IMPORTANT:** This project serves as a **starting point** and reference. Don't follow the structure blindly - adapt it to your application's reality.

Every API has its own specifics: authentication, rate limiting, endpoint dependencies, business rules, etc. Use this template as a base and modify as needed.

**Examples of what you can (and should) adapt:**

- **Authentication**: add a login/token flow in Cypress's `before()` (OAuth, JWT, API Key, etc.)
- **Data cleanup**: include database reset/cleanup steps between runs to avoid data pollution
- **Endpoint rules**: configure which endpoints and HTTP methods are relevant for your context
- **Dynamic fixtures**: generate test payloads that respect your API's validation rules
- **Pre/post scan hooks**: run scripts before or after the scan (e.g., create test user, clear sessions)
- **CI/CD integration**: adapt the scripts to run in pipelines (GitHub Actions, GitLab CI, Jenkins, etc.)
- **Quality thresholds**: define acceptance criteria (e.g., fail the pipeline if High vulnerabilities are found)

### Why JSONPlaceholder?

This example uses **JSONPlaceholder** (https://jsonplaceholder.typicode.com) as the target API because it is:

- **Public and free** - no registration, authentication, or API key required
- **No rate limiting** - allows multiple requests without blocking
- **Standard REST** - supports GET, POST, PUT, DELETE
- **Stable** - available 24/7, ideal for demonstrations
- **Safe for testing** - write operations (POST, PUT, DELETE) are simulated and don't persist real data

In a real scenario, you would replace the base URL and endpoints with your own API.

---

## Prerequisites

| Tool | Version | Description |
|---|---|---|
| **Node.js** | 18+ | Runtime for Cypress |
| **Python** | 3.10+ | Core automation (HAR processing + ZAP integration) |
| **OWASP ZAP** | 2.14+ | DAST security scanner |
| **Google Chrome** | Any | Browser for Cypress tests (required for HAR capture) |

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd cypress-owasp
```

### 2. Install Node.js dependencies (Cypress)

```bash
npm install
```

### 3. Install Python dependencies

With virtual environment (recommended):

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

Or directly (without venv):

```bash
pip install -r requirements.txt
```

### 4. Configure OWASP ZAP

1. Download and install OWASP ZAP: https://www.zaproxy.org/download/
2. Open ZAP
3. Go to **Tools > Options > API**
4. Copy the **API Key** shown on screen
5. Create a `.env` file in the project root:

```env
ZAP_API_KEY=paste_your_api_key_here
```

> The `.env` is already in `.gitignore` to avoid exposing your key in the repository.

---

## Usage

The pipeline has 3 steps that must be executed in order:

### Step 1: Run Cypress tests (generate HAR traffic)

```bash
# Run ALL tests at once
npm run cypress:run:all

# Or run by controller individually
npm run cypress:run:posts
npm run cypress:run:comments
npm run cypress:run:todos
npm run cypress:run:users
npm run cypress:run:albums
```

After execution, HAR files will be generated in `security_tests/traffic/`.

> **Tip:** To open the Cypress GUI and debug tests: `npm run cypress:open`

### Step 2: Process the HAR files

```bash
python -m security_tests.cli.process_har
```

This command runs the preprocessing pipeline:

1. **Loads** all raw HARs from the `traffic/` folder
2. **Filters** error responses (4xx, 5xx) and out-of-scope endpoints
3. **Deduplicates** by `METHOD|URL` combination (no need to scan the same endpoint 10x)
4. **Tokenizes** numeric fields with `{{AUTO_INT}}` so ZAP generates unique values
5. **Saves** the result as `filtered_traffic.har`

### Step 3: Run the security scan

> **IMPORTANT:** OWASP ZAP must be running before executing this command.

```bash
python -m security_tests.cli.run_scan
```

The scan runs through 7 phases:

| Phase | Description |
|---|---|
| 1. Connection | Connects to ZAP and creates a clean session |
| 2. Context | Configures scope and technology allowlist |
| 3. Import HAR | Imports filtered traffic into ZAP |
| 4. Passive Scan | Analyzes headers, cookies, info leaks (no traffic sent) |
| 5. Configure Active | Sets attack policy (strength, threshold, threads) |
| 6. Active Scan | Sends malicious payloads endpoint by endpoint |
| 7. Report | Generates HTML with all vulnerabilities found |

The HTML report will be saved in `security_tests/reports/`.

---

## Project Structure

```
cypress-owasp/
|
|-- cypress/
|   |-- e2e/tests/                       # E2E tests organized by controller
|   |   |-- 1-posts-controller/          #   GET, POST, PUT, DELETE on /posts
|   |   |-- 2-comments-controller/       #   GET, POST on /comments
|   |   |-- 3-todos-controller/          #   GET, POST on /todos
|   |   |-- 4-users-controller/          #   GET on /users
|   |   |-- 5-albums-controller/         #   GET on /albums and /photos
|   |
|   |-- fixtures/                        # Static test data
|   |-- support/
|       |-- commands.js                  # Custom commands (apiFetch, etc.)
|       |-- e2e.js                       # Global setup (before/after with HAR)
|       |-- pages/
|           |-- urls.js                  # Centralized endpoint URLs
|           |-- payloads.js              # Centralized payloads for POST/PUT
|
|-- security_tests/
|   |-- config.py                        # Centralized configuration (Pydantic Settings)
|   |
|   |-- cli/                             # Command-line scripts
|   |   |-- process_har.py               #   Preprocessing pipeline
|   |   |-- run_scan.py                  #   ZAP scan pipeline
|   |
|   |-- har/                             # HAR processing modules
|   |   |-- preprocessing.py             #   Filter, deduplicate, tokenize
|   |   |-- zap_integration.py           #   Import HAR into ZAP, extract targets
|   |
|   |-- zap_scan/                        # ZAP scan modules
|   |   |-- zap_client.py                #   Connection and session
|   |   |-- context.py                   #   Scope and technologies
|   |   |-- scan_policy.py               #   Attack strength and thresholds
|   |   |-- scan_execution.py            #   Active scan per endpoint
|   |   |-- script_randomizer.py         #   HttpSender script for tokens
|   |   |-- report.py                    #   Generate HTML report
|   |
|   |-- zap_scripts/
|   |   |-- replace_tokens.js            # JS script executed by ZAP
|   |
|   |-- traffic/                         # HAR files (generated, gitignored)
|   |-- reports/                         # HTML reports (generated, gitignored)
|
|-- cypress.config.js                    # Cypress + HAR generator configuration
|-- cypress.env.json                     # Cypress environment variables
|-- package.json                         # Node.js dependencies
|-- requirements.txt                     # Python dependencies
|-- pyrightconfig.json                   # Python type checker configuration
|-- .env                                 # ZAP API key (gitignored)
|-- .gitignore
```

---

## How It Works (Technical Details)

### Why `fetch()` and not `cy.request()`?

Cypress has the `cy.request()` command for making HTTP requests, but it executes the request in Cypress's **Node.js** process, **outside the browser**. This means the HAR generator (which intercepts browser traffic) **does not capture these requests**.

That's why the custom `cy.apiFetch()` command uses the browser's native `fetch()`:

```
cy.request()  -->  Node.js  -->  API  (does NOT appear in the HAR)
cy.apiFetch() -->  Browser  -->  API  (DOES appear in the HAR)
```

### Why preprocess the HAR?

Cypress generates traffic for **everything**: the HTML page, CSS, JS, images, favicon, etc. If we send the raw HAR to ZAP, it will waste time scanning irrelevant static assets.

The preprocessing:
- **Removes** requests for assets (keeps only API endpoints)
- **Removes** error responses (4xx, 5xx generate false positives)
- **Deduplicates** endpoints (scanning `/posts` once is sufficient)
- **Tokenizes** numeric IDs so ZAP varies values on each request

### Why tokenize fields with `{{AUTO_INT}}`?

During the active scan, ZAP sends hundreds of requests varying payloads. If all use `"userId": 1`, conflicts can occur. The `{{AUTO_INT}}` token is replaced by a random number on each request by ZAP's `replace_tokens.js` script.

### Technology allowlist

ZAP has hundreds of scan rules for various technologies (PHP, ASP.NET, MongoDB, etc.). Filtering only the technologies relevant to your stack drastically reduces scan time and decreases false positives.

In this template, we filter for: `JavaScript, Node.js, Express, Nginx, Linux, Git`.

---

## Configuration

All configuration is centralized in `security_tests/config.py`. The main options:

### ZAP Connection

| Variable | Default | Description |
|---|---|---|
| `ZAP_HOST` | `127.0.0.1` | Host where ZAP is running |
| `ZAP_PORT` | `8080` | ZAP API port |
| `ZAP_API_KEY` | `""` | API Key (configure in `.env`) |
| `ZAP_MODE` | `standard` | ZAP mode: `safe`, `protect`, `standard`, `attack` |

### Scan Policy

| Variable | Default | Description |
|---|---|---|
| `ZAP_ATTACK_STRENGTH` | `MEDIUM` | Payload count: `LOW`, `MEDIUM`, `HIGH`, `INSANE` |
| `ZAP_ALERT_THRESHOLD` | `LOW` | Sensitivity: `LOW` (more alerts), `MEDIUM`, `HIGH` (fewer alerts) |
| `ZAP_THREAD_PER_HOST` | `2` | Simultaneous requests per host |
| `ZAP_DELAY_IN_MS` | `0` | Interval between requests (useful for rate limiting) |
| `ZAP_PSCAN_TIMEOUT_SECONDS` | `300` | Passive scan timeout |

### Business Rules

```python
# Which endpoints/methods ZAP should scan
ENDPOINT_RULES: dict[str, list[str]] = {
    "/posts": ["GET", "POST"],
    "/posts/": ["GET", "PUT", "DELETE"],
    "/comments": ["GET", "POST"],
    # ... add yours
}

# Fields whose values will be randomized by ZAP
FIELDS_TO_TOKENIZE: list[str] = [
    "userId",
    "id",
    "postId",
]
```

### Environment Variables

All settings can be overridden via environment variables or `.env`:

```env
ZAP_API_KEY=your_key_here
ZAP_PORT=8090
ZAP_ATTACK_STRENGTH=HIGH
ZAP_MODE=protect
```

---

## Adapting to Your API

### 1. Change the base URL

In `cypress.env.json`:

```json
{
  "apiUrl": "https://your-api.com",
  "appUrl": "https://your-api.com"
}
```

In `security_tests/config.py`:

```python
BASE_URL: str = "https://your-api.com"
```

### 2. Add authentication

If your API requires authentication, add it in `cypress/support/e2e.js`:

```javascript
before(() => {
  // Example: obtain JWT token before tests
  cy.request("POST", "https://your-api.com/auth/login", {
    username: "test_user",
    password: "test_password",
  }).then((response) => {
    Cypress.env("authToken", response.body.token);
  });

  // ... rest of HAR setup
});
```

And in `commands.js`, include the token in the header:

```javascript
headers: {
  "Content-Type": "application/json",
  "Authorization": `Bearer ${Cypress.env("authToken")}`,
},
```

### 3. Add database cleanup

For APIs that persist real data, it's important to clean state between runs:

```javascript
before(() => {
  // Clean test data before starting
  cy.request("POST", "https://your-api.com/admin/reset-test-data");

  // ... rest of setup
});

after(() => {
  // Clean data created during tests
  cy.request("DELETE", "https://your-api.com/admin/cleanup");

  // ... save HAR
});
```

You can also add periodic cleanup in the Python pipeline, for example by creating a `security_tests/cleanup.py` module that runs between scan phases.

### 4. Configure endpoints and rules

Edit `ENDPOINT_RULES` in `config.py` to map your API's endpoints:

```python
ENDPOINT_RULES: dict[str, list[str]] = {
    "/api/v1/products": ["GET", "POST"],
    "/api/v1/products/": ["GET", "PUT", "DELETE"],
    "/api/v1/orders": ["GET", "POST"],
    "/api/v1/users": ["GET"],
}
```

### 5. Adjust technologies

If your API uses PHP + MySQL instead of Node.js:

```python
ZAP_TECH_ALLOWLIST: str = "Language.PHP,Db.MySQL,WS.Apache,OS.Linux"
```

---

## Technologies Used

| Technology | Version | Purpose |
|---|---|---|
| **Cypress** | 13+ | E2E testing framework - generates real HTTP traffic |
| **cypress-har-generator** | 5.17+ | Plugin that captures browser traffic in HAR format |
| **Python** | 3.10+ | Core language for processing and integration |
| **Pydantic Settings** | 2.7+ | Typed configuration with validation and `.env` support |
| **Loguru** | 0.7+ | Structured and colorful logging |
| **zaproxy** | 0.5+ | Python client for the OWASP ZAP API |
| **OWASP ZAP** | 2.14+ | Open-source DAST scanner maintained by OWASP |

---

## License

This project is an educational template. Use, modify, and distribute freely.
