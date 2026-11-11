"""Fixed seed catalogue: job specifications, projects and staff roles.

Everything here is fictitious. Company and client names are invented and do
not refer to real organisations (NFR5 / POPIA).

Each job uses the same fields as the Job Specification screen. Skills are
written the way a recruiter would type them; the SkillNormaliser cleans them
on load exactly as it does for typed input.
"""
from __future__ import annotations

E = ("Matric", "Higher Certificate", "Diploma", "Bachelor's Degree", "Honours", "Master's", "Doctorate")


def _job(title, location, min_exp, min_edu, required, preferred, description, status="open", weights=None):
    return {
        "job_title": title,
        "location": location,
        "status": status,
        "min_experience": min_exp,
        "min_education": min_edu,
        "required_skills": required,
        "preferred_skills": preferred,
        "job_description": description,
        "weights": weights or {"skills": 40, "experience": 25, "education": 15, "semantic": 20},
    }


JOBS: list[dict] = [
    # ---- data
    _job("Junior Data Engineer", "Johannesburg", 0, E[3], ["Python", "SQL", "ETL"], ["Airflow", "Docker", "AWS"],
         "Join our data platform team as a junior engineer. You will help build and test batch pipelines that load "
         "data from operational systems into the warehouse, write SQL transformations, fix data quality issues and "
         "learn to orchestrate scheduled jobs under the guidance of senior engineers."),
    _job("Senior Data Engineer", "Cape Town", 5, E[3], ["Python", "SQL", "Spark", "Data Modelling"],
         ["Databricks", "Kafka", "Terraform"],
         "Lead the design of our lakehouse. You will build reliable batch and streaming pipelines that process "
         "millions of events a day, model data for analytics, set engineering standards, review code and mentor "
         "a team of data engineers while keeping cloud costs under control."),
    _job("Analytics Engineer", "Remote", 2, E[3], ["SQL", "dbt", "Data Modelling"], ["Snowflake", "Python", "Power BI"],
         "Turn raw data into trusted, documented models that analysts can use without help. You will own the "
         "transformation layer in the warehouse, write tested dbt models, define metrics with the business and "
         "keep dashboards fast and consistent."),
    _job("Data Platform Lead", "Johannesburg", 8, E[4], ["Python", "AWS", "Spark", "Airflow"], ["Kafka", "Terraform", "Snowflake"],
         "Own the strategy and delivery of the group data platform. You will lead several squads, choose "
         "technologies, plan migrations from on-premise warehouses to the cloud, set data governance standards "
         "and report progress to executives.", status="closed"),
    # ---- software
    _job("Junior Software Developer", "Durban", 0, E[2], ["Java", "SQL", "Git"], ["Spring", "JavaScript", "REST APIs"],
         "Start your career building internal business applications. You will fix bugs, add small features to "
         "Java services, write unit tests and learn our code review and release process alongside experienced "
         "developers."),
    _job("Backend Developer (Python)", "Cape Town", 3, E[3], ["Python", "Django", "PostgreSQL", "REST APIs"],
         ["Docker", "Redis", "Celery"],
         "Build and maintain the APIs behind our customer platform. You will design endpoints, model data in "
         "PostgreSQL, write automated tests, improve performance and work with frontend developers to ship "
         "features every sprint."),
    _job("Backend Developer (.NET)", "Johannesburg", 3, E[3], ["C#", ".NET", "SQL Server", "REST APIs"], ["Azure", "Docker", "Microservices"],
         "Develop and support the .NET services that run our policy administration system. You will write clean, "
         "tested C# code, design database changes, integrate with partner systems and help move services to the "
         "cloud."),
    _job("Frontend Developer", "Cape Town", 2, E[2], ["JavaScript", "React", "HTML", "CSS"], ["TypeScript", "Accessibility", "Testing"],
         "Create fast, accessible web interfaces for our online store. You will build React components, work "
         "closely with designers, write tests, and improve page performance and accessibility across devices."),
    _job("Senior Full-Stack Developer", "Johannesburg", 6, E[3], ["TypeScript", "React", "Node.js", "SQL"],
         ["AWS", "GraphQL", "Docker"],
         "Lead features end to end, from database design to user interface. You will design APIs in Node.js, "
         "build React screens, mentor developers, and take part in architecture decisions and on-call support."),
    _job("Mobile Developer", "Pretoria", 3, E[3], ["Kotlin", "Android", "REST APIs"], ["Java", "Firebase", "Testing"],
         "Build and maintain our Android banking app used by thousands of customers. You will implement new "
         "features in Kotlin, integrate with backend APIs, improve app stability and publish regular releases."),
    _job("Software Engineering Manager", "Midrand", 8, E[3], ["Java", "Microservices", "Agile"], ["AWS", "Kubernetes", "Mentoring"],
         "Lead two product engineering teams. You will plan delivery, coach engineers, improve engineering "
         "practices, manage stakeholders and stay close enough to the code to guide technical decisions.",
         status="closed"),
    # ---- cloud / devops
    _job("Cloud Engineer", "Johannesburg", 3, E[3], ["AWS", "Terraform", "Linux", "Networking"], ["Kubernetes", "Python", "Monitoring"],
         "Design, build and operate our AWS environments. You will write infrastructure as code, manage networks "
         "and identity, automate account provisioning, respond to incidents and reduce cloud spend."),
    _job("Azure Cloud Administrator", "Durban", 2, E[2], ["Azure", "Networking", "PowerShell"], ["Terraform", "Active Directory", "Monitoring"],
         "Look after our Azure subscriptions. You will manage virtual machines, networks and access, apply "
         "security baselines, monitor costs and support teams moving workloads from the data centre."),
    _job("DevOps Engineer", "Cape Town", 3, E[3], ["Docker", "Kubernetes", "CI/CD", "Linux"], ["Terraform", "AWS", "Python"],
         "Help development teams ship safely and often. You will build and maintain CI/CD pipelines, run "
         "Kubernetes clusters, automate infrastructure, improve monitoring and lead post-incident reviews."),
    _job("Site Reliability Engineer", "Remote", 5, E[3], ["Kubernetes", "Monitoring", "Linux", "Python"], ["Go", "Terraform", "Incident Management"],
         "Keep our payment platform fast and available. You will define service level objectives, build "
         "observability, automate toil, plan capacity and lead incident response for critical services."),
    _job("Cloud Solutions Architect", "Johannesburg", 8, E[4], ["AWS", "Azure", "Networking", "Security"],
         ["Terraform", "Kubernetes", "Cost Optimisation"],
         "Design secure, resilient cloud solutions for client projects. You will run architecture workshops, "
         "produce designs and cost estimates, guide delivery teams and review implementations."),
    # ---- security
    _job("Security Analyst", "Pretoria", 2, E[3], ["SIEM", "Incident Response", "Networking"], ["Splunk", "Python", "Threat Intelligence"],
         "Monitor and respond to security events in our security operations centre. You will triage alerts, "
         "investigate incidents, tune detection rules and write clear incident reports."),
    _job("Penetration Tester", "Johannesburg", 3, E[3], ["Penetration Testing", "Linux", "Networking", "OWASP"],
         ["Python", "Burp Suite", "Active Directory"],
         "Test the security of web applications and internal networks for our clients. You will plan and run "
         "penetration tests, exploit weaknesses safely, write findings with clear fixes and present results."),
    _job("Information Security Manager", "Midrand", 7, E[4], ["Risk Management", "ISO 27001", "Security"],
         ["POPIA", "Incident Response", "Cloud Security"],
         "Run the information security programme. You will manage risk, maintain policies, lead audits, oversee "
         "the security operations team and report to the executive committee."),
    # ---- business intelligence / analysis
    _job("BI Developer", "Johannesburg", 3, E[3], ["SQL", "Power BI", "Data Modelling"], ["SSIS", "DAX", "Python"],
         "Build reports and dashboards that managers use every day. You will gather requirements, model data, "
         "write efficient SQL, design clear Power BI reports and support users."),
    _job("Data Analyst", "Cape Town", 1, E[3], ["SQL", "Excel", "Power BI"], ["Python", "Statistics", "Tableau"],
         "Answer business questions with data. You will query databases, clean and analyse data, build "
         "dashboards and present findings to marketing and operations teams."),
    _job("Data Scientist", "Johannesburg", 3, E[4], ["Python", "Machine Learning", "SQL", "Statistics"],
         ["Scikit-learn", "Spark", "MLOps"],
         "Build models that predict customer churn and credit risk. You will explore data, engineer features, "
         "train and validate models, explain results to stakeholders and help deploy models to production."),
    _job("Systems Analyst", "Pretoria", 3, E[3], ["Requirements Analysis", "UML", "SQL"], ["Agile", "Process Modelling", "Jira"],
         "Translate business needs into clear system specifications. You will run workshops, model processes, "
         "write user stories and acceptance criteria, and support testing and implementation."),
    # ---- quality assurance
    _job("QA Engineer", "Durban", 2, E[2], ["Manual Testing", "Test Cases", "SQL"], ["Selenium", "Jira", "API Testing"],
         "Make sure our releases work. You will write and run test cases, log defects clearly, test APIs, take "
         "part in sprint planning and help the team improve quality."),
    _job("Test Automation Engineer", "Cape Town", 3, E[3], ["Selenium", "Java", "API Testing", "CI/CD"],
         ["Playwright", "Cucumber", "Performance Testing"],
         "Build and maintain automated test suites for web and API layers. You will design test frameworks, "
         "run them in CI pipelines, report quality trends and coach developers on testing."),
    # ---- support / infrastructure
    _job("IT Support Technician", "Bloemfontein", 0, E[1], ["Windows", "Troubleshooting", "Networking"],
         ["Active Directory", "Microsoft 365", "Customer Service"],
         "Support staff with their computers, accounts and networks. You will log and resolve support tickets, "
         "set up laptops, manage user accounts and keep clear notes in the service desk system."),
    _job("Service Desk Team Lead", "Johannesburg", 4, E[2], ["ITIL", "Troubleshooting", "Customer Service"],
         ["Microsoft 365", "Reporting", "Mentoring"],
         "Lead a team of service desk agents. You will manage queues and service levels, coach agents, handle "
         "escalations and report on performance to IT management."),
    _job("Network Engineer", "Pretoria", 3, E[2], ["Networking", "Cisco", "Firewalls", "Linux"], ["SD-WAN", "Python", "Monitoring"],
         "Design and maintain the network that connects our branches. You will configure routers, switches and "
         "firewalls, troubleshoot outages, plan upgrades and document the network."),
    _job("Database Administrator", "Johannesburg", 4, E[3], ["SQL Server", "PostgreSQL", "Backup and Recovery"],
         ["Performance Tuning", "Azure", "PowerShell"],
         "Keep our databases healthy, fast and recoverable. You will manage backups and restores, tune queries, "
         "plan capacity, apply patches and support developers with database design."),
    _job("IT Project Manager", "Midrand", 5, E[3], ["Project Management", "Agile", "Stakeholder Management"],
         ["Scrum", "Budgeting", "Risk Management"],
         "Deliver IT projects on time and within budget. You will plan scope and schedules, manage risks and "
         "budgets, run project meetings and keep stakeholders informed.", status="closed"),
]

# Fictitious clients for the resource allocation module.
PROJECTS: list[dict] = [
    # offsets are in days relative to the day the seed runs
    {"name": "Core Banking Data Migration", "client": "Karoo Mutual Bank", "start": -150, "end": 120, "status": "active",
     "description": "Move ten years of account history from the legacy warehouse into the new lakehouse."},
    {"name": "Claims Portal Rebuild", "client": "Fynbos Insurance", "start": -90, "end": 150, "status": "active",
     "description": "Replace the paper-based claims process with an online portal and API."},
    {"name": "Fleet Tracking Platform", "client": "Baobab Logistics", "start": -60, "end": 200, "status": "active",
     "description": "Real-time vehicle tracking, route reports and driver scorecards."},
    {"name": "Patient Booking App", "client": "Highveld Health Group", "start": -30, "end": 180, "status": "active",
     "description": "Mobile and web booking for 40 clinics, integrated with the practice system."},
    {"name": "Cloud Landing Zone", "client": "Umoya Energy", "start": -45, "end": 75, "status": "active",
     "description": "Secure multi-account AWS foundation with networking, identity and guardrails."},
    {"name": "Security Operations Uplift", "client": "Jacaranda Metro Municipality", "start": -20, "end": 160, "status": "active",
     "description": "Stand up a 24x7 monitoring capability and incident response playbooks."},
    {"name": "Loyalty Analytics", "client": "Protea Retail", "start": -120, "end": 40, "status": "active",
     "description": "Customer segmentation and campaign dashboards for the loyalty programme."},
    {"name": "Network Refresh Phase 2", "client": "Kestrel Airways", "start": 20, "end": 140, "status": "planned",
     "description": "Replace branch routers and firewalls at 18 airport sites."},
    {"name": "Test Automation Rollout", "client": "Fynbos Insurance", "start": 30, "end": 210, "status": "planned",
     "description": "Automated regression suites for the policy and claims systems."},
    {"name": "Student Records Modernisation", "client": "Marula College", "start": 45, "end": 300, "status": "planned",
     "description": "Replace the student records system and integrate with the learning platform."},
    {"name": "Payroll System Upgrade", "client": "Karoo Mutual Bank", "start": -300, "end": -60, "status": "completed",
     "description": "Upgrade and parallel-run the payroll system."},
    {"name": "Warehouse Scanner Pilot", "client": "Baobab Logistics", "start": -40, "end": 60, "status": "on_hold",
     "description": "Handheld scanner pilot at two distribution centres, paused pending budget approval."},
]

# Existing (non-hired) staff on the bench or on projects: role titles by family.
STAFF_ROLES = {
    "data": ["Data Engineer", "Senior Data Engineer", "Analytics Engineer"],
    "software": ["Software Developer", "Senior Software Developer", "Frontend Developer", "Mobile Developer"],
    "cloud": ["Cloud Engineer", "DevOps Engineer", "Site Reliability Engineer"],
    "security": ["Security Analyst", "Penetration Tester"],
    "bi": ["BI Developer", "Data Analyst", "Business Analyst"],
    "qa": ["QA Engineer", "Test Automation Engineer"],
    "support": ["Network Engineer", "Database Administrator", "IT Project Manager"],
}
# Which staff families each project mainly needs.
PROJECT_NEEDS = {
    "Core Banking Data Migration": ["data", "bi", "qa"],
    "Claims Portal Rebuild": ["software", "qa", "cloud"],
    "Fleet Tracking Platform": ["software", "data", "cloud"],
    "Patient Booking App": ["software", "qa", "support"],
    "Cloud Landing Zone": ["cloud", "security"],
    "Security Operations Uplift": ["security", "support"],
    "Loyalty Analytics": ["bi", "data"],
    "Network Refresh Phase 2": ["support", "security"],
    "Test Automation Rollout": ["qa", "software"],
    "Student Records Modernisation": ["software", "data", "bi"],
    "Payroll System Upgrade": ["software", "qa"],
    "Warehouse Scanner Pilot": ["software", "support"],
}
