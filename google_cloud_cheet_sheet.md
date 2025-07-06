# Google Cloud Cheat Sheet

> **Note on AI Use**  
> This document was created with the help of AI (ChatGPT by OpenAI) to save time and speed up the writing process. It's not a direct copy-paste—I built it gradually from my own notes and questions, and reviewed and edited the content to fit my needs.


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

## Billing Accounts

- Billing is set at the **billing account** level, like a **utility bill** for your data center.
- Projects are linked to a billing account

## Quotas

Quotas are limited. For instance you can use an large vm you might need to request an increasing in your quota for that and can take up to 2 business day.

- GCP sets quotas to prevent abuse or overconsumption.
- Can be per project, per region, per user, or per API.

 ## Resource Hierarchy

 Organization
└── Folder(s)
    └── Project(s)
        └── Resources (VMs, Buckets, Datasets, etc.)

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
