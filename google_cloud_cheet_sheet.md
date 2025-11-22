# Google Cloud Cheat Sheet

> **Note on AI Use**  
> This document was created with the help of AI to save time and speed up the writing process. It's not a direct copy-paste—I built it gradually from my own notes and questions, and reviewed and edited the content to fit my needs.


##  Project

Resources in GCP are grouped into **projects**. Every GCP resource belongs to a project. Each project has a **globally unique ID** and a **name** that you can choose to suit your use case.

A project has:
- **Quotas**: limits on the resources it can use
- A **billing account**: to track and charge usage

It's common to create separate projects for development and production environments. This separation makes it easier to manage permissions, resources, and especially **track costs** independently.

**Example project naming:**
1. `ai-pricing-dev`
2. `ai-pricing-prod`

## IAM, IAM Groups, IAM policy and service accounts

IAM is similar to **user and permission systems in an operating system**. It controls **who can access what** and **what actions they can perform** on GCP resources.

Examples of IAM:
  - **Google accounts**: your personal account (`you` = root user)
  - **IAM users**: like OS users (e.g., `bob`)
  - **IAM groups**: collections of users, similar to Linux groups (e.g., `sudo`, `docker`)
  - **Service accounts**: robot users, like `systemd`, `docker`, or cronjob users

**IAM roles** define **what actions** an identity can perform. Think of them like extended file permissions (`read`, `write`, `execute`) but more granular and cloud-specific.
- `roles/storage.objectViewer` = Read from bucket
- `roles/compute.admin` = Full control over VMs

An **IAM policy** binds a principal (user, group, or service account) to one or more roles **on a resource**. They are similar to `/etc/group` or `/etc/sudoers` in Linux, where you map users to groups and assign privileges.

```sh
  export PROJECT_ID="mlops-project-id"
  export SA="service-account"          # service account to create/manage
  
  # NOTE: create IAM service account
  gcloud iam service-accounts create "$SA" \
    --project="$PROJECT_ID" \
    --description="Service account for bike share project" \
    --display-name="bike-share-service-account"

  # list all IAM bindings on the project
  gcloud projects get-iam-policy "$PROJECT_ID"

  # list only service accounts
  gcloud iam service-accounts list --project="$PROJECT_ID"

  # delete a service account (example)
  gcloud iam service-accounts delete \
    "${SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project="$PROJECT_ID"

  # NOTE: grant access (example: Storage Admin)
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

  # NOTE: generate and download a key file
  gcloud iam service-accounts keys create ~/key.json \
    --iam-account="${SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project="$PROJECT_ID"
```

## Billing Accounts

- Billing is set at the **billing account** level, like a **utility bill** for your data center.
- Projects are linked to a billing account

```sh
# NOTE: list billing accounts
gcloud beta billing accounts list

# NOTE: get billing info for project-id
gcloud beta billing projects describe "$PROJECT_ID"
```

## Quotas

Quotas are limited. For instance you can use an large vm you might need to request an increasing in your quota for that and can take up to 2 business day.

- GCP sets quotas to prevent abuse or overconsumption.
- Can be per project, per region, per user, or per API.

 ## Resource Hierarchy

* Organization
  * Folder(s) (Usually department, environment, geography. Useful for large and scale companies)
    * Project(s)
      * Resources (VMs, Buckets, Datasets, etc.)

Example:

```yaml
Organization
└─ Folder: Prod
   ├─ Project: app-prod
   └─ Project: data-prod
└─ Folder: Non-Prod
   ├─ Project: app-dev
   └─ Project: app-staging

# NOTE: by departments
Organization
└─ Folder: Financing
   ├─ Project: payments
   └─ Project: revenue
└─ Folder: Data Science
   ├─ Project: pricing
   └─ Project: customer segmentation
```

## Regions and Zones

- **Region**: Geographical area (e.g., `us-central1`)
- **Zone**: Isolated location within a region (e.g., `us-central1-a`)
- Use **multi-zone** or **regional** setups for HA (high availability)

Some services are global, but others are **region-specific**, such as AI Platform training jobs, Cloud Run, and GKE clusters.

Most of the time, accessing resources across different regions can **increase latency** and **cost more**. For networking between regions or zones, you must go over the internet or use **VPC Peering** / **Cloud Interconnect**.

> PS: Cloud Storage (GCS) is global by design. Buckets can be accessed from any zone or region, regardless of where they're located.

Zones can be used for **operational risk management**:
- Placing all resources in one zone is like putting all your eggs in one basket.

| VM Location                      | Private IP Communication  | Notes                              |
|----------------------------------|---------------------------|------------------------------------|
| Same zone                        | Yes                       | Lowest latency                     |
| Different zones (same region)    | Yes                       | Slightly higher latency            |
| Different regions (same VPC)     | Yes                       | Higher latency; still private IP   |

## Networking, VPC, DNS and Loading Balancers

A **VPC** is your project's private network inside Google Cloud. It's similar to a physical network you'd set up in a data center, with its 
own IP ranges, subnets, firewalls, and routing rules.

VPCs are **global**, but their **subnets are regional**.

| VPC Component      | Analogy                                 |
|--------------------|-----------------------------------------|
| VPC Network        | Your office building’s entire LAN       |
| Subnets            | Individual floors or departments        |
| Firewall Rules     | Locked doors controlling access         |
| Routes             | Hallways or network switches            |
| Peering            | A direct cable to another office LAN    |

- A **VPC spans all regions** globally.
- **Subnets**, however, are created per **region**.
- **VMs are zonal**, and when you create a VM, you assign it to a **subnet (regional)** and a **zone** within that region.
- **Private IP communication** between VMs is only possible if they are in the same VPC and firewall rules allow it, even across regions.

For global available and low lattency. Google provide a **global load balancer** you can use to redirect request to the most closes resources based on the requester IP. This is how google searches works.

If you’re building an app with users in multiple countries:
- Use **global load balancers**
- Deploy your app in **multiple regions**
- Replicate data carefully if needed (e.g., via Cloud Spanner or multi-region GCS)
- Use **Anycast IPs** and **CDN** when possible for static content

**Cloud DNS** (**AWS Route 53**) is Google Cloud's scalable, high-availability **Domain Name System (DNS)** service.

**Cloud CDN** caches **static content** (images, JavaScript, videos, etc.) at Google’s **edge locations** around the world to improve load times and reduce origin server load.

### 11. Other Important Concepts

| Concept             | Analogy                                                  |
|---------------------|----------------------------------------------------------|
| VPC                 | Ethernet switch + router + firewall                      |
| Cloud Functions     | Bash scripts or cron jobs in the cloud                   |
| Cloud Run           | systemd-run containers on demand                         |
| BigQuery            | Supercharged SQL with columnar storage                   |
| Cloud Logging       | /var/log and journalctl for all your cloud services      |
| Cloud Build         | CI/CD system like Jenkins or GitHub Actions              |

## Authentications:  Application Default Credentials (ADC)

   Rules:
   1. Check GOOGLE_APPLICATION_CREDENTIALS (env var)

```sh
        # NOTE: needs to get the file auth output msgs
        # Ex1:
        export GOOGLE_APPLICATION_CREDENTIALS="/Users/user.name/mlops/sa_prod_key.json"

        # Ex2:
        export GOOGLE_APPLICATION_CREDENTIALS="/Users/user.name/.config/gcloud/application_default_credentials.json"
```

   1. If not set, check gcloud’s ADC file (~/.config/gcloud application_default_credentials.json)

```sh
      # NOTE: how to create the ADC json file

      # application default. follow the link and aithenticate.
      # This save a json file on your disk: (pay attention in the msgs)
      # Ex: /Users/user.nae/.config/gcloud/application_default_credentials.json
      gcloud auth application-default login

      # user account.
      gcloud auth login
```

  1. If still not found ->  use anonymous  credentials (susally fails)


## gcloud

The gcloud CLI is your remote control for Google Cloud — like a universal remote for managing everything from virtual machines to storage buckets. Just like a TV remote lets you switch channels, gcloud lets you spin up servers, trigger jobs, move files, and manage services from your terminal.

* core commands

```sh
gcloud auth login                        # Authenticate to GCP
gcloud config list                       # Show current config (project, region, zone)
gcloud config set project [PROJECT_ID]  # Set active project
gcloud config set compute/region [REGION]
gcloud config set compute/zone [ZONE]

gcloud projects get-iam-policy [PROJECT_ID]                     # View roles & members
gcloud projects add-iam-policy-binding [PROJECT_ID] \
  --member="user:someone@example.com" --role="roles/viewer"     # Grant access
```

* cloud storage 

```sh
gcloud storage ls                                # List buckets
gcloud storage cp file.txt gs://my-bucket/       # Upload file
gcloud storage cp gs://my-bucket/file.txt .      # Download file
gcloud storage rm gs://my-bucket/file.txt        # Delete file

# NOTE: gsutil is old but more robust
gsutil -m cp -r bigdir/ gs://my-bucket/          # Parallel uploads for speed
```

* base of main services

```sh
# NOTE: cloud run (run small jobs)
gcloud run deploy [SERVICE_NAME] \
  --image gcr.io/[PROJECT]/[IMAGE] --region [REGION] --platform managed

gcloud run services list
gcloud run jobs run [JOB_NAME] --region [REGION]

# NOTE: scheduler
gcloud scheduler jobs list
gcloud scheduler jobs run [JOB_NAME]

# NOTE: VMs
gcloud compute instances list
gcloud compute ssh [INSTANCE_NAME]               # SSH into VM
gcloud compute scp file.txt [INSTANCE_NAME]:~/   # Copy file to VM
```

* model artifacts registry

```sh
gcloud artifacts repositories list
gcloud auth configure-docker
gcloud artifacts docker tags list [REGION]-docker.pkg.dev/[PROJECT]/[REPO]/[IMAGE]
```