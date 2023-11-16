# KINEMA - Resource aware pod rescheduling in Kubernetes

Kinema is a sophisticated Kubernetes rescheduling system optimizing resource management by considering cluster state, predictive resource utilization, and cloud vendor pricing for intelligent decisions on node configuration and pod placement, achieving significant gains in cost reduction and resource utilization improvement.

Demo: 
[![Kinema Demo Video](img.youtube.com/vi/COywXBPQTlI/0.jpg)](https://www.youtube.com/watch?v=COywXBPQTlI) 

## Architecture 
![ALT TEXT](docs/architecture_overview.png)
At the core, Kinema has access to all workload placements in the cluster by leveraging the Kubernetes API. The system itself runs as a system-critical pod within the kube system namespace.
Apart from access to the current mapping of workloads onto nodes, the system also has access to current resource utilization that Prometheus actively scrapes. The resource utilization for each workload is provided by the daemon set cAdvisor, which monitors various parameters of the running containers. Additionally, current resource recommendations can be calculated using the available data from Prometheus and the VPA.
Kinema leverages an internal cloud controller to access the underlying cloud infrastructure seamlessly, granting comprehensive insights into available compute configurations and their corresponding pricing details. At present, Google Cloud is fully supported as a trusted cloud provider. However, owing to the cloud controllers’ highly modular nature and architecture, expanding compatibility with other platforms is readily achievable.
By combining the knowledge of current workload mappings, resource utilization, and available compute resources offered by the cloud provider, the current best configuration workload and node configuration for the cluster can be calculated and finally put into action using a rescheduling approach. This approach relies on well-established Kubernetes techniques, specifically rolling updates. These updates are performed with configurable maximum unavailability of services, guaranteeing no disruptions. This methodology maintains service continuity throughout the update process, ensuring a seamless transition without any negative impact on user experience. 
