"""
Advanced Real-World Communication Examples for Streamware
=========================================================

These examples demonstrate production-ready scenarios combining
multiple communication channels with business logic.
"""

import asyncio
from datetime import datetime, timedelta
from streamware import flow, multicast, split, join, choose


# ========== CUSTOMER SUPPORT SYSTEM ==========

def customer_support_system():
    """
    Complete customer support system with ticket routing and escalation
    """
    print("=== Customer Support System ===")
    
    # 1. Receive support requests from multiple channels
    support_pipeline = (
        flow("multicast://parallel=true")
        .destinations([
            "email-watch://folder=support&interval=60",
            "telegram-bot://token=SUPPORT_BOT_TOKEN",
            "whatsapp-webhook://",
            "slack-events://channel=support",
            "discord-bot://token=DISCORD_TOKEN"
        ])
        | "transform://normalize_support_request"
        | "curllm://extract?instruction=Categorize urgency: critical/high/normal/low"
        | "postgres://insert?table=support_tickets"
        | "choose://"
          .when("$.urgency == 'critical'", [
              "sms://send?to={{oncall_engineer}}",
              "slack://send?channel=critical-alerts",
              "pagerduty://create_incident"
          ])
          .when("$.urgency == 'high'", [
              "slack://send?channel=support-high",
              "email://send?to=support-team@company.com"
          ])
          .otherwise([
              "slack://send?channel=support-queue"
          ])
    )
    
    # 2. Auto-response based on category
    auto_response_flow = (
        flow("postgres://query?sql=SELECT * FROM support_tickets WHERE status='new'")
        | "split://"
        | "curllm://chat?instruction=Generate helpful auto-response based on issue"
        | "choose://"
          .when("$.channel == 'email'", "email://send?to={{customer_email}}")
          .when("$.channel == 'telegram'", "telegram://send?chat_id={{chat_id}}")
          .when("$.channel == 'whatsapp'", "whatsapp://send?phone={{phone}}")
          .when("$.channel == 'slack'", "slack://send?channel={{thread_id}}")
        | "postgres://update?table=support_tickets&set=auto_responded=true"
    )
    
    # 3. Escalation workflow
    escalation_flow = (
        flow("postgres://query?sql=SELECT * FROM support_tickets WHERE created < NOW() - INTERVAL '2 hours' AND status='open'")
        | "filter://predicate=$.urgency in ['critical', 'high']"
        | "transform://add_escalation_level"
        | "multicast://destinations="
          "sms://send?to={{manager_phone}}&message=Ticket {{id}} needs attention,"
          "email://send?to=management@company.com&priority=high,"
          "slack://send?channel=escalations"
    )
    
    return {
        "support": support_pipeline,
        "auto_response": auto_response_flow,
        "escalation": escalation_flow
    }


# ========== E-COMMERCE ORDER NOTIFICATION SYSTEM ==========

def ecommerce_notifications():
    """
    Multi-channel order notification and tracking system
    """
    print("=== E-commerce Notification System ===")
    
    # Order confirmation across channels
    order_confirmation = (
        flow("kafka://consume?topic=new_orders")
        | "transform://json"
        | "postgres://insert?table=orders"
        | "multicast://parallel=true"
        .destinations([
            # Email with full details
            "transform://template?file=email_order_confirmation.html"
            | "email://send?to={{customer_email}}&subject=Order {{order_id}} Confirmed",
            
            # SMS with tracking link
            "transform://template?template=Order {{order_id}} confirmed! Track: {{tracking_url}}"
            | "sms://send?to={{customer_phone}}",
            
            # WhatsApp with template
            "whatsapp://template?template=order_confirmation&params={{order_id}},{{total}}",
            
            # Push to mobile app
            "firebase://push?token={{device_token}}&title=Order Confirmed",
            
            # Update CRM
            "salesforce://update?object=Contact&id={{customer_id}}"
        ])
    )
    
    # Shipping updates
    shipping_updates = (
        flow("webhook://path=/shipping/update")
        | "transform://json"
        | "postgres://update?table=orders&where=order_id={{order_id}}"
        | "choose://"
          .when("$.status == 'shipped'", [
              "email://send?template=order_shipped",
              "sms://send?message=Your order has been shipped!",
              "whatsapp://send_media?type=image&url={{shipping_label_url}}"
          ])
          .when("$.status == 'out_for_delivery'", [
              "sms://send?message=Your order is out for delivery today!",
              "telegram://send?text=📦 Your package is on its way!"
          ])
          .when("$.status == 'delivered'", [
              "email://send?template=order_delivered",
              "sms://send?message=Package delivered! Please rate your experience.",
              "wait://seconds=3600",
              "email://send?template=request_review"
          ])
    )
    
    # Abandoned cart recovery
    abandoned_cart = (
        flow("postgres://query?sql=SELECT * FROM carts WHERE updated < NOW() - INTERVAL '1 day' AND status='active'")
        | "split://"
        | "enrich://customer_preferences"
        | "choose://"
          .when("$.preference == 'email'", 
                "email://send?template=abandoned_cart")
          .when("$.preference == 'sms'", 
                "sms://send?message=You have items in your cart! Complete order: {{cart_url}}")
          .when("$.preference == 'whatsapp'", 
                "whatsapp://send?template=abandoned_cart")
        | "postgres://update?table=carts&set=reminder_sent=true"
    )
    
    return {
        "confirmation": order_confirmation,
        "shipping": shipping_updates,
        "abandoned_cart": abandoned_cart
    }


# ========== INCIDENT MANAGEMENT SYSTEM ==========

def incident_management():
    """
    Multi-tier incident response and communication system
    """
    print("=== Incident Management System ===")
    
    # Incident detection and initial response
    incident_detection = (
        flow("prometheus://alerts")
        | "filter://predicate=$.severity in ['critical', 'warning']"
        | "transform://enrich_with_runbook"
        | "postgres://insert?table=incidents"
        | "multicast://parallel=true"
        .destinations([
            # Create war room
            "slack://create_channel?name=incident-{{timestamp}}",
            "discord://create_thread?name=Incident {{id}}",
            
            # Notify on-call
            "pagerduty://trigger?service={{service_name}}",
            "sms://send?to={{oncall_phone}}&message=CRITICAL: {{alert_name}}",
            
            # Update status page
            "statuspage://create_incident?component={{component_id}}"
        ])
    )
    
    # Communication workflow
    incident_comms = (
        flow("postgres://watch?table=incidents&status=active")
        | "transform://generate_status_update"
        | "multicast://sequential=true"
        .destinations([
            # Internal updates
            "slack://send?channel=incident-{{id}}&blocks={{status_blocks}}",
            "email://send?to=engineering@company.com&subject=Incident Update",
            
            # Customer communication
            "choose://"
              .when("$.customer_impact == true", [
                  "statuspage://update?message={{public_message}}",
                  "twitter://post?status=We're investigating issues with {{service}}",
                  "email://send?to=customers&template=service_disruption"
              ]),
            
            # Executive updates
            "choose://"
              .when("$.duration > 30", [
                  "sms://send?to={{exec_phones}}&message=Ongoing incident: {{summary}}",
                  "teams://send?channel=leadership&card={{exec_summary}}"
              ])
        ])
    )
    
    # Post-incident workflow
    postmortem = (
        flow("postgres://query?sql=SELECT * FROM incidents WHERE status='resolved' AND postmortem_status='pending'")
        | "split://"
        | "transform://generate_postmortem_template"
        | "confluence://create_page?space=ENGINEERING&title=Postmortem {{incident_id}}"
        | "multicast://destinations="
          "slack://send?channel=engineering&text=Please review postmortem: {{url}},"
          "calendar://create_event?title=Postmortem Review&attendees={{participants}},"
          "jira://create_task?type=PostmortemAction&assignee={{incident_owner}}"
    )
    
    return {
        "detection": incident_detection,
        "communication": incident_comms,
        "postmortem": postmortem
    }


# ========== MARKETING AUTOMATION SYSTEM ==========

def marketing_automation():
    """
    Multi-channel marketing campaigns with personalization
    """
    print("=== Marketing Automation System ===")
    
    # Campaign execution
    campaign_flow = (
        flow("postgres://query?sql=SELECT * FROM campaign_audiences WHERE campaign_id={{id}}")
        | "split://"
        | "enrich://customer_profile"
        | "curllm://personalize?instruction=Personalize message for customer profile"
        | "choose://"
          .when("$.segment == 'vip'", [
              "email://send?template=vip_campaign&priority=high",
              "whatsapp://send?template=exclusive_offer",
              "sms://send?message=VIP Exclusive: {{offer}}"
          ])
          .when("$.segment == 'regular'", [
              "email://send?template=standard_campaign",
              "choose://"
                .when("$.sms_opted_in == true", 
                      "sms://send?message={{campaign_message}}")
          ])
          .when("$.segment == 'at_risk'", [
              "email://send?template=win_back",
              "wait://days=3",
              "email://send?template=win_back_followup",
              "wait://days=7",
              "sms://send?message=We miss you! Here's 20% off"
          ])
        | "postgres://insert?table=campaign_sends"
    )
    
    # A/B testing
    ab_test_flow = (
        flow("postgres://query?sql=SELECT * FROM ab_test_audience")
        | "split://"
        | "transform://assign_variant"
        | "choose://"
          .when("$.variant == 'A'", 
                "email://send?template=variant_a")
          .when("$.variant == 'B'",
                "email://send?template=variant_b")
        | "analytics://track?event=email_sent&variant={{variant}}"
    )
    
    # Engagement tracking
    engagement_tracking = (
        flow("webhook://path=/tracking/{{event_type}}")
        | "transform://json"
        | "postgres://insert?table=engagement_events"
        | "choose://"
          .when("$.event == 'email_open'", [
              "analytics://track?event=email_opened",
              "postgres://update?table=contacts&set=engagement_score=score+1"
          ])
          .when("$.event == 'link_click'", [
              "analytics://track?event=link_clicked",
              "postgres://update?table=contacts&set=engagement_score=score+5",
              "choose://"
                .when("$.high_intent == true",
                      "salesforce://create_lead?source=marketing_qualified")
          ])
          .when("$.event == 'unsubscribe'", [
              "postgres://update?table=contacts&set=unsubscribed=true",
              "email://send?to=marketing@company.com&subject=Unsubscribe Alert"
          ])
    )
    
    return {
        "campaign": campaign_flow,
        "ab_test": ab_test_flow,
        "engagement": engagement_tracking
    }


# ========== HR ONBOARDING SYSTEM ==========

def hr_onboarding():
    """
    Employee onboarding communication workflow
    """
    print("=== HR Onboarding System ===")
    
    # New hire communication
    onboarding_flow = (
        flow("workday://new_hires")
        | "transform://json"
        | "postgres://insert?table=employees"
        | "multicast://sequential=true"
        .destinations([
            # Day 1 communications
            "email://send?to={{employee_email}}&template=welcome_day1",
            "sms://send?to={{employee_phone}}&message=Welcome to the team! Check email for details",
            "slack://invite?email={{employee_email}}&channels=general,{{department}}",
            "teams://create_account?email={{employee_email}}",
            
            # IT setup
            "jira://create_ticket?type=IT_Setup&assignee=it-team",
            "email://send?to=it@company.com&template=new_hire_setup",
            
            # Manager notification
            "email://send?to={{manager_email}}&template=new_team_member",
            "calendar://create_event?title=1-on-1 with {{employee_name}}&attendees={{manager_email}},{{employee_email}}",
            
            # Buddy assignment
            "postgres://query?sql=SELECT email FROM employees WHERE department={{department}} AND is_buddy=true LIMIT 1"
            | "email://send?template=buddy_assignment"
        ])
    )
    
    # Onboarding task tracking
    task_tracking = (
        flow("postgres://query?sql=SELECT * FROM onboarding_tasks WHERE due_date=TODAY()")
        | "split://"
        | "choose://"
          .when("$.task_type == 'document'", 
                "email://send?to={{employee_email}}&template=document_reminder")
          .when("$.task_type == 'training'",
                "slack://send?channel=@{{employee_slack}}&text=Reminder: Complete {{training_name}}")
          .when("$.task_type == 'meeting'",
                "calendar://send_reminder?event_id={{meeting_id}}")
        | "postgres://update?table=onboarding_tasks&set=reminder_sent=true"
    )
    
    return {
        "onboarding": onboarding_flow,
        "tasks": task_tracking
    }


# ========== IOT MONITORING & ALERTS ==========

def iot_monitoring():
    """
    IoT device monitoring with multi-channel alerts
    """
    print("=== IoT Monitoring System ===")
    
    # Device health monitoring
    device_monitoring = (
        flow("mqtt://subscribe?topic=devices/+/telemetry")
        | "transform://json"
        | "postgres://upsert?table=device_status&key=device_id"
        | "choose://"
          .when("$.battery < 10", [
              "email://send?to=maintenance@company.com&subject=Low battery: {{device_id}}",
              "slack://send?channel=iot-alerts&text=🔋 Low battery on {{device_name}}"
          ])
          .when("$.temperature > 80", [
              "sms://send?to={{emergency_contact}}&message=ALERT: High temp on {{device_id}}",
              "pagerduty://trigger?urgency=high"
          ])
          .when("$.status == 'offline'", [
              "wait://seconds=300",  # Wait 5 minutes
              "mqtt://publish?topic=devices/{{device_id}}/ping",
              "wait://seconds=60",
              "choose://"
                .when("$.still_offline == true", [
                    "sms://send?to={{technician_phone}}&message=Device {{device_id}} offline",
                    "jira://create_ticket?type=maintenance"
                ])
          ])
    )
    
    # Predictive maintenance
    predictive_maintenance = (
        flow("postgres://query?sql=SELECT * FROM device_metrics WHERE anomaly_score > 0.8")
        | "curllm://analyze?instruction=Predict failure probability and recommended actions"
        | "choose://"
          .when("$.failure_probability > 0.7", [
              "email://send?to=maintenance@company.com&template=predictive_maintenance",
              "servicenow://create_work_order?priority=high",
              "teams://send?channel=field-service&card={{maintenance_card}}"
          ])
        | "postgres://insert?table=maintenance_predictions"
    )
    
    return {
        "monitoring": device_monitoring,
        "predictive": predictive_maintenance
    }


# ========== COMPLIANCE & AUDIT NOTIFICATIONS ==========

def compliance_notifications():
    """
    Compliance monitoring and audit trail notifications
    """
    print("=== Compliance & Audit System ===")
    
    # GDPR data requests
    gdpr_workflow = (
        flow("email://read?folder=gdpr-requests")
        | "email-filter://subject=Data Request"
        | "curllm://extract?instruction=Extract request type and user identifier"
        | "postgres://insert?table=gdpr_requests"
        | "choose://"
          .when("$.request_type == 'access'", [
              "postgres://query?sql=SELECT * FROM user_data WHERE user_id={{user_id}}",
              "transform://generate_data_report",
              "email://send?to={{requester_email}}&attachments={{report_file}}"
          ])
          .when("$.request_type == 'deletion'", [
              "jira://create_ticket?type=GDPR_Deletion&priority=high",
              "slack://send?channel=legal&text=New deletion request from {{user_id}}",
              "email://send?to={{requester_email}}&template=deletion_confirmation"
          ])
        | "postgres://update?table=gdpr_requests&set=status=completed"
    )
    
    # Audit notifications
    audit_alerts = (
        flow("postgres://watch?table=audit_log&severity=high")
        | "transform://format_audit_alert"
        | "multicast://destinations="
          "email://send?to=compliance@company.com&priority=high,"
          "slack://send?channel=audit-alerts,"
          "splunk://log?index=compliance"
        | "choose://"
          .when("$.requires_immediate_action == true", [
              "sms://send?to={{compliance_officer}}&message=Urgent: {{alert_summary}}",
              "pagerduty://trigger?service=compliance"
          ])
    )
    
    return {
        "gdpr": gdpr_workflow,
        "audit": audit_alerts
    }


# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    print("=" * 70)
    print("STREAMWARE ADVANCED COMMUNICATION EXAMPLES")
    print("=" * 70)
    
    # List all systems
    systems = [
        ("Customer Support", customer_support_system),
        ("E-commerce Notifications", ecommerce_notifications),
        ("Incident Management", incident_management),
        ("Marketing Automation", marketing_automation),
        ("HR Onboarding", hr_onboarding),
        ("IoT Monitoring", iot_monitoring),
        ("Compliance Notifications", compliance_notifications),
    ]
    
    for name, system_func in systems:
        print(f"\n{'='*50}")
        print(f"Configuring: {name}")
        print(f"{'='*50}")
        
        try:
            workflows = system_func()
            for workflow_name, workflow in workflows.items():
                print(f"  ✓ {workflow_name} pipeline configured")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n" + "=" * 70)
    print("All systems configured successfully!")
    print("=" * 70)
    
    # Example of running a specific workflow
    print("\n" + "=" * 70)
    print("Example: Running Customer Support Auto-Response")
    print("=" * 70)
    
    # Simulate a support ticket
    test_ticket = {
        "id": "TICKET-001",
        "channel": "email",
        "customer_email": "customer@example.com",
        "subject": "Cannot login to account",
        "message": "I forgot my password and can't reset it",
        "urgency": "normal"
    }
    
    print(f"\nTest ticket: {test_ticket}")
    
    # This would actually run the pipeline if services were configured
    # result = support_system["auto_response"].run(test_ticket)
    # print(f"Auto-response sent: {result}")
