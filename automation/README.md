# AutoDriver automation bundle

This bundle adapts the supplied NVIDIA/CUDA Ansible configuration into resumable stages:

1. `precheck.yml` confirms the VM is ready.
2. `system.yml` applies Nouveau, initramfs, IOMMU, GRUB and build-package settings.
3. `repositories.yml` enables the official NVIDIA CUDA package source.
4. `driver.yml` installs the recommended NVIDIA driver from the target VM's repositories.
5. `cuda.yml` installs the newest available CUDA toolkit unless a specific package is requested.
6. `validate.yml` confirms the driver, toolkit and GPUs are available.

The web application executes these stages separately so an update can stop at a safe boundary.
