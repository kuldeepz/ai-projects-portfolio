# Architecture Review Agent

AI-powered architecture reviewer aligned with the AWS/Azure Well-Architected Framework. Describe your system and get a scored review covering scalability, security, reliability, performance, maintainability, and cost.

## What It Does

- **Overall score (0–100)** — holistic Well-Architected assessment
- **Risk identification** — per pillar: scalability/security/reliability/performance/maintainability/cost
- **Single Points of Failure** — explicit SPoF list with mitigation suggestions
- **WAF gaps** — misalignments with Well-Architected best practices
- **Prioritized recommendations** — ordered by impact

## Quick Start

```bash
cd architecture-review-agent
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python reviewer.py
```

## Sample Output

```
Architecture Review
===================
Type: monolith
Overall Score: 31/100

Single Points of Failure:
  🔴 Single EC2 instance — no Auto Scaling Group or standby
  🔴 RDS with no read replicas or Multi-AZ
  🔴 No CDN — all static assets served from app server

Well-Architected Gaps:
  [Reliability]    No health checks or automated failover
  [Security]       No WAF, security groups too permissive
  [Performance]    No caching layer for 50,000 req/day at 100x target

Top Recommendations:
  1. Add ALB + ASG for horizontal scaling [HIGH]
  2. Enable RDS Multi-AZ and daily snapshots [CRITICAL]
  3. Add ElastiCache for session/query caching [HIGH]
```

## Run Tests (No API Key Required)

```bash
python test_reviewer.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Sample: monolith on single EC2 targeting 100x scale — stress-tests the reviewer
