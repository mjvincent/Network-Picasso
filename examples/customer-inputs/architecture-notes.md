# OmniCare Production Notes

The application runs in IBM Cloud us-south with disaster recovery planned for us-east.
Traffic enters through IBM Cloud Internet Services and a public load balancer.
The application runtime is Red Hat OpenShift on IBM Cloud inside the production VPC.
Private connectivity to the customer network uses Direct Link and Transit Gateway.
Application data is stored in PostgreSQL and IBM Cloud Object Storage.
Secrets Manager and Key Protect are required for secrets and encryption keys.
Monitoring, logging, Activity Tracker, and VPC flow logs are required for operations and audit.
