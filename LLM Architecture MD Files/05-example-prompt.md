Using the IBM Cloud diagram style guide, create a logical architecture diagram for the following system:

A healthcare application runs on IBM Cloud. Users access the app through a web browser. Traffic enters through IBM Cloud Internet Services and a public load balancer. The application runs on Red Hat OpenShift on IBM Cloud in a VPC. The app uses IBM Cloud Databases for PostgreSQL, IBM Cloud Object Storage for documents, IBM Key Protect for encryption keys, Secrets Manager for application secrets, IBM Cloud Monitoring and Log Analysis for operations, and Activity Tracker for audit events. The app integrates with an external EHR system through secure APIs.

Show:
- External users
- IBM Cloud boundary
- Region and VPC boundary
- Public ingress path
- OpenShift application layer
- Data layer
- Security services
- Observability/audit layer
- External EHR integration

Use clean IBM Cloud-style colors, clear labels, and labeled arrows.
