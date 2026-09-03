# Review Environments

> Mirrored from Confluence: [Review Environments](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4811751462/Review+Environments)
> Space `BAE` · page `4811751462` · last modified in Confluence Aug 24, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

**Status: unproven. This is a guide, not a commitment to an approach.**

Nothing on this page has been implemented or run for real. The workflows, naming scheme, infrastructure split, and cost estimates below are a proposed design to build from and validate — they do not describe anything that exists today, and they are not an agreed standard to comply with. Expect the details to change once we have stood one of these up. Until then, treat this as a starting point for building review environments.

## 1.1 Review Environments

Review environments allow QA, product owners, and other stakeholders to validate features on a real running instance before a PR is merged. They are ephemeral — created on demand and destroyed automatically.

### 1.1.1 Lifecycle Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Review Environment Lifecycle                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Developer adds `review-deploy` label to PR                     │
│     │                                                               │
│  2. `review-deploy.yml` workflow triggers                          │
│     ├── Generate unique env name: review-pr-{number}               │
│     ├── Restore staging DB snapshot → review-pr-{number} database  │
│     ├── Build Docker image tagged with PR head SHA                 │
│     ├── Create ECS task definition for review-pr-{number}          │
│     ├── Create ECS service (web + worker if applicable)            │
│     ├── Register target in shared review ALB                       │
│     ├── Create Route53 record: pr-{number}.review.{domain}        │
│     └── Post PR comment with environment URL                       │
│                                                                     │
│  3. Developer pushes new commits to PR                             │
│     ├── Rebuild Docker image with new SHA                          │
│     ├── Update ECS task definition with new image                  │
│     ├── Deploy to existing review environment                      │
│     └── Post PR comment: "Review environment updated"              │
│                                                                     │
│  4. Environment is torn down (any of these triggers):              │
│     ├── PR is merged → auto-teardown                               │
│     ├── PR is closed → auto-teardown                               │
│     ├── Label `review-deploy` is removed → auto-teardown           │
│     └── Stale (48h no PR activity) → nightly cleanup tears down    │
│                                                                     │
│  5. On teardown:                                                   │
│     ├── Deregister targets from ALB                                │
│     ├── Stop ECS services and delete task definitions              │
│     ├── Delete review database                                     │
│     ├── Delete Route53 record                                      │
│     └── Post PR comment: "Review environment destroyed"            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1.2 Naming Convention

All review environment resources use a consistent naming scheme derived from the PR number:

| Resource | Name Pattern | Example (PR #142) |
| --- | --- | --- |
| ECS Service (web) | `{App}-Review-PR{number}-Web` | `PaymentManager-Review-PR142-Web` |
| ECS Service (worker) | `{App}-Review-PR{number}-Worker` | `PaymentManager-Review-PR142-Worker` |
| ECS Task Definition | `{App}-Review-PR{number}-Web` | `PaymentManager-Review-PR142-Web` |
| CloudWatch Log Group | `/aws/ecs/{App}-Review-PR{number}` | `/aws/ecs/PaymentManager-Review-PR142` |
| Database | `{app}_review_pr{number}` | `paymentmanager_review_pr142` |
| DNS Record | `pr-{number}.review.{domain}` | `pr-142.review.bnkflow.com` |
| Docker Image Tag | `review-pr{number}-{short_sha}` | `review-pr142-a1b2c3d` |

### 1.1.3 Infrastructure Architecture

Review environments share certain infrastructure with staging to reduce cost and complexity, but isolate compute and data.

**Shared with staging** (managed by the project's main Terraform):

* VPC, subnets, gateways, route tables
* ECS cluster (review services run on the same cluster as staging)
* ECR repository (review images are pushed to the same repo with different tags)
* Application Load Balancer (shared ALB with host-based routing rules)
* Route53 hosted zone
* ACM wildcard certificate (`*.review.{domain}`)

**Isolated per review environment** (managed by the review workflow):

* ECS task definitions and services
* Database (restored from staging snapshot)
* CloudWatch log group
* ALB listener rule (routes `pr-{number}.review.{domain}` to the review target group)
* ALB target group

This means the main project Terraform needs to provision these additional resources to support review environments:

**Additions to** `acm.tf` — wildcard certificate for review subdomains:

```hcl
resource "aws_acm_certificate" "review" {
  domain_name       = "*.review.${var.root_domain}"
  validation_method = "DNS"
  tags              = local.tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "review" {
  certificate_arn         = aws_acm_certificate.review.arn
  validation_record_fqdns = [for record in aws_route53_record.review_acm : record.fqdn]

  timeouts {
    create = "10m"
  }
}

resource "aws_route53_record" "review_acm" {
  for_each = {
    for dvo in aws_acm_certificate.review.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}
```

**Additions to** `alb.tf` — additional HTTPS certificate on the existing listener:

```hcl
resource "aws_lb_listener_certificate" "review" {
  listener_arn    = aws_lb_listener.https_forward.arn
  certificate_arn = aws_acm_certificate_validation.review.certificate_arn
}
```

### 1.1.4 Workflow: Create Review Environment

This workflow is triggered when the `review-deploy` label is added to a PR, or when new commits are pushed to a PR that already has the label.

**File:** `.github/workflows/review-deploy.yml`

```yaml
name: Review Environment Deploy
on:
  pull_request:
    types: [labeled, synchronize]

# Prevent concurrent deploys for the same PR
concurrency:
  group: review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

env:
  REVIEW_PREFIX: review-pr${{ github.event.pull_request.number }}
  PR_NUMBER: ${{ github.event.pull_request.number }}

jobs:
  check-label:
    name: Check for review-deploy label
    runs-on: ubuntu-latest
    outputs:
      should_deploy: ${{ steps.check.outputs.should_deploy }}
    steps:
      - name: Check if review-deploy label exists
        id: check
        run: |
          LABELS='${{ toJSON(github.event.pull_request.labels.*.name) }}'
          if echo "$LABELS" | grep -q "review-deploy"; then
            echo "should_deploy=true" >> $GITHUB_OUTPUT
          else
            echo "should_deploy=false" >> $GITHUB_OUTPUT
          fi

  deploy-review:
    name: Deploy Review Environment
    needs: check-label
    if: needs.check-label.outputs.should_deploy == 'true'
    runs-on: ubuntu-latest
    environment: review
    permissions:
      id-token: write        # required for OIDC
      contents: read
      pull-requests: write   # required to post PR comments
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_GITHUB_ACTIONS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      # ── Build and push Docker image ────────────────────────────
      - name: Build and push image
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: ${{ vars.DOCKER_REPO_NAME }}
          IMAGE_TAG: review-pr${{ env.PR_NUMBER }}-${{ github.event.pull_request.head.sha }}
        run: |
          docker build -f Dockerfile . \
            -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      # ── Restore database from staging snapshot ─────────────────
      - name: Check if review database exists
        id: check-db
        run: |
          DB_EXISTS=$(aws rds describe-db-instances \
            --query "DBInstances[?DBInstanceIdentifier=='${{ env.REVIEW_PREFIX }}'].DBInstanceIdentifier" \
            --output text 2>/dev/null || echo "")
          echo "exists=$([[ -n "$DB_EXISTS" ]] && echo true || echo false)" >> $GITHUB_OUTPUT

      - name: Get latest staging snapshot
        if: steps.check-db.outputs.exists == 'false'
        id: snapshot
        run: |
          SNAPSHOT_ID=$(aws rds describe-db-snapshots \
            --db-instance-identifier ${{ vars.STAGING_DB_INSTANCE_ID }} \
            --query "reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[0].DBSnapshotIdentifier" \
            --output text)
          echo "snapshot_id=$SNAPSHOT_ID" >> $GITHUB_OUTPUT

      - name: Restore database from staging snapshot
        if: steps.check-db.outputs.exists == 'false'
        run: |
          aws rds restore-db-instance-from-db-snapshot \
            --db-instance-identifier ${{ env.REVIEW_PREFIX }} \
            --db-snapshot-identifier ${{ steps.snapshot.outputs.snapshot_id }} \
            --db-instance-class db.t3.micro \
            --vpc-security-group-ids ${{ vars.REVIEW_DB_SECURITY_GROUP_ID }} \
            --db-subnet-group-name ${{ vars.DB_SUBNET_GROUP_NAME }} \
            --no-multi-az \
            --tags Key=Environment,Value=review Key=PR,Value=${{ env.PR_NUMBER }} \
              Key=ManagedBy,Value=github-actions

      - name: Wait for database to be available
        if: steps.check-db.outputs.exists == 'false'
        run: |
          aws rds wait db-instance-available \
            --db-instance-identifier ${{ env.REVIEW_PREFIX }}

      - name: Get review database endpoint
        id: db-endpoint
        run: |
          ENDPOINT=$(aws rds describe-db-instances \
            --db-instance-identifier ${{ env.REVIEW_PREFIX }} \
            --query "DBInstances[0].Endpoint.Address" \
            --output text)
          echo "endpoint=$ENDPOINT" >> $GITHUB_OUTPUT

      # ── Create or update ECS task definition ───────────────────
      - name: Register web task definition
        id: web-task-def
        run: |
          TASK_DEF=$(cat <<'TASKEOF'
          {
            "family": "${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "256",
            "memory": "512",
            "executionRoleArn": "${{ vars.ECS_EXECUTION_ROLE_ARN }}",
            "taskRoleArn": "${{ vars.ECS_TASK_ROLE_ARN }}",
            "containerDefinitions": [
              {
                "name": "${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web",
                "image": "${{ steps.build-image.outputs.image }}",
                "essential": true,
                "portMappings": [
                  {
                    "containerPort": 3000,
                    "hostPort": 3000
                  }
                ],
                "environment": [
                  { "name": "RAILS_ENV", "value": "staging" },
                  { "name": "DATABASE_URL", "value": "postgresql://${{ secrets.REVIEW_DB_USER }}:${{ secrets.REVIEW_DB_PASSWORD }}@${{ steps.db-endpoint.outputs.endpoint }}:5432/${{ vars.REVIEW_DB_NAME }}" },
                  { "name": "LOG_LEVEL", "value": "debug" },
                  { "name": "DOMAIN", "value": "pr-${{ env.PR_NUMBER }}.review.${{ vars.ROOT_DOMAIN }}" }
                ],
                "logConfiguration": {
                  "logDriver": "awslogs",
                  "options": {
                    "awslogs-group": "/aws/ecs/${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}",
                    "awslogs-region": "${{ vars.AWS_REGION }}",
                    "awslogs-stream-prefix": "web",
                    "awslogs-create-group": "true"
                  }
                }
              }
            ]
          }
          TASKEOF
          )

          # Register the task definition
          TASK_ARN=$(aws ecs register-task-definition \
            --cli-input-json "$TASK_DEF" \
            --query "taskDefinition.taskDefinitionArn" \
            --output text)
          echo "task_arn=$TASK_ARN" >> $GITHUB_OUTPUT

      # ── Create or update ECS service ───────────────────────────
      - name: Check if ECS service exists
        id: check-service
        run: |
          SERVICE_STATUS=$(aws ecs describe-services \
            --cluster ${{ vars.ECS_CLUSTER_NAME }} \
            --services ${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web \
            --query "services[0].status" \
            --output text 2>/dev/null || echo "MISSING")
          echo "exists=$([[ "$SERVICE_STATUS" == "ACTIVE" ]] && echo true || echo false)" >> $GITHUB_OUTPUT

      - name: Create ECS service
        if: steps.check-service.outputs.exists == 'false'
        run: |
          aws ecs create-service \
            --cluster ${{ vars.ECS_CLUSTER_NAME }} \
            --service-name ${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web \
            --task-definition ${{ steps.web-task-def.outputs.task_arn }} \
            --desired-count 1 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[${{ vars.PRIVATE_SUBNET_IDS }}],securityGroups=[${{ vars.ECS_SECURITY_GROUP_ID }}]}" \
            --load-balancers "targetGroupArn=${{ steps.target-group.outputs.arn }},containerName=${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web,containerPort=3000" \
            --health-check-grace-period-seconds 60 \
            --tags key=Environment,value=review key=PR,value=${{ env.PR_NUMBER }} key=ManagedBy,value=github-actions

      - name: Update ECS service
        if: steps.check-service.outputs.exists == 'true'
        run: |
          aws ecs update-service \
            --cluster ${{ vars.ECS_CLUSTER_NAME }} \
            --service ${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web \
            --task-definition ${{ steps.web-task-def.outputs.task_arn }} \
            --force-new-deployment

      # ── Create ALB target group and listener rule ──────────────
      - name: Create target group (if needed)
        id: target-group
        run: |
          TG_ARN=$(aws elbv2 describe-target-groups \
            --names "${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}" \
            --query "TargetGroups[0].TargetGroupArn" \
            --output text 2>/dev/null || echo "")

          if [[ -z "$TG_ARN" || "$TG_ARN" == "None" ]]; then
            TG_ARN=$(aws elbv2 create-target-group \
              --name "${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}" \
              --protocol HTTP \
              --port 3000 \
              --vpc-id ${{ vars.VPC_ID }} \
              --target-type ip \
              --health-check-path "/" \
              --health-check-interval-seconds 30 \
              --healthy-threshold-count 2 \
              --unhealthy-threshold-count 3 \
              --query "TargetGroups[0].TargetGroupArn" \
              --output text)
          fi
          echo "arn=$TG_ARN" >> $GITHUB_OUTPUT

      - name: Create listener rule for host-based routing
        run: |
          # Check if rule already exists
          EXISTING_RULE=$(aws elbv2 describe-rules \
            --listener-arn ${{ vars.ALB_HTTPS_LISTENER_ARN }} \
            --query "Rules[?Conditions[?Values[?contains(@, 'pr-${{ env.PR_NUMBER }}.review')]]]" \
            --output text 2>/dev/null || echo "")

          if [[ -z "$EXISTING_RULE" || "$EXISTING_RULE" == "None" ]]; then
            # Find next available priority
            MAX_PRIORITY=$(aws elbv2 describe-rules \
              --listener-arn ${{ vars.ALB_HTTPS_LISTENER_ARN }} \
              --query "max(Rules[?Priority!='default'].Priority)" \
              --output text 2>/dev/null || echo "0")
            NEXT_PRIORITY=$((MAX_PRIORITY + 1))

            aws elbv2 create-rule \
              --listener-arn ${{ vars.ALB_HTTPS_LISTENER_ARN }} \
              --priority $NEXT_PRIORITY \
              --conditions "Field=host-header,Values=['pr-${{ env.PR_NUMBER }}.review.${{ vars.ROOT_DOMAIN }}']" \
              --actions "Type=forward,TargetGroupArn=${{ steps.target-group.outputs.arn }}"
          fi

      # ── Create DNS record ──────────────────────────────────────
      - name: Create Route53 record
        run: |
          aws route53 change-resource-record-sets \
            --hosted-zone-id ${{ vars.ROUTE53_ZONE_ID }} \
            --change-batch '{
              "Changes": [{
                "Action": "UPSERT",
                "ResourceRecordSet": {
                  "Name": "pr-${{ env.PR_NUMBER }}.review.${{ vars.ROOT_DOMAIN }}",
                  "Type": "A",
                  "AliasTarget": {
                    "HostedZoneId": "${{ vars.ALB_HOSTED_ZONE_ID }}",
                    "DNSName": "${{ vars.ALB_DNS_NAME }}",
                    "EvaluateTargetHealth": true
                  }
                }
              }]
            }'

      # ── Wait for service stability ─────────────────────────────
      - name: Wait for service stability
        run: |
          aws ecs wait services-stable \
            --cluster ${{ vars.ECS_CLUSTER_NAME }} \
            --services ${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web

      # ── Post PR comment with environment URL ───────────────────
      - name: Post PR comment
        uses: actions/github-script@v7
        with:
          script: |
            const body = [
              `### Review Environment Ready`,
              ``,
              `| | |`,
              `|---|---|`,
              `| **URL** | https://pr-${{ env.PR_NUMBER }}.review.${{ vars.ROOT_DOMAIN }} |`,
              `| **Image** | \`${{ steps.build-image.outputs.image }}\` |`,
              `| **Commit** | ${{ github.event.pull_request.head.sha }} |`,
              `| **Database** | Restored from staging snapshot |`,
              ``,
              `> Remove the \`review-deploy\` label or merge/close this PR to tear down the environment.`,
            ].join('\n');

            // Delete previous review environment comments
            const comments = await github.rest.issues.listComments({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: ${{ env.PR_NUMBER }},
            });
            for (const comment of comments.data) {
              if (comment.body.includes('### Review Environment')) {
                await github.rest.issues.deleteComment({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  comment_id: comment.id,
                });
              }
            }

            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: ${{ env.PR_NUMBER }},
              body: body,
            });
```

### 1.1.5 Workflow: Destroy Review Environment

This workflow triggers when a PR is closed (merged or abandoned), or when the `review-deploy` label is removed. It tears down all review resources and notifies the PR author.

**File:** `.github/workflows/review-destroy.yml`

```yaml
name: Review Environment Destroy
on:
  pull_request:
    types: [closed, unlabeled]

env:
  REVIEW_PREFIX: review-pr${{ github.event.pull_request.number }}
  PR_NUMBER: ${{ github.event.pull_request.number }}

jobs:
  check-trigger:
    name: Check if teardown is needed
    runs-on: ubuntu-latest
    outputs:
      should_destroy: ${{ steps.check.outputs.should_destroy }}
      trigger_reason: ${{ steps.check.outputs.trigger_reason }}
    steps:
      - name: Determine if teardown is needed
        id: check
        run: |
          if [[ "${{ github.event.action }}" == "closed" ]]; then
            echo "should_destroy=true" >> $GITHUB_OUTPUT
            if [[ "${{ github.event.pull_request.merged }}" == "true" ]]; then
              echo "trigger_reason=PR #${{ env.PR_NUMBER }} was merged" >> $GITHUB_OUTPUT
            else
              echo "trigger_reason=PR #${{ env.PR_NUMBER }} was closed" >> $GITHUB_OUTPUT
            fi
          elif [[ "${{ github.event.action }}" == "unlabeled" ]]; then
            if [[ "${{ github.event.label.name }}" == "review-deploy" ]]; then
              echo "should_destroy=true" >> $GITHUB_OUTPUT
              echo "trigger_reason=review-deploy label was removed from PR #${{ env.PR_NUMBER }}" >> $GITHUB_OUTPUT
            else
              echo "should_destroy=false" >> $GITHUB_OUTPUT
            fi
          else
            echo "should_destroy=false" >> $GITHUB_OUTPUT
          fi

  destroy-review:
    name: Destroy Review Environment
    needs: check-trigger
    if: needs.check-trigger.outputs.should_destroy == 'true'
    runs-on: ubuntu-latest
    environment: review
    permissions:
      id-token: write        # required for OIDC
      contents: read
      pull-requests: write   # required to post PR comments
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_GITHUB_ACTIONS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      # ── Delete ECS service ─────────────────────────────────────
      - name: Scale down and delete ECS service
        run: |
          # Scale to 0 first for graceful shutdown
          aws ecs update-service \
            --cluster ${{ vars.ECS_CLUSTER_NAME }} \
            --service ${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web \
            --desired-count 0 \
            2>/dev/null || echo "Service not found, skipping"

          # Wait for tasks to drain
          sleep 30

          # Delete the service
          aws ecs delete-service \
            --cluster ${{ vars.ECS_CLUSTER_NAME }} \
            --service ${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}-Web \
            --force \
            2>/dev/null || echo "Service not found, skipping"

      # ── Delete ALB listener rule and target group ──────────────
      - name: Delete ALB listener rule
        run: |
          RULE_ARN=$(aws elbv2 describe-rules \
            --listener-arn ${{ vars.ALB_HTTPS_LISTENER_ARN }} \
            --query "Rules[?Conditions[?Values[?contains(@, 'pr-${{ env.PR_NUMBER }}.review')]]].RuleArn" \
            --output text 2>/dev/null || echo "")

          if [[ -n "$RULE_ARN" && "$RULE_ARN" != "None" ]]; then
            aws elbv2 delete-rule --rule-arn "$RULE_ARN"
          fi

      - name: Delete target group
        run: |
          TG_ARN=$(aws elbv2 describe-target-groups \
            --names "${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}" \
            --query "TargetGroups[0].TargetGroupArn" \
            --output text 2>/dev/null || echo "")

          if [[ -n "$TG_ARN" && "$TG_ARN" != "None" ]]; then
            aws elbv2 delete-target-group --target-group-arn "$TG_ARN"
          fi

      # ── Delete DNS record ──────────────────────────────────────
      - name: Delete Route53 record
        run: |
          aws route53 change-resource-record-sets \
            --hosted-zone-id ${{ vars.ROUTE53_ZONE_ID }} \
            --change-batch '{
              "Changes": [{
                "Action": "DELETE",
                "ResourceRecordSet": {
                  "Name": "pr-${{ env.PR_NUMBER }}.review.${{ vars.ROOT_DOMAIN }}",
                  "Type": "A",
                  "AliasTarget": {
                    "HostedZoneId": "${{ vars.ALB_HOSTED_ZONE_ID }}",
                    "DNSName": "${{ vars.ALB_DNS_NAME }}",
                    "EvaluateTargetHealth": true
                  }
                }
              }]
            }' 2>/dev/null || echo "DNS record not found, skipping"

      # ── Delete review database ─────────────────────────────────
      - name: Delete review database
        run: |
          aws rds delete-db-instance \
            --db-instance-identifier ${{ env.REVIEW_PREFIX }} \
            --skip-final-snapshot \
            --delete-automated-backups \
            2>/dev/null || echo "Database not found, skipping"

      # ── Delete CloudWatch log group ────────────────────────────
      - name: Delete log group
        run: |
          aws logs delete-log-group \
            --log-group-name "/aws/ecs/${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}" \
            2>/dev/null || echo "Log group not found, skipping"

      # ── Deregister task definitions ────────────────────────────
      - name: Deregister task definitions
        run: |
          TASK_DEFS=$(aws ecs list-task-definitions \
            --family-prefix "${{ vars.APPLICATION_NAME }}-Review-PR${{ env.PR_NUMBER }}" \
            --query "taskDefinitionArns" \
            --output text 2>/dev/null || echo "")

          for TASK_DEF in $TASK_DEFS; do
            aws ecs deregister-task-definition \
              --task-definition "$TASK_DEF" 2>/dev/null || true
          done

      # ── Notify: Post PR comment ────────────────────────────────
      - name: Post teardown comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const reason = `${{ needs.check-trigger.outputs.trigger_reason }}`;
            const body = [
              `### Review Environment Destroyed`,
              ``,
              `**Reason:** ${reason}`,
              `**Time:** ${new Date().toISOString()}`,
              ``,
              `> To redeploy, add the \`review-deploy\` label to a new or reopened PR.`,
            ].join('\n');

            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: ${{ env.PR_NUMBER }},
              body: body,
            });
```

### 1.1.6 Workflow: Nightly Stale Environment Cleanup

A scheduled workflow runs nightly to catch any review environments that were not cleaned up by the normal triggers (e.g., the destroy workflow failed, or a PR sits open with no activity).

**File:** `.github/workflows/review-cleanup.yml`

```yaml
name: Review Environment Cleanup
on:
  schedule:
    # Run at 2am UTC every night
    - cron: '0 2 * * *'
  workflow_dispatch: # Allow manual trigger for immediate cleanup

env:
  STALE_HOURS: 48

jobs:
  cleanup:
    name: Clean up stale review environments
    runs-on: ubuntu-latest
    environment: review
    permissions:
      id-token: write        # required for OIDC
      contents: read
      pull-requests: write   # required to post PR comments
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_GITHUB_ACTIONS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Find and clean stale review environments
        uses: actions/github-script@v7
        with:
          script: |
            const { execSync } = require('child_process');
            const staleHours = parseInt('${{ env.STALE_HOURS }}');
            const appName = '${{ vars.APPLICATION_NAME }}';
            const cluster = '${{ vars.ECS_CLUSTER_NAME }}';

            // List all review ECS services
            const servicesOutput = execSync(
              `aws ecs list-services --cluster ${cluster} --query "serviceArns" --output json`
            ).toString();
            const allServices = JSON.parse(servicesOutput);
            const reviewServices = allServices.filter(arn =>
              arn.includes('-Review-PR')
            );

            if (reviewServices.length === 0) {
              console.log('No review environments found.');
              return;
            }

            console.log(`Found ${reviewServices.length} review service(s).`);

            for (const serviceArn of reviewServices) {
              // Extract PR number from service name
              const match = serviceArn.match(/Review-PR(\d+)/);
              if (!match) continue;
              const prNumber = parseInt(match[1]);

              console.log(`\nChecking PR #${prNumber}...`);

              // Check PR state
              let prState, prUpdatedAt;
              try {
                const pr = await github.rest.pulls.get({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  pull_number: prNumber,
                });
                prState = pr.data.state;
                prUpdatedAt = new Date(pr.data.updated_at);
              } catch (e) {
                console.log(`  PR #${prNumber} not found, marking for cleanup.`);
                prState = 'not_found';
              }

              let shouldDestroy = false;
              let reason = '';

              if (prState === 'closed' || prState === 'not_found') {
                shouldDestroy = true;
                reason = `PR is ${prState}`;
              } else {
                // Check if PR has the label
                const labels = (await github.rest.issues.listLabelsOnIssue({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  issue_number: prNumber,
                })).data.map(l => l.name);

                if (!labels.includes('review-deploy')) {
                  shouldDestroy = true;
                  reason = 'review-deploy label was removed';
                } else {
                  // Check staleness
                  const hoursSinceUpdate =
                    (Date.now() - prUpdatedAt.getTime()) / (1000 * 60 * 60);
                  if (hoursSinceUpdate > staleHours) {
                    shouldDestroy = true;
                    reason = `PR inactive for ${Math.round(hoursSinceUpdate)} hours (threshold: ${staleHours}h)`;
                  }
                }
              }

              if (shouldDestroy) {
                console.log(`  Destroying: ${reason}`);

                // Trigger the destroy workflow for this PR
                try {
                  // Scale down service
                  execSync(
                    `aws ecs update-service --cluster ${cluster} ` +
                    `--service ${appName}-Review-PR${prNumber}-Web ` +
                    `--desired-count 0 2>/dev/null || true`
                  );
                  execSync('sleep 15');
                  execSync(
                    `aws ecs delete-service --cluster ${cluster} ` +
                    `--service ${appName}-Review-PR${prNumber}-Web ` +
                    `--force 2>/dev/null || true`
                  );

                  // Delete database
                  execSync(
                    `aws rds delete-db-instance ` +
                    `--db-instance-identifier review-pr${prNumber} ` +
                    `--skip-final-snapshot --delete-automated-backups ` +
                    `2>/dev/null || true`
                  );

                  // Delete ALB resources
                  const ruleArn = execSync(
                    `aws elbv2 describe-rules ` +
                    `--listener-arn ${{ vars.ALB_HTTPS_LISTENER_ARN }} ` +
                    `--query "Rules[?Conditions[?Values[?contains(@, 'pr-${prNumber}.review')]]].RuleArn" ` +
                    `--output text 2>/dev/null || echo ""`
                  ).toString().trim();
                  if (ruleArn && ruleArn !== 'None') {
                    execSync(`aws elbv2 delete-rule --rule-arn "${ruleArn}" 2>/dev/null || true`);
                  }

                  const tgArn = execSync(
                    `aws elbv2 describe-target-groups ` +
                    `--names "${appName}-Review-PR${prNumber}" ` +
                    `--query "TargetGroups[0].TargetGroupArn" ` +
                    `--output text 2>/dev/null || echo ""`
                  ).toString().trim();
                  if (tgArn && tgArn !== 'None') {
                    execSync(`aws elbv2 delete-target-group --target-group-arn "${tgArn}" 2>/dev/null || true`);
                  }

                  // Delete DNS record
                  execSync(
                    `aws route53 change-resource-record-sets ` +
                    `--hosted-zone-id ${{ vars.ROUTE53_ZONE_ID }} ` +
                    `--change-batch '{"Changes":[{"Action":"DELETE","ResourceRecordSet":{"Name":"pr-${prNumber}.review.${{ vars.ROOT_DOMAIN }}","Type":"A","AliasTarget":{"HostedZoneId":"${{ vars.ALB_HOSTED_ZONE_ID }}","DNSName":"${{ vars.ALB_DNS_NAME }}","EvaluateTargetHealth":true}}}]}' ` +
                    `2>/dev/null || true`
                  );

                  // Delete log group
                  execSync(
                    `aws logs delete-log-group ` +
                    `--log-group-name "/aws/ecs/${appName}-Review-PR${prNumber}" ` +
                    `2>/dev/null || true`
                  );

                  // Deregister task definitions
                  const taskDefs = execSync(
                    `aws ecs list-task-definitions ` +
                    `--family-prefix "${appName}-Review-PR${prNumber}" ` +
                    `--query "taskDefinitionArns" --output json 2>/dev/null || echo "[]"`
                  ).toString().trim();
                  for (const td of JSON.parse(taskDefs)) {
                    execSync(`aws ecs deregister-task-definition --task-definition "${td}" 2>/dev/null || true`);
                  }

                  console.log(`  Successfully destroyed review environment for PR #${prNumber}.`);

                  // Notify on PR if it's still open
                  if (prState === 'open') {
                    await github.rest.issues.createComment({
                      owner: context.repo.owner,
                      repo: context.repo.repo,
                      issue_number: prNumber,
                      body: [
                        `### Review Environment Destroyed (Stale Cleanup)`,
                        ``,
                        `**Reason:** ${reason}`,
                        `**Time:** ${new Date().toISOString()}`,
                        ``,
                        `This environment was automatically cleaned up by the nightly stale environment audit.`,
                        `To redeploy, add the \`review-deploy\` label again.`,
                      ].join('\n'),
                    });
                  }
                } catch (e) {
                  console.log(`  Error destroying PR #${prNumber}: ${e.message}`);
                }
              } else {
                console.log(`  Active and within staleness threshold. Keeping.`);
              }
            }
```

### 1.1.7 Required GitHub Actions Environment Variables

The review workflows reference these variables which must be configured in a GitHub Actions `review` environment:

| Variable | Type | Description |
| --- | --- | --- |
| `AWS_GITHUB_ACTIONS_ROLE_ARN` | Variable | ARN of the IAM role GitHub Actions assumes via OIDC — must have ECS, RDS, ELB, Route53, ECR, CloudWatch, Logs permissions. Not a secret; secured by the OIDC trust policy. |
| `AWS_REGION` | Variable | AWS region (e.g., `us-west-2`) |
| `APPLICATION_NAME` | Variable | PascalCase application name (e.g., `PaymentManager`) |
| `DOCKER_REPO_NAME` | Variable | ECR repository name |
| `ECS_CLUSTER_NAME` | Variable | ECS cluster name (shared with staging) |
| `ECS_EXECUTION_ROLE_ARN` | Variable | ARN of the ECS task execution role |
| `ECS_TASK_ROLE_ARN` | Variable | ARN of the ECS task role |
| `ECS_SECURITY_GROUP_ID` | Variable | Security group for ECS tasks |
| `PRIVATE_SUBNET_IDS` | Variable | Comma-separated private subnet IDs |
| `VPC_ID` | Variable | VPC ID (shared with staging) |
| `ALB_HTTPS_LISTENER_ARN` | Variable | ARN of the HTTPS listener on the shared ALB |
| `ALB_DNS_NAME` | Variable | DNS name of the shared ALB |
| `ALB_HOSTED_ZONE_ID` | Variable | Route53 hosted zone ID of the ALB |
| `ROOT_DOMAIN` | Variable | Root domain (e.g., `bnkflow.com`) |
| `ROUTE53_ZONE_ID` | Variable | Route53 hosted zone ID |
| `STAGING_DB_INSTANCE_ID` | Variable | RDS instance ID of the staging database |
| `REVIEW_DB_SECURITY_GROUP_ID` | Variable | Security group for review databases |
| `DB_SUBNET_GROUP_NAME` | Variable | RDS subnet group name |
| `REVIEW_DB_USER` | Secret | Database username for review environments |
| `REVIEW_DB_PASSWORD` | Secret | Database password for review environments |
| `REVIEW_DB_NAME` | Variable | Database name within the RDS instance |

### 1.1.8 Notification Summary

Review environments produce PR comment notifications at every lifecycle transition so the team always knows the current state:

| Event | PR Comment |
| --- | --- |
| Environment created | "Review Environment Ready" with URL, image, commit |
| Environment updated (new push) | Previous comment deleted, new "Review Environment Ready" |
| Environment destroyed (PR merged) | "Review Environment Destroyed — PR was merged" |
| Environment destroyed (PR closed) | "Review Environment Destroyed — PR was closed" |
| Environment destroyed (label removed) | "Review Environment Destroyed — label removed" |
| Environment destroyed (stale cleanup) | "Review Environment Destroyed (Stale Cleanup)" with reason and instructions to re-add label |

### 1.1.9 Cost Controls

| Control | Details |
| --- | --- |
| Label-gated creation | Environments only exist when explicitly requested — no surprise costs from routine PRs |
| Auto-teardown on merge/close | No orphaned environments from completed work |
| Auto-teardown on label removal | Quick manual teardown without leaving GitHub |
| 48-hour stale cleanup | Catches environments where the destroy workflow failed or was skipped |
| FARGATE_SPOT for review tasks | Review environments are non-critical — use 100% Spot capacity |
| `db.t3.micro` for review databases | Smallest RDS instance; sufficient for testing |
| No Multi-AZ for review databases | Single-AZ is sufficient for ephemeral environments |
| `skip-final-snapshot` on deletion | No snapshot costs accumulate from destroyed review databases |
| Shared ALB and cluster | Review environments share infrastructure with staging, avoiding per-environment ALB costs ($16/month each) |

**Estimated per-environment cost:**

* Fargate (256 CPU / 512 MiB, SPOT): ~$0.50-1.00/day
* RDS (db.t3.micro): ~$0.50/day
* ALB listener rule: free (shared listener)
* Route53 record: $0.50/month (negligible)
* **Total: ~$1-2/day per active review environment**

With 5-10 active review environments at peak (most lasting 1-3 days), expected monthly cost is $50-150.
