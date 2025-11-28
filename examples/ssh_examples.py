#!/usr/bin/env python3
"""
SSH Component Examples - Quick Style

Demonstrates SSH operations using the new sq command and SSH component.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamware import flow
from streamware.components.ssh import ssh_upload, ssh_download, ssh_exec, ssh_deploy


def example_1_simple_upload():
    """Example 1: Simple file upload"""
    print("\n=== Example 1: Simple SSH Upload ===")
    
    # Create test file
    test_file = "/tmp/test_upload.txt"
    with open(test_file, "w") as f:
        f.write("Hello from Streamware SSH!")
    
    # Upload using flow
    result = flow("ssh://upload?host=ssh-server&user=streamware&remote=/data/test.txt").run(test_file)
    print(f"✓ Upload result: {result}")
    
    # Or using helper
    result = ssh_upload("ssh-server", test_file, "/data/test.txt", user="streamware")
    print(f"✓ Helper upload: {result}")


def example_2_download():
    """Example 2: Download file"""
    print("\n=== Example 2: SSH Download ===")
    
    result = flow("ssh://download?host=ssh-server&user=streamware&remote=/data/test.txt&local=/tmp/downloaded.txt").run()
    print(f"✓ Downloaded: {len(result)} bytes")


def example_3_execute_command():
    """Example 3: Execute remote command"""
    print("\n=== Example 3: Execute Command ===")
    
    # Check disk space
    result = flow("ssh://exec?host=ssh-server&user=streamware&command=df -h").run()
    print(f"Exit code: {result['exit_code']}")
    print(f"Output:\n{result['stdout']}")
    
    # Or using helper
    result = ssh_exec("ssh-server", "uptime", user="streamware")
    print(f"Uptime: {result['stdout']}")


def example_4_deployment():
    """Example 4: Deploy application"""
    print("\n=== Example 4: Application Deployment ===")
    
    # Create app file
    app_file = "/tmp/app.py"
    with open(app_file, "w") as f:
        f.write("print('Hello from deployed app!')")
    
    # Deploy with automatic restart
    result = flow("ssh://deploy?host=ssh-server&user=streamware&path=/app/app.py&restart=myapp&permissions=755").run(app_file)
    print(f"✓ Deployment result: {result}")


def example_5_email_to_ssh_pipeline():
    """Example 5: Email attachments to SSH (quick style)"""
    print("\n=== Example 5: Email → SSH Pipeline ===")
    
    # Simulated: In real use, this would be a service
    print("""
    # Quick one-liner for email → SSH:
    
    sq email imap.gmail.com \\
        --user deploy@company.com \\
        --password secret \\
        --attachments \\
        --foreach "sq ssh prod.company.com --upload {} --user deploy --remote /app/uploads/"
    
    # Or as a background service:
    
    nohup bash << 'EOF' &
    while true; do
        for file in $(sq email imap.gmail.com --attachments --list); do
            sq ssh prod.company.com \\
                --upload "$file" \\
                --user deploy \\
                --key ~/.ssh/deploy_key \\
                --remote /data/incoming/
        done
        sleep 60
    done
    EOF
    """)


def example_6_secure_deployment():
    """Example 6: Secure deployment with password"""
    print("\n=== Example 6: Secure Deployment ===")
    
    print("""
    # Shell script with password protection:
    
    #!/bin/bash
    read -sp "Password: " password
    hash=$(echo -n "$password" | sha256sum | cut -d' ' -f1)
    
    if [[ "$hash" == "expected_hash_here" ]]; then
        sq ssh prod.company.com \\
            --deploy app.tar.gz \\
            --user deploy \\
            --key ~/.ssh/deploy_key \\
            --remote /app/ \\
            --restart myapp
        
        sq slack deployments \\
            --message "✓ Deployed by $USER" \\
            --token $SLACK_TOKEN
    else
        echo "Access denied"
        exit 1
    fi
    """)


def example_7_multi_server_deployment():
    """Example 7: Deploy to multiple servers"""
    print("\n=== Example 7: Multi-server Deployment ===")
    
    print("""
    # Deploy to multiple servers in parallel:
    
    servers=("prod1.com" "prod2.com" "prod3.com")
    
    for server in "${servers[@]}"; do
        sq ssh "$server" \\
            --deploy app.tar.gz \\
            --user deploy \\
            --remote /app/ \\
            --restart myapp &
    done
    
    wait
    echo "✓ Deployed to all servers"
    
    # Notify
    sq slack deployments \\
        --message "✓ Deployed to ${#servers[@]} servers"
    """)


def example_8_backup_via_ssh():
    """Example 8: Backup files via SSH"""
    print("\n=== Example 8: SSH Backup ===")
    
    print("""
    # Automated backup:
    
    # 1. Create backup
    sq postgres "SELECT * FROM important_data" --csv > backup.csv
    
    # 2. Compress
    tar czf backup_$(date +%Y%m%d).tar.gz backup.csv
    
    # 3. Upload to backup server
    sq ssh backup.company.com \\
        --upload backup_*.tar.gz \\
        --user backup \\
        --remote /backups/daily/
    
    # 4. Verify and notify
    sq ssh backup.company.com \\
        --exec "ls -lh /backups/daily/backup_$(date +%Y%m%d).tar.gz" \\
        --user backup
    
    sq slack backups --message "✓ Backup completed"
    """)


def example_9_monitoring_via_ssh():
    """Example 9: Remote monitoring"""
    print("\n=== Example 9: SSH Monitoring ===")
    
    print("""
    # Monitor remote servers:
    
    while true; do
        # Check disk space
        disk=$(sq ssh prod.com --exec "df -h /" --user monitor | grep -oP '\\d+%' | head -1)
        
        if [[ "${disk%?}" -gt 90 ]]; then
            sq slack alerts \\
                --message "🚨 Disk usage on prod.com: $disk"
        fi
        
        # Check service status
        status=$(sq ssh prod.com --exec "systemctl is-active myapp" --user monitor)
        
        if [[ "$status" != "active" ]]; then
            sq slack alerts \\
                --message "🚨 Service myapp is down on prod.com"
            
            # Auto-restart
            sq ssh prod.com --exec "systemctl restart myapp" --user admin
        fi
        
        sleep 300
    done
    """)


def example_10_ci_cd_pipeline():
    """Example 10: Complete CI/CD with SSH"""
    print("\n=== Example 10: CI/CD Pipeline ===")
    
    print("""
    # Complete deployment pipeline:
    
    #!/bin/bash
    set -e
    
    # 1. Build
    docker build -t myapp:latest .
    docker save myapp:latest | gzip > myapp.tar.gz
    
    # 2. Upload to staging
    sq ssh staging.company.com \\
        --upload myapp.tar.gz \\
        --user deploy \\
        --remote /tmp/
    
    # 3. Deploy on staging
    sq ssh staging.company.com \\
        --exec "docker load < /tmp/myapp.tar.gz && docker-compose up -d" \\
        --user deploy
    
    # 4. Run tests
    if sq get https://staging.company.com/health --json | jq -e '.status == "ok"'; then
        echo "✓ Staging tests passed"
        
        # 5. Deploy to production
        for server in prod1.com prod2.com prod3.com; do
            sq ssh "$server" \\
                --upload myapp.tar.gz \\
                --user deploy \\
                --remote /tmp/ &&
            sq ssh "$server" \\
                --exec "docker load < /tmp/myapp.tar.gz && docker-compose up -d" \\
                --user deploy
        done
        
        # 6. Notify success
        sq slack deployments \\
            --message "✓ Deployed v$(git describe --tags) to production"
        
        sq postgres "INSERT INTO deployments (version, timestamp, status) 
            VALUES ('$(git describe --tags)', NOW(), 'success')"
    else
        echo "✗ Staging tests failed"
        sq slack alerts --message "🚨 Deployment failed - staging tests"
        exit 1
    fi
    """)


def main():
    """Run all examples"""
    print("=" * 60)
    print("STREAMWARE SSH COMPONENT EXAMPLES")
    print("=" * 60)
    
    examples = [
        example_1_simple_upload,
        example_2_download,
        example_3_execute_command,
        example_4_deployment,
        example_5_email_to_ssh_pipeline,
        example_6_secure_deployment,
        example_7_multi_server_deployment,
        example_8_backup_via_ssh,
        example_9_monitoring_via_ssh,
        example_10_ci_cd_pipeline,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nNote: {example.__name__} - {e}")
            print("(Some examples show shell scripts, not Python execution)")
    
    print("\n" + "=" * 60)
    print("SSH Examples completed!")
    print("=" * 60)
    print("\n📚 Quick Reference:")
    print("  sq ssh HOST --upload FILE --remote PATH")
    print("  sq ssh HOST --download FILE --local PATH")
    print("  sq ssh HOST --exec COMMAND")
    print("  sq ssh HOST --deploy FILE --remote PATH --restart SERVICE")


if __name__ == "__main__":
    main()
