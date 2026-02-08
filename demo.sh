#!/bin/bash

# LifeOS Task Orchestrator - Quick Demo
# This script demonstrates the core functionality

set -e

API_URL="${API_URL:-http://localhost:8080}"

echo "=================================="
echo "LifeOS Task Orchestrator - Demo"
echo "=================================="
echo ""
echo "API URL: ${API_URL}"
echo ""

# Check if API is running
echo "1. Checking API health..."
HEALTH=$(curl -s "${API_URL}/api/v1/health")
echo "   Health: $(echo $HEALTH | jq -r '.status')"
echo ""

# List available agents
echo "2. Listing available agents..."
AGENTS=$(curl -s "${API_URL}/api/v1/agents")
echo "   Available agents: $(echo $AGENTS | jq -r '.registered_agents | keys | join(", ")')"
echo ""

# Create an email task
echo "3. Creating an email task..."
TASK=$(curl -s -X POST "${API_URL}/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Send Welcome Email",
    "description": "Send welcome email to new user",
    "task_type": "email",
    "priority": "high",
    "input_data": {
      "action": "send",
      "to": "newuser@example.com",
      "subject": "Welcome to LifeOS!",
      "body": "Thank you for joining our platform."
    }
  }')

TASK_ID=$(echo $TASK | jq -r '.id')
echo "   Created task: $TASK_ID"
echo "   Status: $(echo $TASK | jq -r '.status')"
echo ""

# Execute the task
echo "4. Executing the task..."
EXECUTED=$(curl -s -X POST "${API_URL}/api/v1/tasks/${TASK_ID}/execute")
echo "   Execution status: $(echo $EXECUTED | jq -r '.status')"
if [ "$(echo $EXECUTED | jq -r '.status')" = "completed" ]; then
  echo "   ✓ Task completed successfully!"
  echo "   Output: $(echo $EXECUTED | jq -r '.output_data.message_id')"
fi
echo ""

# Create a workflow
echo "5. Creating a workflow with multiple tasks..."
WORKFLOW=$(curl -s -X POST "${API_URL}/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Onboarding",
    "description": "Complete onboarding workflow for new users",
    "tasks": [
      {
        "name": "Send Welcome Email",
        "task_type": "email",
        "priority": "high",
        "input_data": {
          "action": "send",
          "to": "user@example.com",
          "subject": "Welcome!"
        }
      },
      {
        "name": "Process User Data",
        "task_type": "data_processing",
        "priority": "medium",
        "input_data": {
          "operation": "transform",
          "data": [{"user": "new"}]
        }
      },
      {
        "name": "Notify Team",
        "task_type": "notification",
        "priority": "low",
        "input_data": {
          "channel": "slack",
          "message": "New user onboarded!"
        }
      }
    ]
  }')

WORKFLOW_ID=$(echo $WORKFLOW | jq -r '.id')
echo "   Created workflow: $WORKFLOW_ID"
echo "   Number of tasks: $(echo $WORKFLOW | jq -r '.tasks | length')"
echo ""

# Execute the workflow
echo "6. Executing the workflow..."
EXECUTED_WF=$(curl -s -X POST "${API_URL}/api/v1/workflows/${WORKFLOW_ID}/execute")
echo "   Workflow status: $(echo $EXECUTED_WF | jq -r '.status')"
COMPLETED=$(echo $EXECUTED_WF | jq -r '.output_data.tasks_completed')
FAILED=$(echo $EXECUTED_WF | jq -r '.output_data.tasks_failed')
echo "   Tasks completed: $COMPLETED"
echo "   Tasks failed: $FAILED"
echo ""

# List all tasks
echo "7. Listing all tasks..."
TASKS=$(curl -s "${API_URL}/api/v1/tasks?limit=10")
TOTAL=$(echo $TASKS | jq -r '.meta.total')
echo "   Total tasks: $TOTAL"
echo ""

echo "=================================="
echo "Demo Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Visit ${API_URL}/docs for interactive API documentation"
echo "2. Check README.md for detailed usage examples"
echo "3. Review docs/ARCHITECTURE.md for system design"
echo ""
