# FortiGate-VM on AWS — Step-by-Step Deploy Guide

Deploy a **FortiGate-VM (BYOL)** firewall into **your own AWS account** in about 15 minutes — **even if you have never used Terraform before**. Just follow the steps **in order**. Every command is copy-paste.

**What you end up with:** one FortiGate-VM firewall with a public IP address you can log into from your browser, running FortiOS 7.6.7 GA. When you're done testing, one command deletes it all.

> ℹ️ You need: an **AWS account** you can log into, and the **AWS Access Key** for it (ask your AWS admin if you don't have one). That's it.

---

## PART A — One-time setup (do these once per computer)

### Step 1 — Install Terraform
Terraform is the free tool that builds everything for you.

- **Windows:** Easiest way — open **PowerShell** and run:
  ```powershell
  choco install terraform
  ```
  (No Chocolatey? Download the ZIP from https://developer.hashicorp.com/terraform/install, unzip it, and put `terraform.exe` in a folder that's on your PATH — e.g. `C:\Windows\System32`.)
- **Mac:** `brew install terraform`
- **Linux:** follow https://developer.hashicorp.com/terraform/install

**Check it worked** (should print a version number, 1.3 or higher):
```
terraform -version
```

### Step 2 — Install the AWS CLI
This lets Terraform talk to your AWS account.

- **Windows:** download and run the installer at https://awscli.amazonaws.com/AWSCLIV2.msi
- **Mac:** `brew install awscli`
- **Linux:** follow https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

**Check it worked:**
```
aws --version
```

### Step 3 — Connect the AWS CLI to your account
Run this and answer the 4 prompts:
```
aws configure
```
| It asks for… | What to enter |
|---|---|
| AWS Access Key ID | paste your key (from your AWS admin / IAM user) |
| AWS Secret Access Key | paste your secret |
| Default region name | `us-east-1` |
| Default output format | `json` |

**Check it worked** (should print your AWS account number — no errors):
```
aws sts get-caller-identity
```

### Step 4 — Subscribe to the FortiGate image (FREE — this is required!)
AWS will **block the deployment** unless you've clicked "subscribe" to the FortiGate BYOL image **once**.

1. Sign in to the AWS Console (https://console.aws.amazon.com) with the **same account** from Step 3.
2. Go to AWS Marketplace, search **"FortiGate"**, and open the **"Fortinet FortiGate Next-Generation Firewall (BYOL)"** listing (BYOL = Bring Your Own License).
3. Click **Continue to Subscribe** → **Accept Terms**.
4. Wait about a minute until it says the subscription is complete.

> ⛔ If you skip this, Step 8 fails with an error that says **`OptInRequired`**. That just means "go do Step 4."

---

## PART B — Deploy the firewall

### Step 5 — Download these files
- If you have `git`:
  ```
  git clone https://github.com/howardsinc3753/MSSP-Tools.git
  cd MSSP-Tools/FortiGate-AWS-Terraform
  ```
- **No git?** Go to https://github.com/howardsinc3753/MSSP-Tools → green **Code** button → **Download ZIP** → unzip it → open a terminal **inside** the `FortiGate-AWS-Terraform` folder.

### Step 6 — Enter your 2 settings
First, make your own copy of the settings file:
- **Windows:** `copy terraform.tfvars.example terraform.tfvars`
- **Mac/Linux:** `cp terraform.tfvars.example terraform.tfvars`

Now open **`terraform.tfvars`** in Notepad (or any text editor) and set just these two lines:

```hcl
admin_password = "PickAStrongPassword1!"   # the firewall's login password (8+ characters)
admin_cidr     = "1.2.3.4/32"              # YOUR public IP so only you can reach it
```

**How to get your public IP for `admin_cidr`:** open https://ifconfig.me in your browser, copy the number it shows (e.g. `98.76.54.32`), and write it with `/32` on the end, in quotes → `"98.76.54.32/32"`.

Save the file.

### Step 7 — Get ready (run once)
```
terraform init
```
This downloads what Terraform needs. You'll see "Terraform has been successfully initialized!"

### Step 8 — Build it
```
terraform apply
```
It shows a plan and asks **`Enter a value:`** — type **`yes`** and press Enter. Wait about **3 minutes**. When it finishes you'll see something like:

```
Outputs:

admin_url = "https://54.123.45.67/"
public_ip = "54.123.45.67"
```

📋 **Copy that `admin_url`** — that's your firewall.

### Step 9 — Log into your firewall
1. Open the **`admin_url`** (e.g. `https://54.123.45.67/`) in your browser.
2. You'll get a **certificate warning** — that's normal (the firewall uses a self-signed cert). Click **Advanced → Proceed / Continue**.
3. Log in:
   - **Username:** `admin`
   - **Password:** the one you set in Step 6.

### Step 10 — Activate the license (BYOL)
The firewall boots unlicensed. To license it:
- In the GUI: go to **System → FortiGuard** and register, **or**
- Upload your license file when prompted at first login, **or**
- CLI: `execute vm-license <your-FortiFlex-token>`

(You provide the license — "BYOL" means Bring Your Own License. Get a free eval or a FortiFlex token from Fortinet.)

🎉 **Done — you have a working FortiGate on AWS.**

---

## PART C — When you're finished: DELETE everything
This removes the firewall and **stops all AWS charges**. From the same folder:
```
terraform destroy
```
Type **`yes`** when asked. That's it — everything is gone.

---

## Troubleshooting (common issues)

| What you see | What it means / the fix |
|---|---|
| `Error: ... OptInRequired` | You skipped **Step 4**. Subscribe to the FortiGate BYOL Marketplace product, then run `terraform apply` again. |
| Browser just **spins / times out** on the admin URL | Your IP probably changed. Re-check https://ifconfig.me, update `admin_cidr` in `terraform.tfvars`, then run `terraform apply` again. |
| `Unable to locate credentials` | The AWS CLI isn't connected. Re-do **Step 3** (`aws configure`). |
| `no AMI found` / `InvalidAMIID` | That FortiOS version isn't offered in your region. Leave the defaults, or set a different `aws_region` in `terraform.tfvars`. |
| GUI won't load but SSH works | Give it another 2–3 minutes to finish booting, then refresh. |
| Forgot the admin password | Run `terraform destroy` then `terraform apply` to start fresh, or reset via the AWS EC2 serial console. |

**Need help?** Open an issue at https://github.com/howardsinc3753/MSSP-Tools/issues (never paste passwords or keys).

---

## What this actually builds (for the curious)
- 1 VPC with a public (WAN) and private (LAN) subnet + internet gateway
- 1 FortiGate-VM (BYOL), two NICs (`port1` WAN + `port2` LAN), with a public Elastic IP
- A firewall (security group) that only allows **your IP** to the admin GUI/SSH
- The FortiOS AMI is **looked up automatically** for your region — no AMI IDs to hunt down

## Changing options (optional)
Everything is in `terraform.tfvars`. Common ones:

| Setting | Default | Notes |
|---|---|---|
| `fortios_version` | `7.6.7` | any FortiOS GA version |
| `architecture` | `arm64` | `arm64` (cheaper) or `x86_64` |
| `instance_type` | `t4g.medium` | keep 4 GB+ RAM |
| `aws_region` | `us-east-1` | any region you like |

---

## License & Disclaimer
Licensed under the [MIT License](LICENSE). **Not an official Fortinet product** — it is not endorsed or supported by Fortinet, Inc. It deploys **billable** AWS resources; you are responsible for all costs, security, licensing, and outcomes. **Test in a lab first.** Provided AS-IS with no warranty. See [LICENSE](LICENSE) for full terms.
